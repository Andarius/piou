import asyncio
import dataclasses
import datetime as dt
import inspect
import json
import re
import shlex
from collections import namedtuple
from dataclasses import dataclass, field
from enum import Enum
from functools import partial
from inspect import iscoroutinefunction
from pathlib import Path
from typing import (
    Any, Optional, get_args, get_origin, get_type_hints,
    Literal, TypeVar, Generic, Callable
)
from uuid import UUID

from .exceptions import (
    PosParamsCountError,
    KeywordParamNotFoundError,
    KeywordParamMissingError)

T = TypeVar('T', str, int, float, dt.date, dt.datetime, Path, dict, list)


def convert_to_type(data_type: Any, value: str,
                    *,
                    case_sensitive: bool = True):
    """
    Converts `value` to `data_type`, if not possible raises the appropriate error
    """

    if data_type is Any or data_type is bool:
        return value
    elif data_type is str:
        return str(value)
    elif data_type is int:
        return int(value)
    elif data_type is float:
        return float(value)
    elif data_type is UUID:
        return UUID(value)
    elif data_type is dt.date:
        return dt.date.fromisoformat(value)
    elif data_type is dt.datetime:
        return dt.datetime.fromisoformat(value)
    elif data_type is Path:
        p = Path(value)
        if not p.exists():
            raise FileNotFoundError(f'File not found: "{value}"')
        return p
    elif data_type is dict:
        return json.loads(value)
    elif get_origin(data_type) is Literal:
        possible_fields = get_args(data_type)
        _possible_fields_case = possible_fields
        if not case_sensitive:
            _possible_fields_case = [x.lower() for x in possible_fields] + [
                x.upper() for x in possible_fields]
        if value not in _possible_fields_case:
            possible_fields = ', '.join(possible_fields)
            raise ValueError(f'"{value}" is not a valid value for Literal[{possible_fields}]')
        return value
    elif data_type is list or get_origin(data_type) is list:
        list_type = get_args(data_type)
        return [convert_to_type(list_type[0] if list_type else str,
                                x) for x in value.split(' ')]
    elif issubclass(data_type, Enum):
        return data_type[value].value
    else:
        raise NotImplementedError(f'No parser implemented for data type "{data_type}"')


_KEYWORD_TO_NAME_REG = re.compile(r'^-+')


def keyword_arg_to_name(keyword_arg: str) -> str:
    """ Formats a string from '--quiet-v2' to 'quiet_v2' """
    return _KEYWORD_TO_NAME_REG.sub('', keyword_arg).replace('-', '_')


@dataclass
class CommandOption(Generic[T]):
    default: T
    help: Optional[str] = None
    keyword_args: tuple[str, ...] = field(default_factory=tuple)

    _name: Optional[str] = field(init=False, default=None)
    data_type: type[T] = field(init=False, default=Any)  # noqa

    # Only for literal types
    case_sensitive: bool = True

    @property
    def name(self):
        return self._name or keyword_arg_to_name(sorted(self.keyword_args)[0])

    @name.setter
    def name(self, name: Optional[str]):
        self._name = name

    @property
    def names(self) -> list[str]:
        names = []
        if self._name:
            names.append(self._name)
        for keyword_arg in self.keyword_args:
            names.append(keyword_arg_to_name(keyword_arg))
        return names

    @property
    def is_required(self):
        return self.default is ...

    @property
    def is_positional_arg(self):
        return len(self.keyword_args) == 0

    def validate(self, value: str) -> T:
        return convert_to_type(self.data_type, value,
                               case_sensitive=self.case_sensitive)  # type: ignore


def Option(
        default: Any,
        *keyword_args: str,
        help: Optional[str] = None,
        # Only for type Literal
        case_sensitive: bool = True
) -> Any:
    return CommandOption(
        default=default,
        help=help,
        keyword_args=keyword_args,
        case_sensitive=case_sensitive
    )


def _split_cmd(cmd: str) -> list[str]:
    """
    Utility to split a string containing arrays like --foo 1 2 3
    from ['--foo', '1', '2', '3'] to ['--foo', '1 2 3']
    """

    def reset_buff():
        nonlocal buff, cmd_split
        cmd_split.append(' '.join(buff))
        buff = []

    is_pos_arg = True
    buff = []
    cmd_split = []

    for arg in shlex.split(cmd):

        if arg.startswith('-'):
            if buff:
                reset_buff()
            is_pos_arg = False
        else:
            if is_pos_arg:
                cmd_split.append(arg)
                continue
            else:
                buff.append(arg)

        if not buff:
            cmd_split.append(arg)
    if buff:
        reset_buff()
    return cmd_split


def get_cmd_args(cmd: str, types: dict[str, Any]) -> tuple[list[str], dict[str, str]]:
    positional_args = []
    keyword_params = {}

    is_positional_arg = True
    skip_position = None

    cmd_split = _split_cmd(cmd)

    for i, _arg in enumerate(cmd_split):
        if skip_position is not None and i <= skip_position:
            continue

        if _arg.startswith('-'):
            is_positional_arg = False

        if is_positional_arg:
            positional_args.append(_arg)
            continue

        try:
            curr_type = types[keyword_arg_to_name(_arg)]
        except KeyError:
            raise KeywordParamNotFoundError(f'Could not find parameter {_arg!r}',
                                            _arg)
        if curr_type is bool:
            keyword_params[_arg] = True
        else:
            keyword_params[_arg] = (
                cmd_split[i + 1] if i + 1 < len(cmd_split)
                # In case of "store_true"
                else True
            )
            skip_position = i + 1

    return positional_args, keyword_params


def get_default_args(func) -> list[CommandOption]:
    signature = inspect.signature(func)
    return [v.default
            for v in signature.parameters.values()
            if v is not inspect.Parameter.empty]


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


KeywordParam = namedtuple('KeywordParam', ['name', 'validate'])


def convert_args_to_dict(input_args: list[str],
                         options: list[CommandOption]) -> dict:
    _input_pos_args, _input_keyword_args = get_cmd_args(' '.join(f'"{x}"' for x in input_args),
                                                        {name: opt.data_type
                                                         for opt in options
                                                         for name in opt.names})
    positional_args, keyword_args = [], {}
    for _arg in options:
        if _arg.is_positional_arg:
            positional_args.append(_arg)
        for _keyword_arg in _arg.keyword_args:
            keyword_args[_keyword_arg] = KeywordParam(_arg.name, _arg.validate)

    # Positional arguments
    if len(_input_pos_args) != len(positional_args):
        raise PosParamsCountError(
            f'Expected {len(positional_args)} positional values but got {len(_input_pos_args)}',
            expected_count=len(positional_args),
            count=len(_input_pos_args)
        )

    fn_args = {
        _param.name: _param.validate(_param_value)
        for _param, _param_value in zip(positional_args, _input_pos_args)
    }

    # Keyword Arguments
    for _keyword_arg_key, _keyword_arg_value in _input_keyword_args.items():
        _keyword_param = keyword_args.get(_keyword_arg_key)
        if not _keyword_param:
            raise KeywordParamMissingError(f'Missing value for required keyword parameter {_keyword_arg_key!r}',
                                           _keyword_arg_key)
        fn_args[_keyword_param.name] = _keyword_param.validate(_keyword_arg_value)

    # We fill optional fields with None and check for missing ones
    for _arg in options:
        if _arg.name not in fn_args:
            if _arg.is_required:
                raise KeywordParamMissingError(f'Missing value for required keyword parameter {_arg.name!r}',
                                               _arg.name)
            fn_args[_arg.name] = None if _arg.default is ... else _arg.default

    return fn_args


def run_function(fn: Callable, *args, loop: Optional[asyncio.AbstractEventLoop] = None, **kwargs):
    """ Runs a async / non async function """
    if iscoroutinefunction(fn):
        if loop is not None:
            return loop.run_until_complete(fn(*args, **kwargs))
        else:
            return asyncio.run(fn(*args, **kwargs))
    else:
        return fn(*args, **kwargs)


def extract_function_info(f) -> tuple[list[CommandOption], list['CommandDerivedOption']]:
    """Extracts the options from a function arguments"""
    options: list[CommandOption] = []
    derived_opts: list[CommandDerivedOption] = []

    for (param_name, param_type), option in zip(get_type_hints(f).items(),
                                                get_default_args(f)):
        if isinstance(option, CommandOption):
            # Making a copy in case of reuse
            _option = dataclasses.replace(option)
            _option.name = param_name
            _option.data_type = param_type
            options.append(_option)
        elif isinstance(option, CommandDerivedOption):
            _option = option  # dataclasses.replace(option)
            _option.param_name = param_name
            _options, _ = extract_function_info(_option.processor)
            options += _options
            derived_opts.append(_option)
        else:
            pass

    return options, derived_opts


"""
CommandDerivedOption(processor=<function test_chained_derived.<locals>.processor_3 at 0x7f086de0b130>, param_name='value') {'a': 1, 'b': 2}
[CommandOption(default=1, help=None, keyword_args=('-a',), _name='a', data_type=<class 'int'>, case_sensitive=True), 
CommandOption(default=2, help=None, keyword_args=('-b',), _name='b', data_type=<class 'int'>, case_sensitive=True)] 

[CommandDerivedOption(processor=<function test_chained_derived.<locals>.processor_2 at 0x7f086de0b1c0>, param_name='d')]

"""


@dataclass
class CommandDerivedOption:
    processor: Callable
    """Processor function, can be async """
    param_name: Optional[str] = field(init=False)

    def update_args(self, args: dict, *, loop: Optional[asyncio.AbstractEventLoop] = None) -> dict:
        if self.param_name is None:
            raise ValueError('param_name not set. Did you forget to set it?')
        _args = args.copy()
        fn_args = {}
        _options, _derived = extract_function_info(self.processor)

        for _opt in _options:
            fn_args[_opt.name] = _args.pop(_opt.name)

        for _der in _derived:
            fn_args = _der.update_args(fn_args, loop=loop)

        _args[self.param_name] = run_function(self.processor, **fn_args, loop=loop)
        return _args


def Derived(
        processor: Callable
) -> Any:
    return CommandDerivedOption(processor=processor)
