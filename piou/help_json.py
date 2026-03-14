from __future__ import annotations

import json
import re
import sys
from types import NoneType, UnionType
from typing import Any, Literal, Union, get_args, get_origin

from .command import Command, CommandGroup
from .utils import CommandOption, run_function


def print_help_json(
    group: CommandGroup,
    command: Command | None,
    resolve_choices: bool,
):
    """Print JSON schema of CLI to stdout."""
    if command:
        data = _serialize_command(command, resolve_choices)
    else:
        data = _serialize_group(group, resolve_choices)
    json.dump(data, sys.stdout, indent=2, default=str)
    print()


def _serialize_group(group: CommandGroup, resolve_choices: bool) -> dict[str, Any]:
    result: dict[str, Any] = {"name": group.name}
    if group.help:
        result["help"] = group.help
    if group.description:
        result["description"] = group.description
    if group.options:
        result["options"] = [_serialize_option(o, resolve_choices) for o in group.options]
    commands: dict[str, Any] = {}
    for name, cmd in group.commands.items():
        if name == "__main__":
            continue
        if isinstance(cmd, CommandGroup):
            commands[name] = _serialize_group(cmd, resolve_choices)
        else:
            commands[name] = _serialize_command(cmd, resolve_choices)
    if commands:
        result["commands"] = commands
    return result


def _serialize_command(cmd: Command, resolve_choices: bool) -> dict[str, Any]:
    result: dict[str, Any] = {"name": cmd.name}
    if cmd.help:
        result["help"] = cmd.help
    if cmd.description:
        result["description"] = cmd.description
    if cmd.options:
        result["arguments"] = [_serialize_option(o, resolve_choices) for o in cmd.options_sorted]
    return result


def _serialize_option(opt: CommandOption, resolve_choices: bool) -> dict[str, Any]:
    result: dict[str, Any] = {"name": opt.name, "type": _type_name(opt.data_type)}
    if opt.keyword_args:
        result["flags"] = list(opt.keyword_args)
    if opt.negative_flag:
        result["negative_flag"] = opt.negative_flag
    result["required"] = opt.is_required
    if not opt.is_required and not opt.is_secret:
        result["default"] = opt.default
    if opt.help:
        result["help"] = opt.help
    if not opt.hide_choices:
        choices = _get_choices(opt, resolve_choices)
        if choices:
            if isinstance(choices, str):
                result["choices"] = choices
            else:
                result["choices"] = [str(c) if isinstance(c, re.Pattern) else c for c in choices]
    if opt.is_positional_arg:
        result["positional"] = True
    return result


def _get_choices(opt: CommandOption, resolve: bool) -> list | str | None:
    if opt.literal_values:
        return opt.literal_values
    if opt.choices is None:
        return None
    if callable(opt.choices):
        if not resolve:
            return "<dynamic>"
        return run_function(opt.choices)
    return opt.choices


def _type_name(t: type) -> str:
    origin = get_origin(t)
    if origin is Union or origin is UnionType:
        args = [a for a in get_args(t) if a is not NoneType]
        if len(args) == 1:
            return _type_name(args[0])
        return " | ".join(_type_name(a) for a in args)
    if origin is Literal:
        args = get_args(t)
        if args:
            return type(args[0]).__name__
    return getattr(t, "__name__", str(t))
