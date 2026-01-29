from types import NoneType, UnionType
from typing import Union, get_args, get_origin

from rich.console import Console
from rich.text import Text

from ..command import Command, CommandGroup

__all__ = ("get_command_help",)

_RENDER_CONSOLE = Console(force_terminal=True, markup=True, highlight=False)


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

        if cmd.positional_args:
            lines.append("")
            lines.append("[bold]Arguments:[/bold]")
            for opt in cmd.positional_args:
                type_name = _format_type_name(opt.data_type)
                help_text = f" - {opt.help}" if opt.help else ""
                lines.append(f"  [cyan]<{opt.name}>[/cyan] ({type_name}){help_text}")

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
        lines.append(f"[bold]Usage:[/bold] /{cmd.name}:<subcommand>")
        if cmd.commands:
            lines.append("")
            lines.append("[bold]Subcommands:[/bold]")
            for subcmd in cmd.commands.values():
                help_text = f" - {subcmd.help}" if subcmd.help else ""
                lines.append(f"  [cyan]{subcmd.name}[/cyan]{help_text}")

    with console.capture() as capture:
        for line in lines:
            console.print(line)
    return Text.from_ansi(capture.get().rstrip())
