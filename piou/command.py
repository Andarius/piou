import asyncio
import textwrap
from dataclasses import dataclass, field
from functools import wraps
from inspect import getdoc, iscoroutinefunction
from typing import get_type_hints, Optional, Any, NamedTuple, Callable

from .exceptions import (
    DuplicatedCommandError, CommandException, CommandNotFoundError
)
from .utils import (
    CommandOption,
    CommandDerivedOption,
    get_default_args,
    parse_input_args,
    convert_args_to_dict
)


class ParentArg(NamedTuple):
    cmd: str
    options: list[CommandOption]
    input_options: list[str]
    options_processor: Optional[Callable] = None
    propagate_args: Optional[bool] = False


ParentArgs = list[ParentArg]


def clean_multiline(s: str) -> str:
    return textwrap.dedent(s).strip()


@dataclass
class Command:
    name: str
    fn: Callable
    help: Optional[str] = None
    options: list[CommandOption] = field(default_factory=list)
    description: Optional[str] = None
    derived_options: list[CommandDerivedOption] = field(default_factory=list)

    @property
    def positional_args(self) -> list[CommandOption]:
        return [opt for opt in self.options if opt.is_positional_arg]

    @property
    def keyword_args(self) -> list[CommandOption]:
        return [opt for opt in self.options if not opt.is_positional_arg]

    def run(self, *args, loop: asyncio.AbstractEventLoop = None, **kwargs):
        if iscoroutinefunction(self.fn):
            if loop is not None:
                return loop.run_until_complete(self.fn(*args, **kwargs))
            else:
                return asyncio.run(self.fn(*args, **kwargs))
        else:
            return self.fn(*args, **kwargs)

    def __post_init__(self):

        self.description = clean_multiline(self.description) if self.description else None

        keyword_params = [x for x in self.options if not x.is_positional_arg]
        if not keyword_params:
            return

        _keyword_args = set()
        for _param in keyword_params:
            for _keyword_arg in _param.keyword_args:
                if _keyword_arg in _keyword_args:
                    raise ValueError(f'Duplicate keyword args found "{_keyword_arg}"')
                _keyword_args.add(_keyword_arg)


def extract_function_info(f) -> tuple[list[CommandOption], list[CommandDerivedOption]]:
    """Extracts the options from a function arguments"""
    options: list[CommandOption] = []
    derived_opts: list[CommandDerivedOption] = []
    defaults: list[CommandOption] = get_default_args(f)

    for (param_name, param_type), option in zip(get_type_hints(f).items(),
                                                defaults):
        if isinstance(option, CommandOption):
            option.name = param_name
            option.data_type = param_type
            options.append(option)
        elif isinstance(option, CommandDerivedOption):
            option.param_name = param_name
            _options, _ = extract_function_info(option.processor)
            options += _options
            derived_opts.append(option)
        else:
            pass

    return options, derived_opts


@dataclass
class CommandMeta:
    cmd_name: str
    fn_args: dict
    cmd_args: dict


OnCommandRun = Callable[[CommandMeta], None]


@dataclass
class CommandGroup:
    name: Optional[str] = None
    help: Optional[str] = None
    """ Short line to explain the command group"""
    description: Optional[str] = None
    """ Description of the command group"""

    options_processor: Optional[Callable] = None

    propagate_options: Optional[bool] = None

    on_cmd_run: Optional[OnCommandRun] = None

    # _formatter: Formatter = field(init=False, default=None)
    _options: list[CommandOption] = field(init=False, default_factory=list)
    _commands: dict[str, Command] = field(init=False, default_factory=dict)
    _command_groups: dict[str, 'CommandGroup'] = field(init=False, default_factory=dict)

    def __post_init__(self):
        self.description = clean_multiline(self.description) if self.description else None

    @property
    def commands(self):
        return {k: self._commands.get(k) or self._command_groups[k] for k in sorted(self.command_names)}

    @property
    def options(self):
        return self._options

    def add_sub_parser(self, help: Optional[str] = None, description: Optional[str] = None):
        cls = type(self)
        return cls(help=help, description=description)  # noqa

    def add_option(self, *args: str, help: str = None, data_type: Any = bool,
                   default: Any = False):
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
        group.on_cmd_run = self.on_cmd_run
        self._command_groups[group.name] = group

    def add_command(self, f, cmd: str = None, help: str = None, description: str = None):
        cmd_name = cmd or f.__name__
        if cmd_name in self.commands:
            raise DuplicatedCommandError(f'Duplicated command found for {cmd_name!r}',
                                         cmd_name)

        _options, _derived_options = extract_function_info(f)
        self._commands[cmd_name] = Command(name=cmd_name,
                                           fn=f,
                                           options=_options,
                                           derived_options=_derived_options,
                                           help=help,
                                           description=description or getdoc(f))

    def command(self, cmd: str = None, help: str = None, description: str = None):

        def _command(f):
            @wraps(f)
            def wrapper(*args, **kwargs):
                return f(*args, **kwargs)

            self.add_command(f, cmd=cmd, help=help, description=description)
            return wrapper

        return _command

    def processor(self):
        def _processor(f):
            @wraps(f)
            def wrapper(*args, **kwargs):
                return f(*args, **kwargs)

            options, _ = extract_function_info(f)
            for option in options:
                self._options.append(option)
            self.set_options_processor(f)
            return wrapper

        return _processor

    def run_with_args(self, *args, parent_args: ParentArgs = None):

        cmd, global_options, cmd_options = parse_input_args(args, self.command_names)

        command_group = self._command_groups.get(cmd) if cmd else None
        command = (command_group or self)._commands.get(cmd) if cmd else None

        parent_args = parent_args or []
        if command_group:
            if cmd is None:
                raise NotImplementedError('"cmd" cannot be empty')
            parent_args.append(ParentArg(cmd, self.options, global_options,
                                         options_processor=self.options_processor,
                                         propagate_args=self.propagate_options))
            return command_group.run_with_args(*cmd_options, parent_args=parent_args)

        if set(global_options + cmd_options) & {'-h', '--help'}:
            raise ShowHelpError(
                group=command_group or self,
                parent_args=parent_args,
                command=command
            )

        if not command:
            raise CommandNotFoundError(list(self.command_names))

        args_dict = {}
        options, input_options, processors, propagate_args = (
            # Parent / current
            [command.options, self._options],
            [cmd_options, global_options],
            [None, self.options_processor],
            [True, self.propagate_options],
        )

        for parent_arg in parent_args:
            options.append(parent_arg.options)
            input_options.append(parent_arg.input_options)
            processors.append(parent_arg.options_processor)
            propagate_args.append(parent_arg.propagate_args)

        for _opts, _input_opts, _processor, _propagate in zip(
                options, input_options, processors, propagate_args):
            try:
                _arg_dict = convert_args_to_dict(_input_opts, _opts)
            except CommandException as e:
                e.cmd = cmd
                raise e
            if _processor:
                _processor(**_arg_dict)
            if _propagate is not False:
                args_dict.update(_arg_dict)

        cmd_args = args_dict.copy()
        for _derived in command.derived_options:
            args_dict = _derived.update_args(args_dict)

        if self.on_cmd_run:
            full_command_name = '.'.join([x.cmd for x in parent_args] + [command.name])
            self.on_cmd_run(CommandMeta(full_command_name,
                                        fn_args=args_dict,
                                        cmd_args=cmd_args))

        return command.run(**args_dict)

    def set_options_processor(self, fn: Callable):
        self.options_processor = fn
        # We don't propagate if not specified otherwise when processor is set
        if self.propagate_options is None:
            self.propagate_options = False


class ShowHelpError(Exception):
    def __init__(self,
                 group: CommandGroup,
                 command: Command = None,
                 parent_args: ParentArgs = None):
        self.command = command
        self.group = group
        self.parent_args = parent_args
