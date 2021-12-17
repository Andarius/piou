import sys
from dataclasses import dataclass, field
from functools import wraps
from typing import get_type_hints, List

from .command import Command, Option
from .formatter import Formatter, RichFormatter
from .utils import (
    parse_args, CommandArg,
    ParamNotFoundError,
    PosParamsCountError,
    ShowHelpError
)


@dataclass
class Cli:
    description: str

    formatter: Formatter = RichFormatter()
    _options: List[Option] = field(init=False, default_factory=list)
    _commands: dict[str, Command] = field(init=False, default_factory=dict)

    @property
    def commands(self):
        return self._commands

    def print_help(self):
        self.formatter.print_help(
            commands=self.commands,
            options=self._options
        )

    def run(self):
        try:
            _, cmd, *args = sys.argv
        except ValueError:
            return

        if cmd in {'-h', '--help'}:
            self.formatter.print_help(self.commands, self._options)
            return

        _command = self._commands.get(cmd)
        if not _command:
            self.formatter.print_cmd_error(cmd)
            return

        try:
            _args_dict = parse_args(args, _command.command_args)
        except ParamNotFoundError as e:
            self.formatter.print_param_error(e.key)
            return
        except PosParamsCountError as e:
            self.formatter.print_count_error(e.expected_count, e.count)
            return
        except ShowHelpError:
            self.formatter.print_cmd_help(_command, self._options)
            return

        _command.run(**_args_dict)

    def command(self, cmd: str, help: str = None):
        def _command(f):
            @wraps(f)
            def wrapper(*args, **kwargs):
                return f(*args, **kwargs)

            command_args = []
            defaults: List[CommandArg] = f.__defaults__ or []
            for (param_name, param_type), cmd_arg in zip(get_type_hints(f).items(),
                                                         defaults):
                cmd_arg.name = param_name
                cmd_arg.data_type = param_type
                command_args.append(cmd_arg)
                # if cmd_args.default is ...:
                #     positional_params.append(cmd_args)
                # else:
                #     optional_params.append(cmd_args)

            self._commands[cmd] = Command(name=cmd,
                                          fn=wrapper,
                                          command_args=command_args,
                                          help=help)
            return wrapper

        return _command

    def add_argument(self, *args: str, help: str = None):
        self._options.append(Option(help, args=args))
