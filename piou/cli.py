import sys
from dataclasses import dataclass, field
from functools import wraps
from typing import get_type_hints, List

from .command import Command, Option
from .format import RichFormatter
from .utils import parse_args, CommandArgs


@dataclass
class Parser:
    description: str

    formatter = RichFormatter()
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

        _command = self._commands.get(cmd)
        if not _command:
            self.formatter.print_cmd_error(cmd)
            return
        _args_dict = parse_args(args,
                                _command.positional_params,
                                _command.keyword_params)
        _command.run(**_args_dict)

    def command(self, cmd: str, help: str = None):
        def _command(f):
            @wraps(f)
            def wrapper(*args, **kwargs):
                return f(*args, **kwargs)

            positional_params, optional_params = [], []
            defaults: List[CommandArgs] = f.__defaults__ or []
            for (param_name, param_type), cmd_args in zip(get_type_hints(f).items(),
                                                          defaults):
                cmd_args.name = param_name
                cmd_args.data_type = param_type
                if cmd_args.default is ...:
                    positional_params.append(cmd_args)
                else:
                    optional_params.append(cmd_args)

            self._commands[cmd] = Command(name=cmd,
                                          fn=wrapper,
                                          positional_params=positional_params,
                                          keyword_params=optional_params,
                                          help=help)
            return wrapper

        return _command

    def add_argument(self, *args: str, help: str = None):
        self._options.append(Option(help, args=args))
