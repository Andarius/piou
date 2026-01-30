from __future__ import annotations

from typing import TYPE_CHECKING

from textual.suggester import Suggester

from ..command import Command, CommandGroup

if TYPE_CHECKING:
    from .app import TuiApp

__all__ = (
    "CommandSuggester",
    "get_command_for_path",
    "get_command_suggestions",
    "get_subcommand_suggestions",
)


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
            cmd = get_command_for_path(self.app.state.group, parent_path)
            if isinstance(cmd, CommandGroup) and cmd.commands:
                first_sub = next(iter(cmd.commands.values()))
                return f"{value}{first_sub.name}"
            return None

        cmd = get_command_for_path(self.app.state.group, cmd_path)
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


def get_command_for_path(group: CommandGroup, path: str) -> Command | CommandGroup | None:
    """Get command/group for a command path like 'stats' or 'stats:uploads'."""
    parts = path.lstrip("/").split(":")
    current = group
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


def get_command_suggestions(
    commands: list[Command | CommandGroup],
    query: str,
) -> list[tuple[str, str]]:
    """Get top-level command suggestions matching a query.

    Returns list of (command_path, help_text) tuples. The built-in /help command
    is included automatically.
    """
    suggestions: list[tuple[str, str]] = []

    # Add built-in /help command
    if query == "" or "help".startswith(query):
        suggestions.append(("/help", "Show available commands"))

    # Add CLI commands
    for cmd in commands:
        if cmd.name and (query == "" or cmd.name.lower().startswith(query)):
            suggestions.append((f"/{cmd.name}", cmd.help or ""))

    return suggestions


def get_subcommand_suggestions(group: CommandGroup, query: str) -> list[tuple[str, str]]:
    """Get subcommand suggestions for a command path like 'stats:' or 'stats:up'.

    Returns list of (full_path, help_text) tuples for matching subcommands.
    """
    parts = query.split(":")
    prefix = ":".join(parts[:-1])  # e.g., "stats" for "stats:up"
    subquery = parts[-1].lower()  # e.g., "up" for "stats:up"

    parent = get_command_for_path(group, prefix)
    if not isinstance(parent, CommandGroup):
        return []

    suggestions = []
    for cmd in parent.commands.values():
        if cmd.name and (subquery == "" or cmd.name.lower().startswith(subquery)):
            full_path = f"/{prefix}:{cmd.name}"
            suggestions.append((full_path, cmd.help or ""))

    return suggestions
