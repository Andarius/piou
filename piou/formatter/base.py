import shutil
import traceback
from dataclasses import dataclass
from difflib import get_close_matches
from typing import Callable

from ..command import Command, CommandOption, ParentArgs, CommandGroup
from .utils import get_program_name, fmt_option_raw, fmt_cmd_options_raw, fmt_help


def get_str_side_by_side(a: str, b: str, col_1_size: int, col_2_size: int, space: int):
    """Yield lines of two strings side by side, formatted to fit in specified column sizes."""
    while a or b:
        yield f"{a[:col_1_size].ljust(col_1_size):<{col_1_size + space}}{b[:col_2_size]}"
        a = a[col_1_size:]
        b = b[col_2_size:]


def print_size_by_size(
    print_fn: Callable,
    *args,
    col_1_size: int = 20,
    col_2_size: int = 100,
    space: int = 4,
):
    """Prints the given arguments side by side, formatted to fit in specified column sizes."""
    for arg in args:
        if isinstance(arg, str):
            print_fn(arg)
        else:
            _args = [arg] if isinstance(arg, tuple) else arg
            for x in _args:
                for line in get_str_side_by_side(*x, col_1_size=col_1_size, col_2_size=col_2_size, space=space):
                    print_fn(line)


def get_usage(
    global_options: list[CommandOption],
    command: str | None = None,
    command_options: list[CommandOption] | None = None,
    parent_args: ParentArgs | None = None,
):
    """Generate the usage string for a command or command group."""
    parent_args = parent_args or []
    _global_options = " ".join(["[" + sorted(x.keyword_args)[-1] + "]" for x in global_options])
    _command = None
    if command != "__main__":
        _command = command if command else "<command>"

    cmds = [get_program_name()] + [x.cmd for x in parent_args]
    cmds_str = " ".join(cmds)

    usage = cmds_str

    if _global_options:
        usage = f"{usage} {_global_options}"
    usage = f"{usage} {_command}" if _command is not None else usage
    if command_options:
        usage = f"{usage} {fmt_cmd_options_raw(command_options)}"

    return usage


def get_options_str(
    options: list[CommandOption],
) -> list[tuple[str | None, str, CommandOption]]:
    """Returns a list of tuples containing the name, other arguments, and the option itself."""
    lines = []
    for _option in options:
        if len(_option.keyword_args) == 0:
            name = None
            other_args = None
        else:
            name, *other_args = _option.keyword_args
            other_args = " (" + ", ".join(other_args) + ")" if other_args else ""

        lines.append((name, other_args, _option))
    return lines


@dataclass(frozen=True)
class Titles:
    """Titles used in the formatter for different sections of the help output."""

    GLOBAL_OPTIONS = "GLOBAL OPTIONS"
    AVAILABLE_CMDS = "AVAILABLE COMMANDS"
    COMMANDS = "COMMANDS"
    USAGE = "USAGE"
    DESCRIPTION = "DESCRIPTION"
    ARGUMENTS = "ARGUMENTS"
    OPTIONS = "OPTIONS"


@dataclass
class Formatter:
    """Base class for formatting command line interface (CLI) help output."""

    print_fn: Callable = print
    col_size: int = 20
    col_space: int = 4
    show_default: bool = True

    def print_rows(self, *args):
        columns, _ = shutil.get_terminal_size()
        return print_size_by_size(
            self.print_fn,
            *args,
            col_1_size=self.col_size,
            col_2_size=columns - self.col_size - self.col_space,
            space=self.col_space,
        )

    def print_help(
        self,
        *,
        group: CommandGroup,
        command: Command | None = None,
        parent_args: ParentArgs | None = None,
    ) -> None:
        # We are printing a command help
        if command:
            self.print_cmd_help(command, group.options, parent_args)
        # In case we are printing help for a command group
        elif parent_args:
            self.print_cmd_group_help(group, parent_args)
        # We are printing the CLI help
        else:
            self.print_cli_help(group)

    def _fmt_help(self, option: CommandOption) -> str | None:
        return fmt_help(option, self.show_default)

    def _print_options(self, options: list[CommandOption]):
        for name, other_args, opt in get_options_str(options):
            if name:
                opt_str = f"{name}{other_args or ''}"
                if opt.is_required:
                    opt_str += "*"
            else:
                opt_str = f"<{opt.name}>"

            help_str = self._fmt_help(opt) or ""
            self.print_fn(f"  {opt_str}")
            if help_str:
                for line in help_str.split("\n"):
                    self.print_fn(f"      {line}")

    def _print_description(self, item: CommandGroup | Command):
        description = item.description or item.help
        if description:
            self.print_fn()
            self.print_fn(Titles.DESCRIPTION)
            for line in description.split("\n"):
                self.print_fn(f"  {line}")

    def print_cli_help(self, group: CommandGroup) -> None:
        self.print_fn(Titles.USAGE)
        self.print_fn(f"  {get_usage(group.options)}")
        self.print_fn()

        if group.options:
            self.print_fn(Titles.GLOBAL_OPTIONS)
            self._print_options(group.options)
            self.print_fn()

        self.print_fn(Titles.AVAILABLE_CMDS)
        for _command in group.commands.values():
            cmd_name = _command.name or ""
            help_str = _command.help or ""
            self.print_fn(f"  {cmd_name}")
            if help_str:
                self.print_fn(f"      {help_str}")

        self._print_description(group)

    def print_cmd_group_help(self, group: CommandGroup, parent_args: ParentArgs) -> None:
        parent_commands = [get_program_name()] + [x.cmd for x in parent_args]
        commands_str = []
        for i, (cmd_name, cmd) in enumerate(group.commands.items()):
            _cmds = []
            for cmd_lvl, x in enumerate(parent_commands + [cmd_name]):
                _cmds.append(x)
                if group.options and cmd_lvl == len(parent_commands) - 1:
                    _cmds.append(fmt_cmd_options_raw(group.options))
            _cmds_str = " ".join(_cmds)
            _line = f"{'' if i == 0 else 'or: ':>5}{_cmds_str} {fmt_cmd_options_raw(cmd.options_sorted)}".rstrip()
            commands_str.append(_line)
        commands_output = "\n".join(commands_str)

        self.print_fn(Titles.USAGE)
        self.print_fn(commands_output)
        self.print_fn()

        self.print_fn(Titles.COMMANDS)
        for cmd_name, cmd in group.commands.items():
            self.print_fn(f"  {cmd_name}")
            if cmd.help:
                self.print_fn(f"    {cmd.help}")
                self.print_fn()
            if cmd.options:
                for opt in cmd.options_sorted:
                    opt_str = fmt_option_raw(opt, show_full=True)
                    self.print_fn(f"    {opt_str}")
                    help_str = self._fmt_help(opt)
                    if help_str:
                        for line in help_str.split("\n"):
                            self.print_fn(f"        {line}")
                self.print_fn()

        if group.options:
            self.print_fn(Titles.OPTIONS)
            self._print_options(group.options)
            self.print_fn()

        global_options = [parent_option for parent_arg in (parent_args or []) for parent_option in parent_arg.options]
        if global_options:
            self.print_fn(Titles.GLOBAL_OPTIONS)
            self._print_options(global_options)

        self._print_description(group)

    def print_cmd_help(
        self,
        command: Command,
        options: list[CommandOption],
        parent_args: ParentArgs | None = None,
    ) -> None:
        usage = get_usage(
            global_options=options,
            command=command.name,
            command_options=command.options_sorted,
            parent_args=parent_args,
        )
        self.print_fn(Titles.USAGE)
        self.print_fn(f"  {usage}")
        self.print_fn()

        if command.positional_args:
            self.print_fn(Titles.ARGUMENTS)
            for option in command.positional_args:
                self.print_fn(f"  <{option.name}>")
                help_str = self._fmt_help(option)
                if help_str:
                    for line in help_str.split("\n"):
                        self.print_fn(f"      {line}")

        if command.keyword_args:
            self.print_fn()
            self.print_fn(Titles.OPTIONS)
            self._print_options(command.keyword_args)

        global_options = options + [
            parent_option for parent_arg in (parent_args or []) for parent_option in parent_arg.options
        ]
        if global_options:
            self.print_fn()
            self.print_fn(Titles.GLOBAL_OPTIONS)
            self._print_options(global_options)

        self._print_description(command)

    def print_invalid_command(self, available_commands: list[str], input_command: str | None = None) -> None:
        msg = "Unknown command"
        if input_command:
            msg = f"Unknown command {input_command!r}"
            suggestions = get_close_matches(input_command, available_commands, n=1, cutoff=0.6)
            if suggestions:
                msg += f". Did you mean {suggestions[0]!r}?"
        _available_cmds = ", ".join(available_commands)
        self.print_fn(f'{msg}. Possible commands are "{_available_cmds}"')

    def print_param_error(self, key: str, cmd: str) -> None:
        self.print_fn(f"Could not find value for {key!r} in command {cmd!r}")

    def print_keyword_param_error(self, cmd: str, param: str) -> None:
        self.print_fn(f"Could not find keyword parameter {param!r} for command {cmd!r}")

    def print_count_error(self, expected_count: int, count: int, cmd: str) -> None:
        self.print_fn(f"Expected {expected_count} positional arguments but got {count} for command {cmd!r}")

    def print_invalid_value_error(
        self, value: str, literal_choices: list[str], regex_patterns: list[str] | None = None
    ) -> None:
        parts = []
        if literal_choices:
            parts.append("Possible values are:")
            parts.extend(f" - {choice}" for choice in literal_choices)
        if regex_patterns:
            parts.append("Or matching patterns:")
            parts.extend(f" - /{pattern}/" for pattern in regex_patterns)
        if parts:
            msg = f"Invalid value {value!r} found.\n" + "\n".join(parts)
        else:
            msg = f"Invalid value {value!r} found."
        self.print_fn(msg)

    def print_error(self, message: str) -> None:
        self.print_fn(message)

    def print_exception(self, exc: BaseException, *, hide_internals: bool = True) -> None:
        """Print an exception traceback.

        Args:
            exc: The exception to print
            hide_internals: If True, hide piou internal frames from the traceback
        """
        # Base implementation just prints the full traceback
        traceback.print_exception(type(exc), exc, exc.__traceback__)
