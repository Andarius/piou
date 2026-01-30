from __future__ import annotations

import asyncio
import io
import shlex
from contextlib import redirect_stdout, redirect_stderr
from dataclasses import dataclass, field

from typing import Callable

from rich.console import Console
from rich.text import Text

from piou import CommandGroup
from ..command import ShowHelpError
from ..exceptions import (
    CommandError,
    CommandException,
    CommandNotFoundError,
    InvalidChoiceError,
    InvalidValueError,
)
from ..formatter import Formatter, RichFormatter

__all__ = ("CommandRunner",)


@dataclass
class CommandRunner:
    """Handles command parsing, execution, and output capture."""

    group: CommandGroup
    formatter: Formatter
    hide_internal_errors: bool = True

    # Internal state
    _input_future: asyncio.Future[str] | None = field(init=False, default=None)
    _command_queue: asyncio.Queue[str] = field(init=False, default_factory=asyncio.Queue)
    _processor_task: asyncio.Task[None] | None = field(init=False, default=None)

    def __post_init__(self):
        if isinstance(self.formatter, RichFormatter):
            self.formatter._console = Console(markup=True, highlight=False, force_terminal=True)

    @property
    def command_queue(self) -> asyncio.Queue[str]:
        """The command queue."""
        return self._command_queue

    @property
    def input_borrowed(self) -> bool:
        """True when a command is awaiting user input via prompt_input."""
        return self._input_future is not None

    def queue_command(self, value: str) -> None:
        """Add a command to the queue."""
        self._command_queue.put_nowait(value)

    def has_pending_commands(self) -> bool:
        """True if there are commands waiting in the queue."""
        return self._command_queue.qsize() > 1

    def cancel_input(self) -> None:
        """Cancel the current input future if one exists."""
        if self._input_future is not None:
            self._input_future.cancel()

    def cancel_and_restart(
        self,
        on_success: Callable[[Text | None, Text | None], None],
        on_error: Callable[[], None],
    ) -> None:
        """Cancel the current processor task and start a new one."""
        if self._processor_task and not self._processor_task.done():
            self._processor_task.cancel()
        self._processor_task = asyncio.create_task(self.process_command_queue(on_success=on_success, on_error=on_error))

    def start_processing(
        self,
        on_success: Callable[[Text | None, Text | None], None],
        on_error: Callable[[], None],
    ) -> None:
        """Start the command queue processor task."""
        self._processor_task = asyncio.create_task(self.process_command_queue(on_success=on_success, on_error=on_error))

    def resolve_input(self, value: str) -> None:
        """Resolve the current input future with a value."""
        if self._input_future is not None and not self._input_future.done():
            self._input_future.set_result(value)

    async def borrow_input(self) -> str | None:
        """Wait for user input. Returns None if cancelled."""
        loop = asyncio.get_running_loop()
        self._input_future = loop.create_future()
        try:
            return await self._input_future
        except asyncio.CancelledError:
            return None
        finally:
            self._input_future = None

    def get_help_output(self) -> str:
        """Return main help as ANSI string."""
        help_capture = io.StringIO()
        with redirect_stdout(help_capture):
            self.formatter.print_help(group=self.group, command=None, parent_args=[])
        return help_capture.getvalue().strip()

    async def execute(self, value: str) -> tuple[Text | None, Text | None]:
        """Execute a command string, returning (stdout, stderr) as Text objects.

        Handles both CLI commands (starting with /) and shell commands (starting with !).
        """
        if value.startswith("!"):
            bash_cmd = value[1:].strip()
            if bash_cmd:
                return await self.execute_bash(bash_cmd)
            return None, None

        try:
            parts = shlex.split(value)
        except ValueError:
            return None, None

        if not parts:
            return None, None

        cmd_path = parts[0].lstrip("/").split(":")
        args = parts[1:]

        # Handle /help as equivalent to --help
        if cmd_path == ["help"]:
            return Text.from_ansi(self.get_help_output()), None

        stdout_capture = io.StringIO()
        stderr_capture = io.StringIO()

        try:
            with redirect_stdout(stdout_capture), redirect_stderr(stderr_capture):
                loop = asyncio.get_running_loop()
                result = self.group.run_with_args(*cmd_path, *args, loop=loop)
                if asyncio.iscoroutine(result):
                    await result
        except ShowHelpError as e:
            with redirect_stdout(stdout_capture):
                self.formatter.print_help(group=e.group, command=e.command, parent_args=e.parent_args)
        except (CommandNotFoundError, CommandException, InvalidChoiceError, InvalidValueError, CommandError) as e:
            stderr_capture.write(str(e))
        except Exception as e:
            if isinstance(self.formatter, RichFormatter):
                with self.formatter._console.capture() as capture:
                    self.formatter.print_exception(e, hide_internals=self.hide_internal_errors)
                stderr_capture.write(capture.get())
            else:
                with redirect_stderr(stderr_capture):
                    self.formatter.print_exception(e, hide_internals=self.hide_internal_errors)

        stdout_output = stdout_capture.getvalue().strip()
        stderr_output = stderr_capture.getvalue().strip()

        return (
            Text.from_ansi(stdout_output) if stdout_output else None,
            Text.from_ansi(stderr_output) if stderr_output else None,
        )

    @staticmethod
    async def execute_bash(cmd: str) -> tuple[Text | None, Text | None]:
        """Execute a shell command and return (stdout, stderr) as Text objects."""
        try:
            proc = await asyncio.create_subprocess_shell(
                cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await proc.communicate()

            return (
                Text.from_ansi(stdout.decode()) if stdout else None,
                Text.from_ansi(stderr.decode()) if stderr else None,
            )
        except Exception as e:
            return None, Text(str(e))

    async def process_command_queue(
        self,
        on_success: Callable[[Text | None, Text | None], None],
        on_error: Callable[[], None],
    ) -> None:
        """Continuously process commands from the queue."""
        while True:
            try:
                value = await self._command_queue.get()
                try:
                    stdout, stderr = await self.execute(value)
                    on_success(stdout, stderr)
                except asyncio.CancelledError:
                    on_error()
                    while not self._command_queue.empty():
                        try:
                            self._command_queue.get_nowait()
                        except asyncio.QueueEmpty:
                            break
                    raise
                finally:
                    self._command_queue.task_done()
            except asyncio.CancelledError:
                break
