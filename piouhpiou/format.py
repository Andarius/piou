from dataclasses import dataclass, field
from rich import box
from rich.console import Console
from rich.table import Table
from typing import List

from .command import Command, Option


@dataclass
class RichFormatter:
    _console: Console = field(init=False, default=Console(markup=True))

    def print_help(self,
                   commands: dict[str, Command],
                   options: List[Option]):

        help = '[bold bright_white]GLOBAL OPTIONS[/bold bright_white]'
        table = Table(show_header=False, box=box.SIMPLE)
        table.add_column('Command name', style="cyan", width=15)
        table.add_column('Commend help')
        for _command in options:
            if len(_command.args) == 0:
                name = _command.args
            else:
                first_arg, *other_args = _command.args
                other_args = ', '.join(other_args)
                name = f'{first_arg} [bright_white]({other_args})[/bright_white]'
            table.add_row(name, _command.help)
        self._console.print(help, table)

        help = '[bold bright_white]AVAILABLE COMMANDS[/bold bright_white]'
        table = Table(show_header=False, box=box.SIMPLE)
        table.add_column('Command name', style="cyan", width=15)
        table.add_column('Commend help')
        for _command in commands.values():
            table.add_row(_command.name, _command.help)
        self._console.print(help, table)

    def print_cmd_error(self, cmd: str):
        self._console.print(f'[red]Unknown command "[bold]{cmd}[/bold]"[/red]')
