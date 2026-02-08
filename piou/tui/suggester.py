from __future__ import annotations

import shlex
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from textual.suggester import Suggester

from ..command import Command, CommandGroup
from ..utils import CommandOption

try:
    import watchfiles  # noqa: F401

    _WATCHFILES_AVAILABLE = True
except ImportError:
    _WATCHFILES_AVAILABLE = False

if TYPE_CHECKING:
    from .app import TuiApp

__all__ = (
    "CommandSuggester",
    "OptionContext",
    "SuggestionState",
    "get_command_for_path",
    "get_command_suggestions",
    "get_subcommand_suggestions",
    "get_value_suggestions",
    "parse_option_context",
)


@dataclass
class SuggestionState:
    index: int = -1
    items: list[str] = field(default_factory=list)
    value_prefix: str | None = None

    def reset(self) -> None:
        self.index = -1
        self.items.clear()
        self.value_prefix = None


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
        if self.app.suggestions.items and len(self.app.suggestions.items) > 1:
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
        elif isinstance(cmd, Command):
            if cmd.positional_args:
                # Check if we're still on positional args (no flags typed yet)
                parts = value[1:].split(None, 1)
                args_text = parts[1] if len(parts) > 1 else ""
                has_flag = any(t.startswith("-") for t in args_text.split())
                if not has_flag:
                    if value.endswith(" "):
                        return f"{value}<{cmd.positional_args[0].name}>"
                    else:
                        return f"{value} <{cmd.positional_args[0].name}>"

            # Skip inline value hint — the ValuePicker handles this
            if self.app.suggestions.value_prefix is not None:
                return None

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

    # Add built-in commands
    if query == "" or "help".startswith(query):
        suggestions.append(("/help", "Show available commands"))
    if _WATCHFILES_AVAILABLE and (query == "" or "tui-reload".startswith(query)):
        suggestions.append(("/tui-reload", "Toggle auto-reload on file changes"))

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


@dataclass
class OptionContext:
    """Context for an in-progress option value in the input."""

    option: CommandOption
    partial: str
    prefix: str


def parse_option_context(command: Command, args_text: str) -> OptionContext | None:
    """Parse the current input to find which option value is being typed.

    Returns an OptionContext if the cursor is on a keyword option value that has
    choices or literal values, otherwise None.
    """
    flag_map, bool_flags, neg_flags = command.flag_maps

    trailing_space = args_text.endswith(" ")

    try:
        tokens = shlex.split(args_text)
    except ValueError:
        return None

    # Walk tokens to find current option context
    current_option: CommandOption | None = None
    expecting_value = False

    for token in tokens:
        if token.startswith("-"):
            # Reset any pending option
            current_option = None
            expecting_value = False

            if token in neg_flags or token in bool_flags:
                # Bool/negative flags take no value
                continue

            if token in flag_map:
                current_option = flag_map[token]
                expecting_value = True
            # Unknown flag — ignore
        else:
            if expecting_value:
                # This token is the value for current_option
                expecting_value = False
                # Don't reset current_option yet — we need it if this is a partial
            else:
                # Positional arg
                current_option = None

    # Determine context based on state
    if expecting_value and trailing_space:
        # Flag was typed with trailing space but no value yet: "-s "
        # partial is empty
        option = current_option
        partial = ""
    elif expecting_value and not trailing_space and tokens:
        # Flag is the last token with no space: "-s" — user hasn't started typing value
        # No context to complete (they need to add a space first)
        return None
    elif not expecting_value and current_option is not None and not trailing_space and tokens:
        # Just finished typing a partial value: "-s up"
        option = current_option
        partial = tokens[-1]
    elif expecting_value and not tokens:
        return None
    else:
        return None

    if option is None:
        return None

    # Check that option has completable choices
    if option.hide_choices:
        return None
    if not option.literal_values and option.choices is None:
        return None

    # Compute prefix from raw args_text
    if partial:
        prefix = args_text[: len(args_text) - len(partial)]
    else:
        prefix = args_text if trailing_space else args_text + " "

    return OptionContext(option=option, partial=partial, prefix=prefix)


async def get_value_suggestions(ctx: OptionContext) -> list[tuple[str, str]]:
    """Get matching value suggestions for an option context."""
    choices = await ctx.option.async_get_choices()
    if not choices:
        return []

    case_sensitive = ctx.option.case_sensitive
    partial = ctx.partial if case_sensitive else ctx.partial.lower()

    results: list[tuple[str, str]] = []
    for choice in choices:
        choice_str = str(choice)
        cmp = choice_str if case_sensitive else choice_str.lower()
        if cmp.startswith(partial):
            results.append((choice_str, ""))

    return results
