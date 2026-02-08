from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from rich.text import Text
from textual.types import CSSPathType

if TYPE_CHECKING:
    from .cli import TuiState

from ..command import Command
from .watcher import Watcher

try:
    from textual.app import App, ComposeResult
    from textual.containers import Horizontal, Vertical
    from textual.events import Key
    from textual.widget import Widget
    from textual.widgets import Input, Rule, Static
except ImportError as e:
    raise ImportError("TUI mode requires textual. Install piou[tui] or 'textual' package.") from e

from .context import TuiContext, set_tui_context
from .suggester import (
    CommandSuggester,
    OptionContext,
    SuggestionState,
    get_command_for_path,
    get_command_suggestions,
    get_subcommand_suggestions,
    get_value_suggestions,
    parse_option_context,
)
from .utils import get_command_help
from .value_picker import ValuePicker


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
        dev: bool = False,
    ):
        super().__init__(ansi_color=ansi_color, css_path=css_path)
        self.state = state
        self.initial_input = initial_input
        self.dev = dev
        if css:
            self.stylesheet.add_source(css, read_from=("<custom>", ""), is_default_css=False)

        # Set up TUI context for commands to access
        ctx = TuiContext()
        ctx.tui = self
        set_tui_context(ctx)

        # UI state
        self.suggestions = SuggestionState()
        self.suppress_input_change = False
        self.exit_pending = False
        self.silent_queue = False
        # Cache last help path to skip redundant widget updates
        self._last_help_path: str | None = None

        # Dev mode: file watching
        self._watcher = Watcher(state.group, on_reload=state.on_reload)
        if dev:
            self._watcher.start()

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

    # Dev mode: file watching

    def _toggle_reload(self) -> None:
        """Toggle reload mode on/off."""
        self.dev = not self.dev
        if self.dev:
            self._watcher.start()
            self.run_worker(self._watch_loop, exclusive=True)
            self.notify("Reload enabled", severity="information")
        else:
            self._watcher.stop()
            self.notify("Reload disabled", severity="information")

    async def _watch_loop(self) -> None:
        """Run the file watcher and handle events."""
        async for error in self._watcher.watch():
            if error:
                self.notify(error, severity="error")
            else:
                self.notify("Code reloaded", severity="information")

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
            │   #value-picker (ValuePicker)    │
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
            yield ValuePicker(id="value-picker")
            yield Static(id="command-help")

    def on_mount(self) -> None:
        """Called when the app is mounted."""
        self._picker = self.query_one(ValuePicker)
        self._suggestions_widget = self.query_one("#suggestions", Vertical)
        self.runner.start_processing(
            on_success=self._display_output,
            on_error=self._on_process_error,
        )
        self._notify_history_error()
        if self.dev:
            self.run_worker(self._watch_loop, exclusive=True)

    def on_ready(self) -> None:
        """Called when the app is fully ready."""
        if self.dev:
            self.notify("Reload enabled", severity="information")
        if self.state.on_ready:
            self.state.on_ready()
        # Auto-execute initial command if provided
        if self.initial_input:
            inp = self.query_one(Input)
            self._add_message(f"> {self.initial_input}", CssClass.MESSAGE)
            inp.value = ""
            self.runner.queue_command(self.initial_input)

    # Input events

    def on_input_changed(self, event: Input.Changed) -> None:
        """Show command suggestions when input starts with /"""
        if self._handle_early_returns(event):
            return

        self._reset_suggestion_state()

        value = event.value.strip()
        if value.startswith("!"):
            self._handle_shell_command()
        elif value.startswith("/"):
            self._handle_command_suggestions(event.value)
        elif value:
            self._set_hint(None)
            self._update_command_help(None)

    def _handle_early_returns(self, event: Input.Changed) -> bool:
        """Check conditions that should skip suggestion processing.

        Returns True when the input change was programmatic (suppress flag),
        the input is borrowed by another widget (e.g. prompt), or to cancel
        exit-pending state when the user starts typing again.
        """
        if self.suppress_input_change:
            self.suppress_input_change = False
            return True

        if self.input_borrowed:
            return True

        if event.value and self.exit_pending:
            self.exit_pending = False
            self._set_hint(None)

        return False

    def _reset_suggestion_state(self) -> None:
        """Reset all suggestion-related UI state."""
        if self._suggestions_widget.children:
            self._suggestions_widget.remove_children()
        self._suggestions_widget.display = False
        self.suggestions.reset()
        if self._picker.values:
            self._picker.clear()

    def _handle_shell_command(self) -> None:
        """Handle shell command input (starts with !)."""
        self._set_hint("Shell command - press Enter to execute", bash_mode=True)
        self._update_command_help(None)

    def _handle_command_suggestions(self, input_value: str) -> None:
        """Handle command suggestions for input starting with /."""
        self._set_hint(None)

        parts = input_value[1:].split(None, 1)
        cmd_path = parts[0].lower() if parts else ""
        args_text = parts[1] if len(parts) > 1 else ""
        resolved = get_command_for_path(self.state.group, cmd_path)

        if not args_text:
            self._show_command_suggestions(cmd_path, self._suggestions_widget)
        elif isinstance(resolved, Command):
            if input_value.endswith(" ") and not args_text.endswith(" "):
                args_text += " "
            self._handle_value_completion(args_text, resolved, cmd_path)

        # Update help panel
        if resolved:
            self._update_command_help(f"/{cmd_path}")
        elif self.suggestions.items:
            self._update_command_help(self.suggestions.items[0])
        else:
            self._update_command_help(None)

    def _show_command_suggestions(self, cmd_path: str, suggestions_widget: Vertical) -> None:
        """Show command suggestions based on command path."""
        if ":" in cmd_path:
            suggestions = get_subcommand_suggestions(self.state.group, cmd_path)
            self._display_suggestions(suggestions, suggestions_widget, width=20)
        else:
            suggestions = get_command_suggestions(self.state.commands, cmd_path)
            self._display_suggestions(suggestions, suggestions_widget, width=15)

        if self.suggestions.items:
            self.suggestions.index = 0
            suggestions_widget.display = True

    def _handle_value_completion(self, args_text: str, command: Command, cmd_path: str) -> None:
        """Handle option value completion for a resolved command with arguments."""
        ctx = parse_option_context(command, args_text)
        if ctx is not None:
            self.suggestions.value_prefix = f"/{cmd_path} {ctx.prefix}"
            self.run_worker(
                self._load_value_suggestions(ctx, self.suggestions.value_prefix),
                exclusive=True,
                group="value_suggestions",
            )

    async def _load_value_suggestions(self, ctx: OptionContext, expected_prefix: str) -> None:
        """Load value suggestions asynchronously and display them."""
        value_suggestions = await get_value_suggestions(ctx)
        if not value_suggestions or self.suggestions.value_prefix != expected_prefix:
            return
        self._picker.set_values([v for v, _ in value_suggestions])

    def _display_suggestions(
        self,
        suggestions: list[tuple[str, str]],
        widget: Vertical,
        width: int,
    ) -> None:
        """Mount suggestion widgets from a list of (path, help_text) tuples."""
        for full_path, help_text in suggestions:
            self.suggestions.items.append(full_path)
            text = f"{full_path:<{width}}{help_text}"
            is_first = len(self.suggestions.items) == 1
            classes = f"{CssClass.SUGGESTION} {CssClass.SELECTED}" if is_first else CssClass.SUGGESTION
            widget.mount(Static(text, classes=classes))

    def on_key(self, event: Key) -> None:
        """Route key events to specific handlers."""
        if event.key in ("left", "right", "up", "down") and self._picker.has_selection:
            event.prevent_default()
            event.stop()
            self._on_picker_nav(event.key, self._picker)
            return
        if event.key in ("up", "down") and self.suggestions.items:
            event.prevent_default()
            event.stop()
            self._on_up_down(event.key)
        elif event.key in ("up", "down") and not self.suggestions.items and self.history.entries:
            event.prevent_default()
            event.stop()
            self._on_history(event.key)
        elif event.key == "tab" and (self.suggestions.index >= 0 or self._picker.has_selection):
            event.prevent_default()
            event.stop()
            self._on_tab()
        elif event.key == "ctrl+c":
            event.prevent_default()
            event.stop()
            self._handle_ctrl_c()

    def _on_up_down(self, key: str) -> None:
        """Cycle through command suggestions with up/down arrows."""
        self.suppress_input_change = True
        if key == "down":
            self.suggestions.index = (self.suggestions.index + 1) % len(self.suggestions.items)
        else:
            self.suggestions.index = (self.suggestions.index - 1) % len(self.suggestions.items)
        inp = self.query_one(Input)
        selected = self.suggestions.items[self.suggestions.index]
        if self.suggestions.value_prefix is not None:
            inp.value = f"{self.suggestions.value_prefix}{selected}"
        else:
            inp.value = selected
        inp.cursor_position = len(inp.value)
        for i, s in enumerate(self.query(f".{CssClass.SUGGESTION}")):
            s.set_class(i == self.suggestions.index, CssClass.SELECTED)
        if self.suggestions.value_prefix is None:
            self._update_command_help(selected)

    def _on_picker_nav(self, key: str, picker: ValuePicker) -> None:
        """Handle navigation within the ValuePicker."""
        self.suppress_input_change = True
        selected = picker.navigate(key)
        if selected is not None:
            inp = self.query_one(Input)
            if self.suggestions.value_prefix is not None:
                inp.value = f"{self.suggestions.value_prefix}{selected}"
            else:
                inp.value = selected
            inp.cursor_position = len(inp.value)

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
        inp = self.query_one(Input)

        if self._picker.has_selection:
            selected = self._picker.selected_value or ""
            inp.value = f"{self.suggestions.value_prefix or ''}{selected} "
            self._picker.clear()
        else:
            self._suggestions_widget.remove_children()
            self._suggestions_widget.display = False
            selected = self.suggestions.items[self.suggestions.index]
            cmd = self.state.commands_map.get(selected)
            if isinstance(cmd, Command) and cmd.positional_args:
                first_arg = cmd.positional_args[0]
                inp.value = f"{selected} <{first_arg.name}>"
            else:
                inp.value = f"{selected} "

        inp.cursor_position = len(inp.value)
        self.suggestions.reset()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        """Show user input in messages area and queue command for execution."""
        value = event.value.strip()
        if not value:
            return

        if self.input_borrowed:
            self.runner.resolve_input(value)
            event.input.value = ""
            return

        # Normalize command (strip extra leading slashes)
        history_value = value
        if value.startswith("/"):
            history_value = "/" + value.lstrip("/")
        self.history.append(history_value)
        self._notify_history_error()

        # Only display message if not in silent queue mode
        if not self.silent_queue:
            self._add_message(f"> {value}", CssClass.MESSAGE)
        event.input.value = ""

        self._suggestions_widget.remove_children()
        self._suggestions_widget.display = False
        self.suggestions.reset()
        self._update_command_help(None)
        self._set_hint(None)

        # Handle built-in TUI commands
        if value.lower() == "/tui-reload":
            self._toggle_reload()
            return

        if value.startswith("/") or value.startswith("!"):
            self.runner.queue_command(value)
            if self.runner.pending_count > 1:
                self._add_message(f"({self.runner.pending_count} queued)", CssClass.OUTPUT)

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
        self._suggestions_widget.remove_children()
        self._suggestions_widget.display = False
        self.suggestions.reset()
        self._picker.clear()
        self.history.reset_index()
        self._update_command_help(None)

    def _update_command_help(self, cmd_path: str | None) -> None:
        """Update the command help widget based on selected command."""
        # Skip if path unchanged (avoid redundant widget updates)
        if cmd_path == self._last_help_path:
            return
        self._last_help_path = cmd_path

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

        help_text = get_command_help(cmd, cmd_path)
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
