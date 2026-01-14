from __future__ import annotations

import asyncio
import io
import os
import shlex
import sys
from contextlib import redirect_stdout, redirect_stderr
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

from rich.console import Console
from rich.text import Text

try:
    from textual.app import App, ComposeResult
    from textual.containers import Horizontal, Vertical
    from textual.widget import Widget
    from textual.widgets import Input, Rule, Static
    from textual.events import Key
except ImportError as e:
    raise ImportError("TUI mode requires textual. Install piou[tui] or 'textual' package.") from e


if TYPE_CHECKING:
    from ..cli import Cli

from ..command import Command, CommandGroup, ShowHelpError
from .context import TuiContext, set_tui_context
from ..formatter.rich_formatter import RichFormatter
from .history import History
from .suggester import CommandSuggester


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
        await super().action_quit()

    def __init__(
        self,
        cli: Cli,
        ansi_color: bool = True,
        history_file: Path | None = None,
        initial_input: str | None = None,
    ):
        super().__init__(ansi_color=ansi_color)
        self.cli = cli
        self.initial_input = initial_input
        # Set up TUI context for commands to access
        ctx = TuiContext()
        ctx.tui = self
        set_tui_context(ctx)
        # Enable force_terminal on formatter to preserve ANSI colors when capturing output
        if isinstance(self.cli.formatter, RichFormatter):
            self.cli.formatter._console = Console(markup=True, highlight=False, force_terminal=True)
        self.cli_name = Path(sys.argv[0]).stem if sys.argv else "cli"
        self.commands = list(cli.commands.values())
        self.commands_map = {f"/{cmd.name}": cmd for cmd in self.commands}
        self.suggestion_index = -1
        self.current_suggestions: list[str] = []
        self.history = History(file=history_file or Path.home() / f".{self.cli_name}_history")
        self.suppress_input_change = False
        self.exit_pending = False
        self.command_queue: asyncio.Queue[str] = asyncio.Queue()
        self.command_processor_task: asyncio.Task[None] | None = None

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

    def _format_command_help(self, cmd: Command | CommandGroup) -> Text:
        """Format command help for display in the help widget."""
        lines: list[str] = []

        # Usage line with arguments
        if isinstance(cmd, Command):
            args_parts = []
            for opt in cmd.positional_args:
                args_parts.append(f"<{opt.name}>")
            for opt in cmd.keyword_args:
                arg_name = sorted(opt.keyword_args)[-1]
                if opt.is_required:
                    args_parts.append(f"{arg_name} <value>")
                else:
                    args_parts.append(f"[{arg_name}]")
            if args_parts:
                lines.append(f"[bold]Usage:[/bold] /{cmd.name} {' '.join(args_parts)}")
            else:
                lines.append(f"[bold]Usage:[/bold] /{cmd.name}")

            # Arguments section
            if cmd.positional_args:
                lines.append("")
                lines.append("[bold]Arguments:[/bold]")
                for opt in cmd.positional_args:
                    type_name = getattr(opt.data_type, "__name__", str(opt.data_type))
                    help_text = f" - {opt.help}" if opt.help else ""
                    lines.append(f"  [cyan]<{opt.name}>[/cyan] ({type_name}){help_text}")

            # Options section
            if cmd.keyword_args:
                lines.append("")
                lines.append("[bold]Options:[/bold]")
                for opt in cmd.keyword_args:
                    arg_display = ", ".join(sorted(opt.keyword_args))
                    type_name = getattr(opt.data_type, "__name__", str(opt.data_type))
                    required = " [red]*required[/red]" if opt.is_required else ""
                    default = f" (default: {opt.default})" if not opt.is_required and opt.default is not None else ""
                    help_text = f" - {opt.help}" if opt.help else ""
                    lines.append(f"  [cyan]{arg_display}[/cyan] ({type_name}){required}{default}{help_text}")
        else:
            # CommandGroup
            lines.append(f"[bold]Usage:[/bold] /{cmd.name}:<subcommand>")
            if cmd.commands:
                lines.append("")
                lines.append("[bold]Subcommands:[/bold]")
                for subcmd in cmd.commands.values():
                    help_text = f" - {subcmd.help}" if subcmd.help else ""
                    lines.append(f"  [cyan]{subcmd.name}[/cyan]{help_text}")

        # Render with Rich markup
        console = Console(force_terminal=True, markup=True, highlight=False)
        with console.capture() as capture:
            for line in lines:
                console.print(line)
        return Text.from_ansi(capture.get().rstrip())

    def _update_command_help(self, cmd_path: str | None) -> None:
        """Update the command help widget based on selected command."""
        help_widget = self.query_one("#command-help", Static)

        if cmd_path is None or cmd_path == "/help":
            help_widget.update("")
            return

        # Strip leading / and get command
        path = cmd_path.lstrip("/")
        cmd = self.get_command_for_path(path)

        if cmd is None:
            help_widget.update("")
            return

        help_text = self._format_command_help(cmd)
        help_widget.update(help_text)

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
        """
        ┌─────────────────────────────────┐
        │ cli_name                        │
        │ description                     │
        │                                 │
        │ #messages (command output)      │
        │                                 │
        │─────────────────────────────────│
        │ > [input                      ] │
        │─────────────────────────────────│
        │ Press Ctrl+C again to exit      │
        │ #suggestions                    │
        │ #command-help                   │
        └─────────────────────────────────┘
        """
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
        yield Static(id="command-help")

    def on_mount(self) -> None:
        """Called when the app is mounted. Prefill input if initial_input is set."""
        if self.initial_input:
            inp = self.query_one(Input)
            inp.value = self.initial_input
            inp.cursor_position = len(inp.value)
        # Start command processor task
        self.command_processor_task = asyncio.create_task(self._process_command_queue())

    def on_input_changed(self, event: Input.Changed) -> None:
        """Show command suggestions when input starts with /"""
        if self.suppress_input_change:
            self.suppress_input_change = False
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
                self._update_command_help(self.current_suggestions[0])
            else:
                self._update_command_help(None)
        else:
            self._update_command_help(None)

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
        self.suppress_input_change = True
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
        # Update help for selected command
        self._update_command_help(self.current_suggestions[self.suggestion_index])

    def on_history(self, key: str) -> None:
        """Cycle through command history with up/down arrows"""
        self.suppress_input_change = True
        entry = self.history.navigate(key)
        inp = self.query_one(Input)
        inp.value = entry or ""  # None when navigating past most recent entry
        inp.cursor_position = len(inp.value)

    def clear_input(self) -> None:
        """Clear input field and suggestions"""
        inp = self.query_one(Input)
        inp.value = ""
        self.query_one("#suggestions", Vertical).remove_children()
        self.current_suggestions = []
        self.suggestion_index = -1
        self.history.reset_index()
        self._update_command_help(None)

    def handle_ctrl_c(self) -> None:
        """Handle Ctrl+C: cancel running command, clear input, show exit hint, or exit"""
        inp = self.query_one(Input)
        exit_hint = self.query_one("#exit-hint", Static)

        # If commands are queued or running, cancel the processor
        if not self.command_queue.empty():
            if self.command_processor_task and not self.command_processor_task.done():
                self.command_processor_task.cancel()
                # Restart the processor for future commands
                self.command_processor_task = asyncio.create_task(self._process_command_queue())
            self.exit_pending = False
            exit_hint.display = False
        elif inp.value:
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
        self.suppress_input_change = True
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

    def on_input_submitted(self, event: Input.Submitted) -> None:
        """Show user input in messages area and queue command for execution"""
        value = event.value.strip()
        if not value:
            return

        # Add to history
        self.history.append(value)

        messages = self.query_one("#messages", Vertical)
        messages.mount(Static(f"> {value}", classes=CssClass.MESSAGE))
        self.call_after_refresh(self.screen.scroll_end)
        event.input.value = ""
        # Clear suggestions and help
        self.query_one("#suggestions", Vertical).remove_children()
        self.current_suggestions = []
        self.suggestion_index = -1
        self._update_command_help(None)

        # Queue command for execution if it starts with /
        if value.startswith("/"):
            self.command_queue.put_nowait(value)
            # Show queued indicator if there are already commands in queue
            if self.command_queue.qsize() > 1:
                messages.mount(Static("(queued)", classes=f"{CssClass.OUTPUT}"))
                self.call_after_refresh(self.screen.scroll_end)

    async def _process_command_queue(self) -> None:
        """Continuously process commands from the queue."""
        while True:
            try:
                # Wait for next command
                value = await self.command_queue.get()

                try:
                    await self.execute_command(value)
                except asyncio.CancelledError:
                    # Command was cancelled, show message and clear queue
                    messages = self.query_one("#messages", Vertical)
                    messages.mount(Static("Interrupted", classes=f"{CssClass.OUTPUT} {CssClass.ERROR}"))
                    self.call_after_refresh(self.screen.scroll_end)
                    # Drain the queue
                    while not self.command_queue.empty():
                        try:
                            self.command_queue.get_nowait()
                        except asyncio.QueueEmpty:
                            break
                    raise  # Re-raise to stop the processor
                finally:
                    # Mark task as done
                    self.command_queue.task_done()
            except asyncio.CancelledError:
                # Processor is being shut down
                break

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
            self.call_after_refresh(self.screen.scroll_end)
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
            # Capture exception traceback using formatter's console
            if isinstance(self.cli.formatter, RichFormatter):
                with self.cli.formatter._console.capture() as capture:
                    self.cli.formatter.print_exception(e, hide_internals=self.cli.hide_internal_errors)
                stderr_capture.write(capture.get())
            else:
                with redirect_stderr(stderr_capture):
                    self.cli.formatter.print_exception(e, hide_internals=self.cli.hide_internal_errors)

        # Display captured output
        stdout_output = stdout_capture.getvalue().strip()
        stderr_output = stderr_capture.getvalue().strip()

        if stdout_output:
            messages.mount(Static(Text.from_ansi(stdout_output), classes=CssClass.OUTPUT))

        if stderr_output:
            messages.mount(Static(Text.from_ansi(stderr_output), classes=f"{CssClass.OUTPUT} {CssClass.ERROR}"))

        if stdout_output or stderr_output:
            self.call_after_refresh(self.screen.scroll_end)

    # TuiInterface implementation - App.notify handles the actual display
    def mount_widget(self, widget: Widget) -> None:
        """Mount a widget to the messages area."""
        messages = self.query_one("#messages", Vertical)
        messages.mount(widget)
        self.call_after_refresh(self.screen.scroll_end)


@dataclass
class TuiCli:
    """TUI wrapper for a piou CLI."""

    cli: Cli
    inline: bool = field(default_factory=lambda: os.getenv("PIOU_TUI_INLINE", "0") == "1")
    """Run TUI in inline mode (uses native terminal scrolling). Supports PIOU_TUI_INLINE env var."""

    def run(self, *args: str) -> None:
        """Run the TUI app.

        Args:
            *args: Command-line arguments to prefill in the input field.
                   Will be formatted as "/<cmd> <args...>" if provided.
        """
        initial_input = None
        if args:
            # Format args as TUI command: first arg is command name, rest are arguments
            cmd_name = args[0]
            cmd_args = args[1:]
            if cmd_args:
                initial_input = f"/{cmd_name} {shlex.join(cmd_args)}"
            else:
                initial_input = f"/{cmd_name}"
        TuiApp(self.cli, initial_input=initial_input).run(inline=self.inline)
