import sys
from dataclasses import dataclass, field
from typing import Optional

from rich.console import Console
from rich.table import Table, Padding

from .base import Formatter, Titles, get_options_str
from ..command import Command, CommandOption, ParentArgs, CommandGroup


def pad(s: str, padding_left: int = 1):
    return Padding(s, (0, padding_left))


def fmt_option(option: CommandOption,
               show_full: bool = False,
               color: str = 'white') -> str:
    if option.is_positional_arg:
        return f'[{color}]<{option.name}>[/{color}]'
    elif show_full:
        first_arg, *other_args = option.keyword_args
        if other_args:
            other_args = ', '.join(other_args)
            return f'[{color}]{first_arg}[/{color}] ({other_args})'
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
    cmds = [sys.argv[0].split('/')[-1]] + [x.cmd for x in parent_args]
    cmds = ' '.join(f'[underline]{x}[/underline]' for x in cmds)

    usage = cmds
    if _global_options:
        usage = f'{usage} {_global_options}'
    usage = f'{usage} {command}'
    if command_options:
        usage = f'{usage} {fmt_cmd_options(command_options)}'

    return usage


@dataclass(frozen=True)
class RichTitles(Titles):
    GLOBAL_OPTIONS = f'[bold bright_white]{Titles.GLOBAL_OPTIONS}[/bold bright_white]'
    AVAILABLE_CMDS = f'[bold bright_white]{Titles.AVAILABLE_CMDS}[/bold bright_white]'
    COMMANDS = f'[bold bright_white]{Titles.COMMANDS}[/bold bright_white]'
    USAGE = f'[bold bright_white]{Titles.USAGE}[/bold bright_white]'
    DESCRIPTION = f'[bold bright_white]{Titles.DESCRIPTION}[/bold bright_white]'
    ARGUMENTS = f'[bold bright_white]{Titles.ARGUMENTS}[/bold bright_white]'
    OPTIONS = f'[bold bright_white]{Titles.OPTIONS}[/bold bright_white]'


@dataclass
class RichFormatter(Formatter):
    _console: Console = field(init=False,
                              default_factory=lambda: Console(markup=True, highlight=False))
    cmd_color: str = 'cyan'
    option_color: str = 'cyan'

    def _color_opt(self, opt: str):
        return f'[{self.option_color}]{opt}[/{self.option_color}]'

    def _color_cmd(self, cmd: str):
        return f'[{self.cmd_color}]{cmd}[/{self.cmd_color}]'

    def __post_init__(self):
        self.print_fn = self._console.print

    def _print_options(self, options: list[CommandOption]):
        self.print_rows([(self._color_opt(_name or '') + _other_args, _help)
                         for _name, _other_args, _help in get_options_str(options)])

    def print_rows(self, rows: list[tuple[str, Optional[str]]]):
        table = Table(show_header=False, box=None, padding=(0, self.col_space))
        table.add_column(width=self.col_size)
        table.add_column()
        for row in rows:
            table.add_row(*row)
        self.print_fn(table)

    def print_cli_help(self,
                       group: CommandGroup):
        self.print_fn(RichTitles.USAGE, '\n', get_usage(group.options), '\n')
        if group.options:
            self.print_fn(RichTitles.GLOBAL_OPTIONS)
            self._print_options(group.options)
            print()

        self.print_fn(RichTitles.AVAILABLE_CMDS)
        self.print_rows([(f' {self._color_cmd(_command.name or "")}', _command.help) for _command in
                         group.commands.values()])

        if group.help:
            self.print_fn(f"\n{RichTitles.DESCRIPTION}\n {group.help}\n")

    def print_cmd_help(self,
                       command: Command,
                       options: list[CommandOption],
                       parent_args: ParentArgs = None):
        usage = get_usage(
            global_options=options,
            command=command.name,
            command_options=command.options,
            parent_args=parent_args
        )
        self.print_fn(RichTitles.USAGE, '\n', usage, '\n')

        if command.positional_args:
            self.print_fn(RichTitles.ARGUMENTS)
            self.print_rows(
                [(fmt_option(option, color=self.option_color), option.help)
                 for option in command.positional_args])
        if command.keyword_args:
            self.print_fn('\n' + RichTitles.OPTIONS)
            self._print_options(command.keyword_args)

        global_options = options + [parent_option for parent_arg in (parent_args or [])
                                    for parent_option in parent_arg.options]
        if global_options:
            self.print_fn('\n' + RichTitles.GLOBAL_OPTIONS)
            self._print_options(global_options)
        if command.help:
            self.print_fn(f'\n{RichTitles.DESCRIPTION}\n {command.help}\n')

    def print_cmd_group_help(self,
                             group: CommandGroup,
                             parent_args: ParentArgs):

        parent_commands = [sys.argv[0].split('/')[-1]] + [x.cmd for x in parent_args]
        commands_str = []
        for i, (cmd_name, cmd) in enumerate(group.commands.items()):
            _cmds = ''.join(
                f'[underline]{x}[/underline] ' + (
                    f'{fmt_cmd_options(group.options)} ' if cmd_lvl == len(parent_commands) - 1 else '')
                for cmd_lvl, x in enumerate(parent_commands + [cmd_name]))

            _line = f'{"" if i == 0 else "or: ":>5}{_cmds}{fmt_cmd_options(cmd.options)}'
            commands_str.append(_line)
        commands_str = '\n'.join(commands_str)

        self.print_fn(RichTitles.USAGE)
        self.print_fn(commands_str)

        print()

        self.print_fn(RichTitles.COMMANDS)
        for cmd_name, cmd in group.commands.items():
            self.print_fn(pad(f'[underline]{cmd_name}[/underline]', padding_left=2))
            if cmd.help:
                self.print_fn(pad(cmd.help, padding_left=4))
                print()
            if cmd.options:
                self.print_rows([(fmt_option(opt, show_full=True, color=self.option_color), opt.help)
                                 for opt in cmd.options])
                print()

        if group.options:
            self.print_fn(RichTitles.OPTIONS)
            self._print_options(group.options)
            print()

        global_options = [parent_option
                          for parent_arg in (parent_args or [])
                          for parent_option in parent_arg.options]
        if global_options:
            self.print_fn(RichTitles.GLOBAL_OPTIONS)
            self._print_options(global_options)
            print()

        if group.help:
            self.print_fn(RichTitles.DESCRIPTION)
            self.print_fn(pad(group.help))

    def print_cmd_error(self, cmd: str):
        self.print_fn(f'[red]Unknown command "[bold]{cmd}[/bold]"[/red]')

    def print_param_error(self, key: str) -> None:
        self.print_fn(f"[red]Could not find value for [bold]{key!r}[/bold][/red]")

    def print_count_error(self, expected_count: int, count: int):
        self.print_fn(f'[red]Expected {expected_count} positional arguments but got {count}[/red]')
