import sys
from dataclasses import dataclass, field
from typing import Optional

from rich import box
from rich.console import Console
from rich.table import Table

from .base import Formatter
from ..command import Command, CommandOption


def _get_table() -> Table:
    table = Table(show_header=False, box=box.SIMPLE)
    table.add_column('option', style="cyan", width=15)
    table.add_column('option_name')
    return table


def get_options_table(options: list[CommandOption]) -> Table:
    table = _get_table()
    for _command in options:
        if len(_command.keyword_args) == 0:
            name = None
        else:
            first_arg, *other_args = _command.keyword_args
            if other_args:
                other_args = ', '.join(other_args)
                name = f'{first_arg} [bright_white]({other_args})[/bright_white]'
            else:
                name = first_arg
        table.add_row(name, _command.help)
    return table


def fmt_option(option: CommandOption) -> str:
    if option.is_positional_arg:
        return f'<{option.name}>'
    else:
        return '[' + sorted(option.keyword_args)[-1] + ']'


def get_usage(global_options: list[CommandOption],
              command: str = None,
              command_options: list[CommandOption] = None):
    _global_options = ' '.join(['[' + sorted(x.keyword_args)[-1] + ']' for x in global_options])
    _command_options = (' '.join([fmt_option(x) for x in command_options])
                        if command_options else ''# '[<arg1>] ... [<argN>]'
                        )
    command = f'[underline]{command}[/underline]' if command else '<command>'
    usage = f'[bright_white][underline]{sys.argv[0]}[/underline] ' \
            f'{_global_options} ' \
            f'{command} ' \
            f'{_command_options} [/bright_white]\n'
    return f'{_USAGE_STR}\n {usage}'


def get_arguments(options: list[CommandOption]) -> Table:
    table = _get_table()
    for option in options:
        if option.is_positional_arg:
            table.add_row(fmt_option(option), option.help)
    return table


_GLOBAL_OPTIONS_STR = '[bold bright_white]GLOBAL OPTIONS[/bold bright_white]'
_AVAILABLE_CMDS_STR = '[bold bright_white]AVAILABLE COMMANDS[/bold bright_white]'
_CMD_STR = '[bold bright_white]COMMANDS[/bold bright_white]'
_USAGE_STR = '[bold bright_white]USAGE[/bold bright_white]'
_DESCRIPTION_STR = f'[bold bright_white]DESCRIPTION[/bold bright_white]'
_ARGUMENTS_STR = f'[bold bright_white]ARGUMENTS[/bold bright_white]'
_OPTIONS_STR = '[bold bright_white]OPTIONS[/bold bright_white]'


def fmt_options(options: list[CommandOption]) -> str:
    print(options)
    return ''


@dataclass
class RichFormatter(Formatter):
    _console: Console = field(init=False, default=Console(markup=True, highlight=False))

    def print_cli_help(self,
                       commands: dict[str, Command],
                       options: list[CommandOption],
                       help: str = None):
        self._console.print(get_usage(options))
        self._console.print(_GLOBAL_OPTIONS_STR,
                            get_options_table(options))

        table = Table(show_header=False, box=box.SIMPLE)
        table.add_column('Command name', style="cyan", width=15)
        table.add_column('Command help')
        for _command in commands.values():
            table.add_row(_command.name, _command.help)
        self._console.print(_AVAILABLE_CMDS_STR, table)
        if help:
            self._console.print(f'{_DESCRIPTION_STR}\n {help}\n')

    def print_cmd_group_help(self,
                             command: Command,
                             commands: dict[str, Command],
                             options: list[CommandOption]):
        # Usage
        # Commands
        # Global Options
        commands_str = '\n'.join(f'[underline]{command.name}[/underline] '
                                 f'[underline]{cmd_name}[/underline] '
                                 f'{fmt_options(cmd.options)}'
                                 for cmd_name, cmd in commands.items())
        self._console.print(f'{_USAGE_STR}\n[bright_white]{commands_str}[/bright_white]')

    def print_cmd_help(self, command: Command, options: list[CommandOption]):
        self._console.print(get_usage(
            global_options=options,
            command=command.name,
            command_options=command.options
        ))
        if command.positional_args:
            self._console.print(_ARGUMENTS_STR, get_arguments(command.positional_args))
        if command.keyword_args:
            self._console.print(_OPTIONS_STR, get_options_table(command.keyword_args))
        if options:
            self._console.print(_GLOBAL_OPTIONS_STR, get_options_table(options))
        if command.help:
            self._console.print(f'{_DESCRIPTION_STR}\n {command.help}\n')

    def print_cmd_error(self, cmd: str):
        self._console.print(f'[red]Unknown command "[bold]{cmd}[/bold]"[/red]')

    def print_param_error(self, key: str) -> None:
        self._console.print(f"[red]Could not find value for [bold]{key!r}[/bold][/red]")

    def print_count_error(self, expected_count: int, count: int):
        self._console.print(f'[red]Expected {expected_count} positional arguments but got {count}[/red]')
