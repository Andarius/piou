import abc
from dataclasses import dataclass
from typing import Optional

from ..command import Command, CommandOption


@dataclass
class Formatter(abc.ABC):

    def print_help(self, *,
                   commands: dict[str, Command],
                   options: list[CommandOption],
                   help: str = None,
                   command: Optional[Command] = None
                   ) -> None:
        if command is None:
            self.print_cli_help(commands, options, help)
        elif command and commands:
            self.print_cmd_group_help(command, commands, options)
        else:
            self.print_cmd_help(command, options)

    @abc.abstractmethod
    def print_cli_help(self, commands: dict[str, Command],
                       options: list[CommandOption],
                       help: str = None) -> None:
        ...

    @abc.abstractmethod
    def print_cmd_group_help(self, command: Command,
                             commands: dict[str, Command],
                             options: list[CommandOption]) -> None:
        ...

    @abc.abstractmethod
    def print_cmd_help(self,
                       command: Command,
                       options: list[CommandOption]) -> None:
        ...

    def print_cmd_error(self, cmd: str) -> None:
        print(f'Unknown command {cmd!r}')

    def print_param_error(self, key: str) -> None:
        print(f'Could not find value for {key!r}')

    def print_count_error(self, expected_count: int, count: int) -> None:
        print(f'Expected {expected_count} positional arguments but got {count}')
