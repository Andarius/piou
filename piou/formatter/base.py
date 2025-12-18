import abc
import shutil
from dataclasses import dataclass
from typing import Callable

from ..command import Command, CommandOption, ParentArgs, CommandGroup


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
class Formatter(abc.ABC):
    """Base class for formatting command line interface (CLI) help output."""

    print_fn: Callable = print
    col_size: int = 20
    col_space: int = 4

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

    @abc.abstractmethod
    def print_cli_help(self, group: CommandGroup) -> None: ...

    @abc.abstractmethod
    def print_cmd_group_help(self, group: CommandGroup, parent_args: ParentArgs) -> None: ...

    @abc.abstractmethod
    def print_cmd_help(
        self,
        command: Command,
        options: list[CommandOption],
        parent_args: ParentArgs | None = None,
    ) -> None: ...

    def print_invalid_command(self, available_commands: list[str]) -> None:
        _available_cmds = ", ".join(available_commands)
        self.print_fn(f'Unknown command given. Possible commands are "{_available_cmds}"')

    def print_param_error(self, key: str, cmd: str) -> None:
        self.print_fn(f"Could not find value for {key!r} in command {cmd!r}")

    def print_keyword_param_error(self, cmd: str, param: str) -> None:
        self.print_fn(f"Could not find keyword parameter {param!r} for command {cmd!r}")

    def print_count_error(self, expected_count: int, count: int, cmd: str) -> None:
        self.print_fn(f"Expected {expected_count} positional arguments but got {count} for command {cmd!r}")

    def print_invalid_value_error(self, value: str, choices: list[str]) -> None:
        possible_fields = "\n" + "\n - ".join(_choice for _choice in choices)
        self.print_fn(f"Invalid value {value!r} found. Possible values are: {possible_fields}")

    def print_error(self, message: str) -> None:
        self.print_fn(message)
