import abc
from dataclasses import dataclass
from typing import Optional

from ..command import Command, CommandOption, ParentArgs, CommandGroup


@dataclass
class Formatter(abc.ABC):

    def print_help(self, *,
                   commands: dict[str, Command],
                   options: list[CommandOption],
                   help: str = None,
                   command: Optional[Command] = None,
                   global_options: list[CommandOption] = None,
                   parent_args: ParentArgs = None
                   ) -> None:
        # We are printing a command help
        if command:
            self.print_cmd_help(command, options, parent_args)
        # In case we are printing help for a command group
        elif parent_args:
            self.print_cmd_group_help(commands, global_options, options,
                                      parent_args)
        # We are printing the CLI help
        else:
            self.print_cli_help(commands, options, help)

    @abc.abstractmethod
    def print_cli_help(self, commands: dict[str, Command],
                       options: list[CommandOption],
                       help: str = None) -> None:
        ...

    @abc.abstractmethod
    def print_cmd_group_help(self,
                             group: CommandGroup,
                             command_name: str,
                             commands: dict[str, Command],
                             global_options: list[CommandOption],
                             options: list[CommandOption],
                             parent_args: ParentArgs) -> None:
        ...

    @abc.abstractmethod
    def print_cmd_help(self,
                       command: Command,
                       options: list[CommandOption],
                       parent_args: ParentArgs = None) -> None:
        ...

    def print_cmd_error(self, cmd: str) -> None:
        print(f'Unknown command {cmd!r}')

    def print_param_error(self, key: str) -> None:
        print(f'Could not find value for {key!r}')

    def print_count_error(self, expected_count: int, count: int) -> None:
        print(f'Expected {expected_count} positional arguments but got {count}')
