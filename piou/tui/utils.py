from types import UnionType, NoneType
from typing import get_origin, Union, get_args

from rich.console import Console
from rich.text import Text

from ..command import Command, CommandGroup

__all__ = ("get_command_for_path", "get_command_help")

_RENDER_CONSOLE = Console(force_terminal=True, markup=True, highlight=False)


def get_command_for_path(group: CommandGroup, path: str) -> Command | CommandGroup | None:
    """
    Get command/group for a command paths like 'stats' or 'stats:uploads'
    """
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


def _format_type_name(t: type) -> str:
    """Format a type for display, handling Union types nicely."""
    origin = get_origin(t)
    if origin is Union or origin is UnionType:
        args = [a for a in get_args(t) if a is not NoneType]
        if len(args) == 1:
            return _format_type_name(args[0])
        return " | ".join(_format_type_name(a) for a in args)
    return getattr(t, "__name__", str(t))


def get_command_help(cmd: Command | CommandGroup, console: Console = _RENDER_CONSOLE) -> Text:
    """Format command help for display in the help widget.

    Example output for a Command:

    ```
    Usage: /greet <name> [--loud]

    Arguments:
      <name> (str) - Name to greet

    Options:
      -l, --loud (bool) (default: False) - Shout the greeting
    ```

    Example output for a CommandGroup:

    ```
    Usage: /stats:<subcommand>

    Subcommands:
      uploads - Show upload statistics
      downloads - Show download statistics
    ```
    """
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
                type_name = _format_type_name(opt.data_type)
                help_text = f" - {opt.help}" if opt.help else ""
                lines.append(f"  [cyan]<{opt.name}>[/cyan] ({type_name}){help_text}")

        # Options section
        if cmd.keyword_args:
            lines.append("")
            lines.append("[bold]Options:[/bold]")
            for opt in cmd.keyword_args:
                arg_display = ", ".join(sorted(opt.keyword_args))
                type_name = _format_type_name(opt.data_type)
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
    with console.capture() as capture:
        for line in lines:
            console.print(line)
    return Text.from_ansi(capture.get().rstrip())


def get_subcommand_suggestions(group: CommandGroup, query: str) -> list[tuple[str, str]]:
    """Get subcommand suggestions for a command path like 'stats:' or 'stats:up'.

    Args:
        group: The root CommandGroup to search from.
        query: The query string (e.g., "stats:" or "stats:up").

    Returns:
        List of (full_path, help_text) tuples for matching subcommands.

    Example:

    ```python
    get_subcommand_suggestions(root_group, "stats:")
    # [("/stats:uploads", "Show upload statistics"), ("/stats:downloads", "")]
    ```
    """
    parts = query.split(":")
    prefix = ":".join(parts[:-1])  # e.g., "stats" for "stats:up"
    subquery = parts[-1].lower()  # e.g., "up" for "stats:up"

    # Get the parent CommandGroup using existing helper
    parent = get_command_for_path(group, prefix)
    if not isinstance(parent, CommandGroup):
        return []

    # Collect matching subcommands
    suggestions = []
    for cmd in parent.commands.values():
        if subquery == "" or cmd.name.lower().startswith(subquery):
            full_path = f"/{prefix}:{cmd.name}"
            suggestions.append((full_path, cmd.help or ""))

    return suggestions
