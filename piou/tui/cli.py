from __future__ import annotations

import asyncio
import io
import shlex
import sys
from contextlib import redirect_stdout, redirect_stderr
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Callable

from rich.text import Text

try:
    from textual.app import App, ComposeResult
    from textual.containers import Horizontal, Vertical
    from textual.widget import Widget
    from textual.widgets import Input, Rule, Static
    from textual.events import Key
except ImportError as e:
    raise ImportError("TUI mode requires textual. Install piou[tui] or 'textual' package.") from e

# Optional watchfiles for hot reload
try:
    import watchfiles  # noqa: F401

    HAS_WATCHFILES = True
except ImportError:
    HAS_WATCHFILES = False

if TYPE_CHECKING:
    from ..cli import Cli

from ..command import Command, CommandGroup, ShowHelpError
from .context import TuiContext, set_tui_context, reset_tui_context
from ..formatter.rich_formatter import RichFormatter
from .history import History
from .suggester import CommandSuggester

WatchCallback = Callable[[set[tuple[str, str]]], None]


class CssClass:
    SUGGESTION = "suggestion"
    SELECTED = "selected"
    MESSAGE = "message"
    OUTPUT = "output"
    ERROR = "error"


class TuiApp(App):
    BINDINGS = [("escape", "quit", "Quit")]
    CSS_PATH = "static/app.tcss"

    async def action_quit(self) -> None:
        """Save history and quit"""
        self.history.save()
        reset_tui_context()
        await super().action_quit()

    def __init__(
        self,
        cli: Cli,
        ansi_color: bool = True,
        history_file: Path | None = None,
    ):
        super().__init__(ansi_color=ansi_color)
        self.cli = cli
        # Set up TUI context for commands to access
        set_tui_context(TuiContext(_tui=self))
        # Enable force_terminal on formatter to preserve ANSI colors when capturing output
        if isinstance(self.cli.formatter, RichFormatter):
            self.cli.formatter._console._force_terminal = True
        self.cli_name = Path(sys.argv[0]).stem if sys.argv else "cli"
        self.commands = list(cli.commands.values())
        self.commands_map = {f"/{cmd.name}": cmd for cmd in self.commands}
        self.suggestion_index = -1
        self.current_suggestions: list[str] = []
        self.cycling = False
        self.history = History(file=history_file or Path.home() / f".{self.cli_name}_history")
        self.exit_pending = False

    def get_command_for_path(self, path: str) -> Command | CommandGroup | None:
        """Get command/group for a path like 'stats' or 'stats:uploads'"""
        parts = path.split(":")
        current = self.cli._group
        for part in parts:
            found = None
            for cmd in current.commands.values():
                if cmd.name.lower() == part.lower():
                    found = cmd
                    break
            if found is None:
                return None
            if isinstance(found, CommandGroup):
                current = found
            else:
                return found
        return current

    def _suggest_subcommands(self, query: str, suggestions: Vertical) -> None:
        """Suggest subcommands for a command path like 'stats:' or 'stats:up'"""
        parts = query.split(":")
        prefix_parts = parts[:-1]  # e.g., ["stats"] for "stats:up"
        subquery = parts[-1]  # e.g., "up" for "stats:up"

        # Navigate to the command group
        current = self.cli._group
        for part in prefix_parts:
            found = None
            for cmd in current.commands.values():
                if cmd.name.lower() == part:
                    found = cmd
                    break
            if found is None or not isinstance(found, CommandGroup):
                return  # Invalid path or not a command group
            current = found

        # Build the prefix string for suggestions
        prefix = ":".join(prefix_parts)

        # Suggest subcommands
        for cmd in current.commands.values():
            if subquery == "" or cmd.name.lower().startswith(subquery):
                full_path = f"/{prefix}:{cmd.name}"
                self.current_suggestions.append(full_path)
                text = f"{full_path:<20}{cmd.help or ''}"
                is_first = len(self.current_suggestions) == 1
                classes = f"{CssClass.SUGGESTION} {CssClass.SELECTED}" if is_first else CssClass.SUGGESTION
                suggestions.mount(Static(text, classes=classes))

    def compose(self) -> ComposeResult:
        yield Static(self.cli_name, id="name")
        if self.cli.description:
            yield Static(self.cli.description, id="description")
        yield Vertical(id="messages")
        yield Rule()
        with Horizontal(id="input-row"):
            yield Static("> ", id="prompt")
            yield Input(suggester=CommandSuggester(self))
        yield Rule()
        yield Static("Press Ctrl+C again to exit", id="exit-hint")
        yield Vertical(id="suggestions")

    def on_input_changed(self, event: Input.Changed) -> None:
        """Show command suggestions when input starts with /"""
        if self.cycling:
            self.cycling = False
            return

        # Reset exit hint when user starts typing
        if event.value and self.exit_pending:
            self.exit_pending = False
            self.query_one("#exit-hint", Static).display = False

        suggestions = self.query_one("#suggestions", Vertical)
        suggestions.remove_children()
        self.current_suggestions = []
        self.suggestion_index = -1

        value = event.value.strip()
        if value.startswith("/"):
            query = value[1:].lower()

            # Check if query contains : for subcommand navigation
            if ":" in query:
                self._suggest_subcommands(query, suggestions)
            else:
                # Add built-in /help command
                if query == "" or "help".startswith(query):
                    self.current_suggestions.append("/help")
                    text = f"{'/help':<15}Show available commands"
                    classes = f"{CssClass.SUGGESTION} {CssClass.SELECTED}"
                    suggestions.mount(Static(text, classes=classes))
                # Add CLI commands
                for cmd in self.commands:
                    if query == "" or cmd.name.lower().startswith(query):
                        self.current_suggestions.append(f"/{cmd.name}")
                        cmd_display = f"/{cmd.name}"
                        text = f"{cmd_display:<15}{cmd.help or ''}"
                        is_first = len(self.current_suggestions) == 1
                        classes = f"{CssClass.SUGGESTION} {CssClass.SELECTED}" if is_first else CssClass.SUGGESTION
                        suggestions.mount(Static(text, classes=classes))

            if self.current_suggestions:
                self.suggestion_index = 0

    def on_key(self, event: Key) -> None:
        """Route key events to specific handlers"""
        if event.key in ("up", "down") and self.current_suggestions:
            event.prevent_default()
            event.stop()
            self.on_up_down(event.key)
        elif event.key in ("up", "down") and not self.current_suggestions and self.history.entries:
            event.prevent_default()
            event.stop()
            self.on_history(event.key)
        elif event.key == "tab" and self.suggestion_index >= 0:
            event.prevent_default()
            event.stop()
            self.on_tab()
        elif event.key == "ctrl+c":
            event.prevent_default()
            event.stop()
            self.handle_ctrl_c()

    def on_up_down(self, key: str) -> None:
        """Cycle through suggestions with up/down arrows"""
        self.cycling = True
        if key == "down":
            self.suggestion_index = (self.suggestion_index + 1) % len(self.current_suggestions)
        else:
            self.suggestion_index = (self.suggestion_index - 1) % len(self.current_suggestions)
        inp = self.query_one(Input)
        inp.value = self.current_suggestions[self.suggestion_index]
        inp.cursor_position = len(inp.value)
        # Highlight selected suggestion
        suggestions = self.query(f".{CssClass.SUGGESTION}")
        for i, s in enumerate(suggestions):
            s.set_class(i == self.suggestion_index, CssClass.SELECTED)

    def on_history(self, key: str) -> None:
        """Cycle through command history with up/down arrows"""
        self.cycling = True
        entry = self.history.navigate(key)
        inp = self.query_one(Input)
        inp.value = entry or ""
        inp.cursor_position = len(inp.value)

    def clear_input(self) -> None:
        """Clear input field and suggestions"""
        inp = self.query_one(Input)
        inp.value = ""
        self.query_one("#suggestions", Vertical).remove_children()
        self.current_suggestions = []
        self.suggestion_index = -1
        self.history.reset_index()

    def handle_ctrl_c(self) -> None:
        """Handle Ctrl+C: clear input, or show exit hint, or exit"""
        inp = self.query_one(Input)
        exit_hint = self.query_one("#exit-hint", Static)

        if inp.value:
            # Input has content: clear it and reset exit state
            self.clear_input()
            self.exit_pending = False
            exit_hint.display = False
        elif self.exit_pending:
            # Input empty and already showed hint: exit
            self.history.save()
            self.exit()
        else:
            # Input empty, first Ctrl+C: show hint
            self.exit_pending = True
            exit_hint.display = True

    def on_tab(self) -> None:
        """Confirm selection and show first argument placeholder"""
        self.cycling = True
        # Clear suggestions
        self.query_one("#suggestions", Vertical).remove_children()
        # Get selected command and show first arg placeholder
        cmd_name = self.current_suggestions[self.suggestion_index]
        cmd = self.commands_map.get(cmd_name)
        inp = self.query_one(Input)
        if cmd and hasattr(cmd, "positional_args") and cmd.positional_args:
            first_arg = cmd.positional_args[0]
            inp.value = f"{cmd_name} <{first_arg.name}>"
        else:
            inp.value = f"{cmd_name} "
        inp.cursor_position = len(inp.value)
        self.current_suggestions = []
        self.suggestion_index = -1

    async def on_input_submitted(self, event: Input.Submitted) -> None:
        """Show user input in messages area and execute command when Enter is pressed"""
        value = event.value.strip()
        if not value:
            return

        # Add to history
        self.history.append(value)
        self.history.reset_index()

        messages = self.query_one("#messages", Vertical)
        messages.mount(Static(f"> {value}", classes=CssClass.MESSAGE))
        event.input.value = ""
        # Clear suggestions
        self.query_one("#suggestions", Vertical).remove_children()
        self.current_suggestions = []
        self.suggestion_index = -1

        # Execute command if it starts with /
        if value.startswith("/"):
            await self.execute_command(value)

    async def execute_command(self, value: str) -> None:
        """Parse and execute a command, capturing and displaying output"""
        try:
            parts = shlex.split(value)
        except ValueError:
            return

        if not parts:
            return

        # Strip leading / and split on : for subcommands
        cmd_path = parts[0].lstrip("/").split(":")
        args = parts[1:]
        messages = self.query_one("#messages", Vertical)

        # Handle /help as equivalent to --help
        if cmd_path == ["help"]:
            help_capture = io.StringIO()
            with redirect_stdout(help_capture):
                self.cli.formatter.print_help(group=self.cli._group, command=None, parent_args=[])
            messages.mount(Static(Text.from_ansi(help_capture.getvalue().strip()), classes=CssClass.OUTPUT))
            return

        # Capture stdout and stderr
        stdout_capture = io.StringIO()
        stderr_capture = io.StringIO()

        try:
            with redirect_stdout(stdout_capture), redirect_stderr(stderr_capture):
                loop = asyncio.get_running_loop()
                # Pass command path parts followed by args (e.g., stats:uploads -> "stats", "uploads")
                result = self.cli._group.run_with_args(*cmd_path, *args, loop=loop)
                if asyncio.iscoroutine(result):
                    await result
        except ShowHelpError as e:
            with redirect_stdout(stdout_capture):
                self.cli.formatter.print_help(group=e.group, command=e.command, parent_args=e.parent_args)
        except Exception as e:
            stderr_capture.write(str(e))

        # Display captured output
        stdout_output = stdout_capture.getvalue().strip()
        stderr_output = stderr_capture.getvalue().strip()

        if stdout_output:
            messages.mount(Static(Text.from_ansi(stdout_output), classes=CssClass.OUTPUT))

        if stderr_output:
            messages.mount(Static(Text.from_ansi(stderr_output), classes=f"{CssClass.OUTPUT} {CssClass.ERROR}"))

    # TuiInterface implementation - App.notify handles the actual display
    def mount_widget(self, widget: Widget) -> None:
        """Mount a widget to the messages area."""
        messages = self.query_one("#messages", Vertical)
        messages.mount(widget)

    def watch_files(
        self,
        *paths: Path | str,
        on_change: WatchCallback | None = None,
    ) -> asyncio.Task[None]:
        """Watch paths for file changes and show notifications.

        Requires `piou[tui-reload]` extra (watchfiles).

        Args:
            *paths: Paths to watch (files or directories)
            on_change: Optional callback called with set of (change_type, path) tuples

        Returns:
            An asyncio.Task that can be cancelled to stop watching.

        Raises:
            ImportError: If watchfiles is not installed.
        """
        if not HAS_WATCHFILES:
            raise ImportError("Hot reload requires watchfiles. Install piou[tui-reload] or 'watchfiles' package.")

        from watchfiles import awatch as watchfiles_awatch

        async def _watch_task() -> None:
            resolved_paths = [Path(p) if isinstance(p, str) else p for p in paths]
            path_names = ", ".join(p.name for p in resolved_paths)
            self.notify(f"Watching: {path_names}", title="Hot Reload")

            async for changes in watchfiles_awatch(*resolved_paths):
                # changes is a set of (change_type, path) tuples
                changed_files = {Path(p).name for _, p in changes}
                self.notify(
                    f"Changed: {', '.join(changed_files)}",
                    title="Hot Reload",
                    severity="warning",
                )
                if on_change is not None:
                    # Convert to (str, str) tuples as per WatchCallback type
                    changes_str = {(str(change_type), path) for change_type, path in changes}
                    on_change(changes_str)

        return asyncio.create_task(_watch_task())


@dataclass
class TuiCli:
    """TUI wrapper for a piou CLI."""

    cli: Cli

    def run(self) -> None:
        TuiApp(self.cli).run()
