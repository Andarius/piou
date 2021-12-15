from dataclasses import dataclass, field
from rich import box
from rich.console import Console
from rich.table import Table

from ..command import Command, Option
from .base import Formatter


@dataclass
class RichFormatter(Formatter):

    _console: Console = field(init=False, default=Console(markup=True))

    def print_help(self,
                   commands: dict[str, Command],
                   options: list[Option]):

        _help = '[bold bright_white]GLOBAL OPTIONS[/bold bright_white]'
        table = Table(show_header=False, box=box.SIMPLE)
        table.add_column('Command name', style="cyan", width=15)
        table.add_column('Command help')
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
        self._console.print(_help, table)

        _help = '[bold bright_white]AVAILABLE COMMANDS[/bold bright_white]'
        table = Table(show_header=False, box=box.SIMPLE)
        table.add_column('Command name', style="cyan", width=15)
        table.add_column('Command help')
        for _command in commands.values():
            table.add_row(_command.name, _command.help)
        self._console.print(_help, table)

    def print_cmd_error(self, cmd: str):
        self._console.print(f'[red]Unknown command "[bold]{cmd}[/bold]"[/red]')
