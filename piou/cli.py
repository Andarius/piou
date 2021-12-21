import inspect
import sys
from dataclasses import dataclass, field
from functools import wraps
from typing import get_type_hints, Optional, Any

from .command import Command
from .formatter import Formatter, RichFormatter
from .utils import (
    convert_args_to_dict,
    CommandOption,
    ParamNotFoundError,
    PosParamsCountError,
    ShowHelpError
)


class DuplicatedCommandError(Exception):
    def __init__(self, msg: str, cmd: str):
        super().__init__(msg)
        self.cmd = cmd


def parse_input_args(args: tuple[Any, ...], commands: set[str]) -> tuple[
    Optional[str], list[str], list[str]
]:
    """
    Extracts the:
     - global options
     - command
     - command options
     from the passed list or arguments
    """
    global_options, cmd_options, cmd = [], [], None
    for arg in args:
        if cmd is None and arg in commands:
            cmd = arg
            continue

        if cmd is None:
            global_options.append(arg)
        else:
            cmd_options.append(arg)
    return cmd, global_options, cmd_options


def get_default_args(func):
    signature = inspect.signature(func)
    return [v.default if v is not inspect.Parameter.empty else None
            for v in signature.parameters.values()]


@dataclass
class CommandGroup:
    help: Optional[str] = None
    name: Optional[str] = None

    _formatter: Formatter = field(init=False, default_factory=RichFormatter)
    _options: list[CommandOption] = field(init=False, default_factory=list)
    _commands: dict[str, Command] = field(init=False, default_factory=dict)
    _command_groups: dict[str, 'CommandGroup'] = field(init=False, default_factory=dict)

    @property
    def commands(self):
        return {k: self._commands.get(k) or self._command_groups[k] for k in sorted(self.command_names)}

    @property
    def options(self):
        return self._options

    def add_sub_parser(self, description: Optional[str] = None):
        cls = type(self)
        return cls(description=description)  # noqa

    def add_option(self, default: Any, *args: str, help: str = None):
        self._options.append(CommandOption(
            default=default,
            help=help,
            keyword_args=args,
        ))

    @property
    def command_names(self) -> set[str]:
        return set(self._commands.keys()) | (self._command_groups.keys())

    def add_group(self, group: 'CommandGroup'):
        if group.name is None:
            raise NotImplementedError('A group must have a name')

        if group.name in self.command_names:
            raise DuplicatedCommandError(f'Duplicated command found for {group.name!r}',
                                         group.name)
        self._command_groups[group.name] = group

    def command(self, cmd: str, help: str = None):
        if cmd in self.commands:
            raise DuplicatedCommandError(f'Duplicated command found for {cmd!r}',
                                         cmd)

        def _command(f):
            @wraps(f)
            def wrapper(*args, **kwargs):
                return f(*args, **kwargs)

            options: list[CommandOption] = []
            defaults: list[CommandOption] = get_default_args(f)

            for (param_name, param_type), option in zip(get_type_hints(f).items(),
                                                        defaults):
                if not isinstance(option, CommandOption):
                    continue

                option.name = param_name
                option.data_type = param_type
                options.append(option)

            self._commands[cmd] = Command(name=cmd,
                                          fn=wrapper,
                                          options=options,
                                          help=help)
            return wrapper

        return _command

    def run_with_args(self, *args):
        cmd, global_options, cmd_options = parse_input_args(args, self.command_names)

        if set(global_options) & {'-h', '--help'}:
            self._formatter.print_help(commands=self.commands,
                                       options=self._options,
                                       help=self.help)
            return

        if not cmd:
            self._formatter.print_cmd_error(cmd)
            return

        command, command_group = self._commands.get(cmd), self._command_groups.get(cmd)
        _command = command or command_group
        try:
            _cmd_args_dict = convert_args_to_dict(
                cmd_options,
                _command.options
            )
            _global_args_dict = convert_args_to_dict(
                global_options, self._options)
        except ParamNotFoundError as e:
            self._formatter.print_param_error(e.key)
            return
        except PosParamsCountError as e:
            self._formatter.print_count_error(e.expected_count, e.count)
            return
        except ShowHelpError:
            if command:
                self._formatter.print_cmd_help(command, self._options)
            else:
                self._formatter.print_cmd_group_help(command=command_group,
                                                     commands=command_group.commands,
                                                     options=command_group.options)
            return

        _args_dict = {**_global_args_dict, **_cmd_args_dict}
        return command.run(**_args_dict)

    def print_help(self):
        self._formatter.print_help(
            commands=self.commands,
            options=self._options
        )


@dataclass
class Cli:
    formatter: Formatter = RichFormatter()
    description: str = None

    _group: CommandGroup = CommandGroup()

    @property
    def commands(self):
        return self._group.commands

    def print_help(self):
        self._group.print_help()

    def run(self):
        try:
            _, *args = sys.argv
        except ValueError:
            return
        return self._group.run_with_args(*args)

    def command(self, cmd: str, help: str = None):
        return self._group.command(cmd=cmd, help=help)

    def add_option(self, default: None, *args, help: str = None):
        self._group.add_option(default, *args, help=help)

    def add_sub_parser(self, cmd: str, description: Optional[str] = None) -> CommandGroup:
        cmd_group = CommandGroup(name=cmd, help=description)
        cmd_group._formatter = self.formatter
        self._group.add_group(cmd_group)
        return cmd_group

    def __post_init__(self):
        self._group.help = self.description
