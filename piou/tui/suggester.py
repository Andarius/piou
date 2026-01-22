from __future__ import annotations

from typing import TYPE_CHECKING

from textual.suggester import Suggester

from .utils import get_command_for_path
from ..command import Command, CommandGroup

if TYPE_CHECKING:
    from .cli import TuiApp


class CommandSuggester(Suggester):
    """Suggester that provides inline hints for commands."""

    def __init__(self, app: TuiApp) -> None:
        super().__init__(use_cache=False, case_sensitive=False)
        self.app = app

    async def get_suggestion(self, value: str) -> str | None:
        """Return completion suggestion for the current input."""
        if not value.startswith("/"):
            return None

        # Strip / and any trailing space
        cmd_path = value[1:].rstrip()
        if not cmd_path:
            return None

        # Don't show hint if multiple suggestions are visible (user is mid-typing)
        if self.app.current_suggestions and len(self.app.current_suggestions) > 1:
            return None

        # Handle path ending with : (e.g., "/stats:")
        if cmd_path.endswith(":"):
            parent_path = cmd_path[:-1]
            cmd = get_command_for_path(self.cli._group, parent_path)
            if isinstance(cmd, CommandGroup) and cmd.commands:
                first_sub = next(iter(cmd.commands.values()))
                return f"{value}{first_sub.name}"
            return None

        cmd = get_command_for_path(self.cli._group, cmd_path)
        if cmd is None:
            return None

        if isinstance(cmd, CommandGroup) and cmd.commands:
            # Don't show subcommand suggestion if user typed a space
            if value.endswith(" "):
                return None
            # Show first subcommand
            first_sub = next(iter(cmd.commands.values()))
            return f"{value}:{first_sub.name}"
        elif isinstance(cmd, Command) and cmd.positional_args:
            # Show first positional arg placeholder
            if value.endswith(" "):
                return f"{value}<{cmd.positional_args[0].name}>"
            else:
                return f"{value} <{cmd.positional_args[0].name}>"

        return None
