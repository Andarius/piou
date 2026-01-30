from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from rich.text import Text
from textual.types import CSSPathType

if TYPE_CHECKING:
    from .cli import TuiState

from ..command import Command

try:
    from textual.app import App, ComposeResult
    from textual.containers import Horizontal, Vertical
    from textual.events import Key
    from textual.widget import Widget
    from textual.widgets import Input, Rule, Static
except ImportError as e:
    raise ImportError("TUI mode requires textual. Install piou[tui] or 'textual' package.") from e

from .context import TuiContext, set_tui_context
from .suggester import CommandSuggester, get_command_for_path, get_command_suggestions, get_subcommand_suggestions
from .utils import get_command_help


class CssClass:
    SUGGESTION = "suggestion"
    SELECTED = "selected"
    MESSAGE = "message"
    OUTPUT = "output"
    ERROR = "error"


@dataclass
class PromptStyle:
    """Style configuration for the input prompt.

    Use this to customize the prompt appearance when borrowing user input.
    """

    text: str = "> "
    css_class: str | None = None

    def apply(self, app: TuiApp) -> PromptStyle:
        """Apply this style to the app's prompt. Returns the previous style for restoration."""
        prompt_widget = app.query_one("#prompt", Static)
        current_text = str(getattr(prompt_widget, "renderable", "> "))
        previous = PromptStyle(
            text=current_text,
            css_class=next(iter(prompt_widget.classes), None),
        )
        prompt_widget.update(self.text)
        prompt_widget.set_classes({self.css_class} if self.css_class else set())
        return previous


class TuiApp(App):
    """TUI application for a piou CLI."""

    BINDINGS = [("escape", "quit", "Quit")]
    CSS_PATH = "static/app.tcss"

    def __init__(
        self,
        state: TuiState,
        *,
        ansi_color: bool = True,
        initial_input: str | None = None,
        css: str | None = None,
        css_path: CSSPathType | None = None,
    ):
        super().__init__(ansi_color=ansi_color, css_path=css_path)
        self.state = state
        self.initial_input = initial_input
        if css:
            self.stylesheet.add_source(css, read_from=("<custom>", ""), is_default_css=False)

        # Set up TUI context for commands to access
        ctx = TuiContext()
        ctx.tui = self
        set_tui_context(ctx)

        # UI state
        self.suggestion_index = -1
        self.current_suggestions: list[str] = []
        self.suppress_input_change = False
        self.exit_pending = False

    @property
    def runner(self):
        """Convenience access to the command runner."""
        return self.state.runner

    @property
    def history(self):
        """Convenience access to command history."""
        return self.state.history

    @property
    def input_borrowed(self) -> bool:
        """True when a command is awaiting user input."""
        return self.runner.input_borrowed

    async def action_quit(self) -> None:
        """Save history and quit."""
        self.history.save()
        self._notify_history_error()
        await super().action_quit()

    # Compose & lifecycle

    def compose(self) -> ComposeResult:
        """Build the TUI layout.

        Layout:
            ┌──────────────────────────────────┐
            │ #name                            │
            │ #description (optional)          │ scrollable
            │ #messages (Vertical)             │
            │   ...                            │
            ├──────────────────────────────────┤
            │ #status-above (hidden by default)│
            │ #rule-above                      │
            │ #input-row (Horizontal)          │
            │   #prompt  Input                 │
            │ #rule-below                      │
            ├──────────────────────────────────┤
            │ #context-panel (Vertical)        │
            │   #hint                          │
            │   #suggestions (Vertical)        │
            │   #command-help                  │
            └──────────────────────────────────┘
        """
        with Vertical(id="messages"):
            yield Static(self.state.cli_name, id="name")
            if self.state.description:
                yield Static(self.state.description, id="description")
        yield Static(id="status-above")
        yield Rule(id="rule-above")
        with Horizontal(id="input-row"):
            yield Static("> ", id="prompt")
            yield Input(suggester=CommandSuggester(self))
        yield Rule(id="rule-below")
        with Vertical(id="context-panel"):
            yield Static(id="hint")
            yield Vertical(id="suggestions")
            yield Static(id="command-help")

    def on_mount(self) -> None:
        """Called when the app is mounted."""
        if self.initial_input:
            inp = self.query_one(Input)
            inp.value = self.initial_input
            inp.cursor_position = len(inp.value)
        self.runner.start_processing(
            on_success=self._display_output,
            on_error=self._on_process_error,
        )
        self._notify_history_error()

    def on_ready(self) -> None:
        """Called when the app is fully ready."""
        if self.state.on_ready:
            self.state.on_ready()

    # Input events

    def on_input_changed(self, event: Input.Changed) -> None:
        """Show command suggestions when input starts with /"""
        if self.suppress_input_change:
            self.suppress_input_change = False
            return

        if self.input_borrowed:
            return

        if event.value and self.exit_pending:
            self.exit_pending = False
            self._set_hint(None)

        suggestions_widget = self.query_one("#suggestions", Vertical)
        suggestions_widget.remove_children()
        suggestions_widget.display = False
        self.current_suggestions = []
        self.suggestion_index = -1

        value = event.value.strip()
        if value.startswith("!"):
            self._set_hint("Shell command - press Enter to execute", bash_mode=True)
            self._update_command_help(None)
        elif value.startswith("/"):
            self._set_hint(None)
            query = value[1:].lower()

            if ":" in query:
                suggestions = get_subcommand_suggestions(self.state.group, query)
                self._display_suggestions(suggestions, suggestions_widget, width=20)
            else:
                suggestions = get_command_suggestions(self.state.commands, query)
                self._display_suggestions(suggestions, suggestions_widget, width=15)

            if self.current_suggestions:
                self.suggestion_index = 0
                suggestions_widget.display = True
                self._update_command_help(self.current_suggestions[0])
            else:
                self._update_command_help(None)
        elif value:
            self._set_hint(None)
            self._update_command_help(None)

    def _display_suggestions(
        self,
        suggestions: list[tuple[str, str]],
        widget: Vertical,
        width: int,
    ) -> None:
        """Mount suggestion widgets from a list of (path, help_text) tuples."""
        for full_path, help_text in suggestions:
            self.current_suggestions.append(full_path)
            text = f"{full_path:<{width}}{help_text}"
            is_first = len(self.current_suggestions) == 1
            classes = f"{CssClass.SUGGESTION} {CssClass.SELECTED}" if is_first else CssClass.SUGGESTION
            widget.mount(Static(text, classes=classes))

    def on_key(self, event: Key) -> None:
        """Route key events to specific handlers."""
        if event.key in ("up", "down") and self.current_suggestions:
            event.prevent_default()
            event.stop()
            self._on_up_down(event.key)
        elif event.key in ("up", "down") and not self.current_suggestions and self.history.entries:
            event.prevent_default()
            event.stop()
            self._on_history(event.key)
        elif event.key == "tab" and self.suggestion_index >= 0:
            event.prevent_default()
            event.stop()
            self._on_tab()
        elif event.key == "ctrl+c":
            event.prevent_default()
            event.stop()
            self._handle_ctrl_c()

    def _on_up_down(self, key: str) -> None:
        """Cycle through suggestions with up/down arrows."""
        self.suppress_input_change = True
        if key == "down":
            self.suggestion_index = (self.suggestion_index + 1) % len(self.current_suggestions)
        else:
            self.suggestion_index = (self.suggestion_index - 1) % len(self.current_suggestions)
        inp = self.query_one(Input)
        inp.value = self.current_suggestions[self.suggestion_index]
        inp.cursor_position = len(inp.value)
        for i, s in enumerate(self.query(f".{CssClass.SUGGESTION}")):
            s.set_class(i == self.suggestion_index, CssClass.SELECTED)
        self._update_command_help(self.current_suggestions[self.suggestion_index])

    def _on_history(self, key: str) -> None:
        """Cycle through command history with up/down arrows."""
        self.suppress_input_change = True
        entry = self.history.navigate(key)
        inp = self.query_one(Input)
        inp.value = entry or ""
        inp.cursor_position = len(inp.value)

    def _on_tab(self) -> None:
        """Confirm selection and show first argument placeholder."""
        self.suppress_input_change = True
        suggestions = self.query_one("#suggestions", Vertical)
        suggestions.remove_children()
        suggestions.display = False
        cmd_name = self.current_suggestions[self.suggestion_index]
        cmd = self.state.commands_map.get(cmd_name)
        inp = self.query_one(Input)
        if isinstance(cmd, Command) and cmd.positional_args:
            first_arg = cmd.positional_args[0]
            inp.value = f"{cmd_name} <{first_arg.name}>"
        else:
            inp.value = f"{cmd_name} "
        inp.cursor_position = len(inp.value)
        self.current_suggestions = []
        self.suggestion_index = -1

    def on_input_submitted(self, event: Input.Submitted) -> None:
        """Show user input in messages area and queue command for execution."""
        value = event.value.strip()
        if not value:
            return

        if self.input_borrowed:
            self.runner.resolve_input(value)
            event.input.value = ""
            return

        self.history.append(value)
        self._notify_history_error()

        self._add_message(f"> {value}", CssClass.MESSAGE)
        event.input.value = ""

        suggestions = self.query_one("#suggestions", Vertical)
        suggestions.remove_children()
        suggestions.display = False
        self.current_suggestions = []
        self.suggestion_index = -1
        self._update_command_help(None)
        self._set_hint(None)

        if value.startswith("/") or value.startswith("!"):
            self.runner.queue_command(value)
            if self.runner.has_pending_commands():
                self._add_message("(queued)", CssClass.OUTPUT)

    def _handle_ctrl_c(self) -> None:
        """Handle Ctrl+C: cancel running command, clear input, show exit hint, or exit."""
        inp = self.query_one(Input)

        if self.input_borrowed:
            self.runner.cancel_input()
            self.clear_input()
            return

        if not self.runner.command_queue.empty():
            self.runner.cancel_and_restart(
                on_success=self._display_output,
                on_error=self._on_process_error,
            )
            self.exit_pending = False
            self._set_hint(None)
        elif inp.value:
            self.clear_input()
            self.exit_pending = False
            self._set_hint(None)
        elif self.exit_pending:
            self.history.save()
            self._notify_history_error()
            self.exit()
        else:
            self.exit_pending = True
            self._set_hint("Press Ctrl+C again to exit")

    def _display_output(self, stdout: Text | None, stderr: Text | None) -> None:
        """Display command output in the messages area."""
        if stdout:
            self._add_message(stdout, CssClass.OUTPUT)
        if stderr:
            self._add_message(stderr, f"{CssClass.OUTPUT} {CssClass.ERROR}")

    def _on_process_error(self):
        self._add_message("Interrupted", f"{CssClass.OUTPUT} {CssClass.ERROR}")

    # -------------------------------------------------------------------------
    # UI helpers
    # -------------------------------------------------------------------------

    def _add_message(self, content: str | Text | Widget, classes: str | None = None) -> None:
        """Add a message to the messages area and scroll to bottom."""
        messages = self.query_one("#messages", Vertical)
        _content = content if isinstance(content, Widget) else Static(content, classes=classes)
        # Scroll to the bottom of the messages area.
        messages.mount(_content)
        if self.is_inline:
            self.call_after_refresh(self.screen.scroll_end, animate=False)
        else:
            self.call_after_refresh(messages.scroll_end, animate=False)

    def clear_input(self) -> None:
        """Clear input field and suggestions."""
        inp = self.query_one(Input)
        inp.value = ""
        suggestions = self.query_one("#suggestions", Vertical)
        suggestions.remove_children()
        suggestions.display = False
        self.current_suggestions = []
        self.suggestion_index = -1
        self.history.reset_index()
        self._update_command_help(None)

    def _update_command_help(self, cmd_path: str | None) -> None:
        """Update the command help widget based on selected command."""
        help_widget = self.query_one("#command-help", Static)

        if cmd_path is None or cmd_path == "/help":
            help_widget.update("")
            help_widget.display = False
            return

        cmd = get_command_for_path(self.state.group, cmd_path)
        if cmd is None:
            help_widget.update("")
            help_widget.display = False
            return

        help_text = get_command_help(cmd)
        help_widget.update(help_text)
        help_widget.display = True

    def _set_hint(self, text: str | None, bash_mode: bool = False) -> None:
        """Update hint widget and Rule styling."""
        hint = self.query_one("#hint", Static)
        rules = self.query(Rule)
        if text:
            hint.update(text)
            hint.display = True
            hint.set_class(bash_mode, "bash-mode")
            for rule in rules:
                rule.set_class(bash_mode, "bash-mode")
        else:
            hint.update("")
            hint.display = False
            hint.remove_class("bash-mode")
            for rule in rules:
                rule.remove_class("bash-mode")

    def _set_rule(
        self,
        rule_id: str,
        line_style: str | None,
        add_class: str | None,
        remove_class: str | None,
    ) -> None:
        """Update a rule's line style and/or CSS class."""
        rule = self.query_one(f"#{rule_id}", Rule)
        if line_style is not None:
            rule.line_style = line_style  # type: ignore[assignment]
        if add_class is not None:
            rule.add_class(add_class)
        if remove_class is not None:
            rule.remove_class(remove_class)

    def _notify_history_error(self) -> None:
        if self.history.last_error:
            self.notify(self.history.last_error, title="History", severity="warning")
            self.history.last_error = None

    # Public API (for TuiContext)

    def set_hint(self, text: str | None) -> None:
        """Set or clear the hint text displayed below the input."""
        self._set_hint(text)

    def set_rule_above(
        self,
        line_style: str | None = None,
        add_class: str | None = None,
        remove_class: str | None = None,
    ) -> None:
        """Set the style of the rule above the input."""
        self._set_rule("rule-above", line_style, add_class, remove_class)

    def set_rule_below(
        self,
        line_style: str | None = None,
        add_class: str | None = None,
        remove_class: str | None = None,
    ) -> None:
        """Set the style of the rule below the input."""
        self._set_rule("rule-below", line_style, add_class, remove_class)

    async def prompt_input(self) -> str | None:
        """Wait for user input. Returns None on Ctrl+C."""
        return await self.runner.borrow_input()

    def mount_widget(self, widget: Widget) -> None:
        """Mount a widget to the messages area."""
        self._add_message(widget)

    def set_status_above(self, content: Widget | str | None) -> None:
        """Set or clear the status area above the input.

        Accepts a Widget for custom displays, a string for simple text,
        or None to clear.
        """
        status = self.query_one("#status-above", Static)
        if content is None:
            status.update("")
            status.display = False
        elif isinstance(content, str):
            status.update(content)
            status.display = True
        else:
            status.update(content.render())
            status.display = True
