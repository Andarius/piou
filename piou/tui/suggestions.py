from __future__ import annotations

from ..command import Command, CommandGroup

__all__ = (
    "get_command_for_path",
    "get_command_suggestions",
    "get_subcommand_suggestions",
)


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
