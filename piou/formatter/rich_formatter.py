from dataclasses import dataclass, field

from rich import box
from rich.console import Console
from rich.table import Table

from .base import Formatter
from ..command import Command, Option


def get_options_table(options: list[Option]) -> Table:
    table = Table(show_header=False, box=box.SIMPLE)
    table.add_column('option', style="cyan", width=15)
    table.add_column('option_name')
    for _command in options:
        if len(_command.args) == 0:
            name = None
        else:
            first_arg, *other_args = _command.args
            if other_args:
                other_args = ', '.join(other_args)
                name = f'{first_arg} [bright_white]({other_args})[/bright_white]'
            else:
                name = first_arg
        table.add_row(name, _command.help)
    return table


@dataclass
class RichFormatter(Formatter):
    _console: Console = field(init=False, default=Console(markup=True))

    def print_help(self,
                   commands: dict[str, Command],
                   options: list[Option]):

        _help = '[bold bright_white]GLOBAL OPTIONS[/bold bright_white]'
        self._console.print(_help, get_options_table(options))

        _help = '[bold bright_white]AVAILABLE COMMANDS[/bold bright_white]'
        table = Table(show_header=False, box=box.SIMPLE)
        table.add_column('Command name', style="cyan", width=15)
        table.add_column('Command help')
        for _command in commands.values():
            table.add_row(_command.name, _command.help)
        self._console.print(_help, table)

    def print_cmd_help(self, command: Command, options: list[Option]):
        _help = '[bold bright_white]OPTIONS[/bold bright_white]'
        self._console.print(_help, get_options_table(command.options))

    def print_cmd_error(self, cmd: str):
        self._console.print(f'[red]Unknown command "[bold]{cmd}[/bold]"[/red]')

    def print_param_error(self, key: str) -> None:
        self._console.print(f'[red]Could not find value for "[bold]{key}[/bold]"[/red]')

    def print_count_error(self, expected_count: int, count: int):
        self._console.print(f'[red]Expected {expected_count} positional arguments but got {count}[/red]')
