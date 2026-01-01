from __future__ import annotations

import asyncio
import io
import shlex
import sys
from contextlib import redirect_stdout, redirect_stderr
from dataclasses import dataclass, field as dataclass_field
from pathlib import Path
from typing import TYPE_CHECKING

from rich.text import Text

try:
    from textual.app import App, ComposeResult
    from textual.containers import Horizontal, Vertical
    from textual.widgets import Input, Rule, Static
    from textual.events import Key
except ImportError as e:
    raise ImportError("TUI mode requires textual. Install piou[tui] or 'textual' package.") from e

from ..command import CommandGroup, ShowHelpError


class CssClass:
    SUGGESTION = "suggestion"
    SELECTED = "selected"
    MESSAGE = "message"
    OUTPUT = "output"
    ERROR = "error"


@dataclass
class History:
    file: Path
    entries: list[str] = dataclass_field(default_factory=list)
    index: int = -1

    def __post_init__(self) -> None:
        if self.file.exists():
            try:
                self.entries = self.file.read_text().strip().split("\n")
            except Exception:
                pass

    def append(self, entry: str) -> None:
        """Add entry to history and persist to file."""
        self.entries.insert(0, entry)
        try:
            with self.file.open("a") as f:
                f.write(entry + "\n")
        except Exception:
            pass

    def save(self, max_entries: int = 1000) -> None:
        """Save and truncate history file to max entries."""
        try:
            entries = self.entries[:max_entries]
            self.file.write_text("\n".join(entries))
        except Exception:
            pass

    def navigate(self, direction: str) -> str | None:
        """Navigate history up/down, return entry or None if at boundary."""
        if not self.entries:
            return None
        if direction == "up":
            self.index = min(self.index + 1, len(self.entries) - 1)
        else:
            self.index = max(self.index - 1, -1)
        return self.entries[self.index] if self.index >= 0 else None

    def reset_index(self) -> None:
        """Reset navigation index."""
        self.index = -1


if TYPE_CHECKING:
    from ..cli import Cli


class TuiApp(App):
    BINDINGS = [("escape", "quit", "Quit")]
    CSS_PATH = "static/app.tcss"

    def action_quit(self) -> None:
        """Save history and quit"""
        self.history.save()
        super().action_quit()

    def __init__(
        self,
        cli: Cli,
        ansi_color: bool = True,
        history_file: Path | None = None,
    ):
        super().__init__(ansi_color=ansi_color)
        self.cli = cli
        # Enable force_terminal on formatter to preserve ANSI colors when capturing output
        if hasattr(self.cli.formatter, "force_terminal"):
            self.cli.formatter.force_terminal = True
            self.cli.formatter.__post_init__()  # Reinitialize console with new setting
        self.cli_name = Path(sys.argv[0]).stem if sys.argv else "cli"
        self.commands = list(cli.commands.values())
        self.commands_map = {f"/{cmd.name}": cmd for cmd in self.commands}
        self.suggestion_index = -1
        self.current_suggestions: list[str] = []
        self.cycling = False
        self.history = History(file=history_file or Path.home() / f".{self.cli_name}_history")
        self.exit_pending = False

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
            yield Input()
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


@dataclass
class TuiCli:
    """TUI wrapper for a piou CLI."""

    cli: Cli

    def run(self) -> None:
        TuiApp(self.cli).run()
