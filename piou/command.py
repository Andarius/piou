from dataclasses import dataclass, field
from functools import wraps
from typing import Callable
from typing import get_type_hints, Optional, Any

from .exceptions import DuplicatedCommandError
from .utils import (
    CommandOption,
    get_default_args,
    parse_input_args,
    convert_args_to_dict
)

ParentArgs = list[tuple[str, list[CommandOption]]]


@dataclass
class Command:
    name: str
    help: Optional[str]
    fn: Callable
    options: list[CommandOption] = field(default_factory=list)

    @property
    def positional_args(self) -> list[CommandOption]:
        return [opt for opt in self.options if opt.is_positional_arg]

    @property
    def keyword_args(self) -> list[CommandOption]:
        return [opt for opt in self.options if not opt.is_positional_arg]

    def run(self, *args, **kwargs):
        return self.fn(*args, **kwargs)

    def __post_init__(self):
        keyword_params = [x for x in self.options if not x.is_positional_arg]
        if not keyword_params:
            return

        _keyword_args = set()
        for _param in keyword_params:
            for _keyword_arg in _param.keyword_args:
                if _keyword_arg in _keyword_args:
                    raise ValueError(f'Duplicate keyword args found "{_keyword_arg}"')
                _keyword_args.add(_keyword_arg)


@dataclass
class CommandGroup:
    help: Optional[str] = None
    name: Optional[str] = None

    # _formatter: Formatter = field(init=False, default=None)
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
        return cls(help=description)  # noqa

    def add_option(self, default: Any, *args: str, help: str = None, data_type: Any = None):
        opt = CommandOption(
            default=default,
            help=help,
            keyword_args=args,
        )
        opt.data_type = data_type
        self._options.append(opt)

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
            defaults: list[Optional[Any]] = get_default_args(f)

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

    def run_with_args(self, *args, parent_args: ParentArgs = None):

        cmd, global_options, cmd_options = parse_input_args(args, self.command_names)

        command_group = self._command_groups.get(cmd) if cmd else None
        command = (command_group or self)._commands.get(cmd) if cmd else None

        # print(command)
        if command_group:
            if cmd is None:
                raise NotImplementedError('"cmd" cannot be empty')
            parent_args = [*(parent_args or [])] + [(cmd, self.options)]
            return command_group.run_with_args(*cmd_options, parent_args=parent_args)

        if set(global_options + cmd_options) & {'-h', '--help'} or \
                not command:
            raise ShowHelpError(
                group=command_group or self,
                parent_args=parent_args,
                command=command
            )

        _cmd_args_dict = convert_args_to_dict(
            cmd_options,
            command.options
        )
        _global_args_dict = convert_args_to_dict(
            global_options, self._options)

        _args_dict = {**_global_args_dict, **_cmd_args_dict}
        return command.run(**_args_dict)


class ShowHelpError(Exception):
    def __init__(self,
                 group: CommandGroup,
                 command: Command = None,
                 parent_args: ParentArgs = None):
        self.command = command
        self.group = group
        self.parent_args = parent_args
