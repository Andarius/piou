from types import NoneType, UnionType
from typing import Union, get_args, get_origin

from rich.text import Text

from ..command import Command, CommandGroup

__all__ = ("get_command_help",)


def _format_type_name(t: type) -> str:
    """Format a type for display, handling Union types nicely."""
    origin = get_origin(t)
    if origin is Union or origin is UnionType:
        args = [a for a in get_args(t) if a is not NoneType]
        if len(args) == 1:
            return _format_type_name(args[0])
        return " | ".join(_format_type_name(a) for a in args)
    return getattr(t, "__name__", str(t))


def _build_command_help(cmd: Command, display_name: str) -> Text:
    """Build help text for a Command."""
    text = Text()

    # Description (from docstring)
    if cmd.description:
        text.append(cmd.description)
        text.append("\n\n")

    # Usage line
    args_parts = []
    for opt in cmd.positional_args:
        args_parts.append(f"<{opt.name}>")
    for opt in cmd.keyword_args:
        arg_name = sorted(opt.keyword_args)[-1]
        if opt.is_required:
            args_parts.append(f"{arg_name} <value>")
        else:
            args_parts.append(f"[{arg_name}]")

    text.append("Usage:", style="bold")
    if args_parts:
        text.append(f" /{display_name} {' '.join(args_parts)}")
    else:
        text.append(f" /{display_name}")

    # Arguments section
    if cmd.positional_args:
        text.append("\n\n")
        text.append("Arguments:", style="bold")
        for opt in cmd.positional_args:
            type_name = _format_type_name(opt.data_type)
            text.append("\n  ")
            text.append(f"<{opt.name}>", style="cyan")
            text.append(f" ({type_name})")
            if opt.help:
                text.append(f" - {opt.help}")

    # Options section
    if cmd.keyword_args:
        text.append("\n\n")
        text.append("Options:", style="bold")
        for opt in cmd.keyword_args:
            arg_display = ", ".join(sorted(opt.keyword_args))
            type_name = _format_type_name(opt.data_type)
            text.append("\n  ")
            text.append(arg_display, style="cyan")
            text.append(f" ({type_name})")
            if opt.is_required:
                text.append(" *required", style="red")
            elif opt.default is not None:
                text.append(f" (default: {opt.default})")
            if opt.help:
                text.append(f" - {opt.help}")
            choices = opt.literal_values or (opt.choices if not callable(opt.choices) else None)
            if choices and not opt.hide_choices:
                if len(choices) <= 10:
                    choices_str = ", ".join(str(c) for c in choices)
                    text.append(f" (choices are: {choices_str})", style="yellow")
                else:
                    text.append(f" ({len(choices)} choices, use Tab to complete)", style="yellow")

    return text


def _build_group_help(group: CommandGroup, display_name: str) -> Text:
    """Build help text for a CommandGroup."""
    text = Text()

    text.append("Usage:", style="bold")
    text.append(f" /{display_name}:<subcommand>")

    if group.commands:
        text.append("\n\n")
        text.append("Subcommands:", style="bold")
        for subcmd in group.commands.values():
            text.append("\n  ")
            text.append(subcmd.name, style="cyan")
            if subcmd.help:
                text.append(f" - {subcmd.help}")

    return text


def get_command_help(cmd: Command | CommandGroup, path: str = "") -> Text:
    """Format command help for display in the help widget.

    Builds Rich Text directly for performance (avoids console.print + from_ansi
    round-trip).
    """
    display_name = path.lstrip("/") if path else cmd.name
    if not display_name:
        raise ValueError("Cannot generate help for command without a name")

    if isinstance(cmd, Command):
        return _build_command_help(cmd, display_name)
    return _build_group_help(cmd, display_name)
