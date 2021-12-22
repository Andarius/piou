import sys
from dataclasses import dataclass, field

from rich import box
from rich.console import Console
from rich.table import Table, PaddingDimensions

from .base import Formatter
from ..command import Command, CommandOption, ParentArgs


def _get_table(width: int = 15, padding: PaddingDimensions = (0, 1)) -> Table:
    table = Table(show_header=False, box=box.SIMPLE, padding=padding)
    table.add_column('option', style="cyan", width=width)
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


def fmt_option(option: CommandOption,
               show_full: bool = False) -> str:
    if option.is_positional_arg:
        return f'<{option.name}>'
    elif show_full:
        first_arg, *other_args = option.keyword_args
        if other_args:
            other_args = ', '.join(other_args)
            return f'{first_arg} [bright_white]({other_args})[/bright_white]'
        else:
            return first_arg
    else:
        return '[' + sorted(option.keyword_args)[-1] + ']'


def fmt_cmd_options(options: list[CommandOption]) -> str:
    return (' '.join([fmt_option(x) for x in options])
            if options else ''  # '[<arg1>] ... [<argN>]'
            )


def get_usage(global_options: list[CommandOption],
              command: str = None,
              command_options: list[CommandOption] = None,
              parent_args: ParentArgs = None):
    parent_args = parent_args or []

    _global_options = ' '.join(['[' + sorted(x.keyword_args)[-1] + ']' for x in global_options])
    command = f'[underline]{command}[/underline]' if command else '<command>'
    cmds = [sys.argv[0].split('/')[-1]] + [x[0] for x in parent_args]
    cmds = ' '.join(f'[underline]{x}[/underline]' for x in cmds)
    usage = f'[bright_white]{cmds} ' \
            f'{_global_options} ' \
            f'{command} ' \
            f'{fmt_cmd_options(command_options)} [/bright_white]\n'
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


@dataclass
class RichFormatter(Formatter):
    _console: Console = field(init=False,
                              default_factory=lambda: Console(markup=True, highlight=False))


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
                             commands: dict[str, Command],
                             global_options: list[CommandOption],
                             options: list[CommandOption],
                             parent_args: ParentArgs):

        parent_commands = [sys.argv[0].split('/')[-1]] + [x[0] for x in parent_args]
        commands_str = []
        for i, (cmd_name, cmd) in enumerate(commands.items()):
            _cmds = ''.join(
                f'[underline]{x}[/underline] ' + (
                    f'{fmt_cmd_options(options)} ' if cmd_lvl == len(parent_commands) - 1 else '')
                for cmd_lvl, x in enumerate(parent_commands + [cmd_name]))

            _line = f'{"" if i == 0 else "or: ":>5}{_cmds}{fmt_cmd_options(cmd.options)}'
            commands_str.append(_line)
        commands_str = '\n'.join(commands_str)

        self._console.print(f'{_USAGE_STR}\n[bright_white]{commands_str}[/bright_white]\n')
        self._console.print(f'[bright_white]{_CMD_STR}[/bright_white]')
        for cmd_name, cmd in commands.items():
            self._console.print(f'  [underline]{cmd_name}[/underline]')
            self._console.print(f'    {cmd.help}')
            if cmd.options:
                table = _get_table(padding=(0, 3))
                for opt in cmd.options:
                    table.add_row(fmt_option(opt, show_full=True), opt.help)
                self._console.print(table)
        if options:
            self._console.print(_OPTIONS_STR, get_options_table(options))

        if global_options:
            self._console.print(_GLOBAL_OPTIONS_STR, get_options_table(global_options))

    def print_cmd_help(self,
                       command: Command,
                       options: list[CommandOption],
                       parent_args: ParentArgs = None):
        self._console.print(get_usage(
            global_options=options,
            command=command.name,
            command_options=command.options,
            parent_args=parent_args
        ))
        if command.positional_args:
            self._console.print(_ARGUMENTS_STR, get_arguments(command.positional_args))
        if command.keyword_args:
            self._console.print(_OPTIONS_STR, get_options_table(command.keyword_args))

        parent_options = [parent_option for parent_arg in (parent_args or []) for parent_option in parent_arg[1]]
        if options or parent_options:
            self._console.print(_GLOBAL_OPTIONS_STR, get_options_table(options + parent_options))
        if command.help:
            self._console.print(f'{_DESCRIPTION_STR}\n {command.help}\n')

    def print_cmd_error(self, cmd: str):
        self._console.print(f'[red]Unknown command "[bold]{cmd}[/bold]"[/red]')

    def print_param_error(self, key: str) -> None:
        self._console.print(f"[red]Could not find value for [bold]{key!r}[/bold][/red]")

    def print_count_error(self, expected_count: int, count: int):
        self._console.print(f'[red]Expected {expected_count} positional arguments but got {count}[/red]')
