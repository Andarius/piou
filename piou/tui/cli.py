from __future__ import annotations

import asyncio
import shlex
import sys
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

from textual.types import CSSPathType

from .runner import CommandRunner

if TYPE_CHECKING:
    from ..cli import Cli
    from ..command import CommandGroup

from ..command import Command

from .history import History


@dataclass
class TuiState:
    """State container for TUI application, decoupled from CLI internals."""

    cli_name: str
    description: str | None
    group: CommandGroup
    commands: list[Command | CommandGroup]
    commands_map: dict[str, Command | CommandGroup]
    history: History
    runner: CommandRunner
    on_ready: Callable[[], None] | None = None


@dataclass
class TuiCli:
    """TUI wrapper for a piou CLI. Creates TuiState and launches TuiApp."""

    cli: Cli
    inline: bool = False
    """Run TUI in inline mode (uses native terminal scrolling)."""
    history_file: Path | None = None
    """Path to history file. Defaults to ~/.{cli_name}_history."""
    loop: asyncio.AbstractEventLoop | None = None
    """Event loop to run the TUI on (if any)."""

    # Initialized in __post_init__
    state: TuiState = field(init=False)

    def __post_init__(self) -> None:
        cli_name = Path(sys.argv[0]).stem if sys.argv else "cli"
        commands = list(self.cli.commands.values())
        self.state = TuiState(
            cli_name=cli_name,
            description=self.cli.description,
            group=self.cli.group,
            commands=commands,
            commands_map={f"/{cmd.name}": cmd for cmd in commands},
            history=History(file=self.history_file or Path.home() / f".{cli_name}_history"),
            runner=CommandRunner(
                group=self.cli.group,
                formatter=self.cli.formatter,
                hide_internal_errors=self.cli.hide_internal_errors,
            ),
            on_ready=self.cli._on_tui_ready,
        )

    def get_app(
        self,
        initial_input: str | None = None,
        css: str | None = None,
        css_path: CSSPathType | None = None,
    ):
        """Create and return a TuiApp instance with optional custom CSS."""
        from .app import TuiApp

        return TuiApp(state=self.state, initial_input=initial_input, css=css, css_path=css_path)

    def run(
        self,
        *args: str,
        css: str | None = None,
        css_path: CSSPathType | None = None,
    ) -> None:
        """Run the TUI app, optionally pre-filling the input field with formatted args."""
        initial_input = None
        if args:
            cmd_name = args[0]
            cmd_args = args[1:]
            if cmd_args:
                initial_input = f"/{cmd_name} {shlex.join(cmd_args)}"
            else:
                initial_input = f"/{cmd_name}"
        return self.get_app(initial_input=initial_input, css=css, css_path=css_path).run(
            inline=self.inline, loop=self.loop
        )
