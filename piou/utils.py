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
from inspect import iscoroutinefunction
from pathlib import Path
from typing import (
    Any, Optional, get_args, get_origin, get_type_hints,
    Literal, TypeVar, Generic, Callable, Union, Coroutine
)

try:
    from types import UnionType, NoneType  # type: ignore
except ImportError:
    UnionType = Union
    NoneType = type(None)

from uuid import UUID

from .exceptions import (
    PosParamsCountError,
    KeywordParamNotFoundError,
    KeywordParamMissingError,
    InvalidChoiceError
)


class Password(str):
    pass


T = TypeVar('T', str, int, float, dt.date, dt.datetime, Path, dict, list, Password)


def extract_optional_type(t: Any):
    _origin = get_origin(t)
    if _origin is Union or _origin is UnionType:
        types = tuple(x for x in get_args(t) if x is not NoneType)
        return Union[types]  # type: ignore
    return t


def get_literals_union_args(literal: Any):
    values = []
    if get_origin(literal) is not Literal:
        return values

    for _l in get_args(literal):
        if get_origin(_l) is Union:
            values += get_literals_union_args(_l)
        elif get_origin(_l) is Literal:
            values += get_args(_l)
        else:
            values.append(_l)
    return values


def get_type_hints_derived(f):
    hints = get_type_hints(f)
    for v in inspect.signature(f).parameters.values():
        if v.name not in hints and isinstance(v.default, CommandDerivedOption):
            try:
                hints[v.name] = get_type_hints(v.default.processor)['return']
            except KeyError:
                raise ValueError(f'Could not find a return type for attribute {v.name!r}.'
                                 f'Did you forget to specify the return type of the function?')

    return hints


def validate_value(data_type: Any, value: str,
                   *,
                   case_sensitive: bool = True,
                   choices: Optional[list[Any]] = None):
    """
    Converts `value` to `data_type`, if not possible raises the appropriate error
    """
    _data_type = extract_optional_type(data_type)

    if choices:
        _choices = choices if case_sensitive else [x.lower() for x in choices]
        _value = value if case_sensitive else value.lower()
        if _value not in _choices:
            raise InvalidChoiceError(value, choices)

    if _data_type is Any or _data_type is bool:
        return value
    elif _data_type is str or _data_type is Password:
        return str(value)
    elif _data_type is int:
        return int(value)
    elif _data_type is float:
        return float(value)
    elif _data_type is UUID:
        return UUID(value)
    elif _data_type is dt.date:
        return dt.date.fromisoformat(value)
    elif _data_type is dt.datetime:
        return dt.datetime.fromisoformat(value)
    elif _data_type is Path:
        p = Path(value)
        if not p.exists():
            raise FileNotFoundError(f'File not found: "{value}"')
        return p
    elif _data_type is dict:
        return json.loads(value)
    elif inspect.isclass(_data_type) and issubclass(_data_type, Enum):
        return _data_type[value].value
    elif _data_type is list or get_origin(_data_type) is list:
        list_type = get_args(_data_type)
        return [validate_value(list_type[0] if list_type else str,
                               x) for x in value.split(' ')]
    elif get_origin(_data_type) is Literal:
        return value
    elif _data_type is list or get_origin(_data_type) is list:
        list_type = get_args(_data_type)
        return [validate_value(list_type[0] if list_type else str,
                               x) for x in value.split(' ')]
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

    choices: Optional[list[T]] = None

    _name: Optional[str] = field(init=False, default=None)
    _data_type: type[T] = field(init=False, default=Any)  # noqa

    # Only for literal types
    case_sensitive: bool = True
    hide_choices: bool = False

    # For dynamic derived
    arg_name: Optional[str] = None

    @property
    def data_type(self):
        return self._data_type

    @property
    def literal_values(self):
        return get_literals_union_args(self.data_type)

    @data_type.setter
    def data_type(self, v: type[T]):
        if self.choices and get_literals_union_args(v):
            raise ValueError('Pick either a Literal type or choices')
        self._data_type = v

    @property
    def is_password(self):
        return self.data_type == Password

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

    def get_choices(self):
        return self.literal_values or self.choices

    def validate(self, value: str) -> T:
        _value = validate_value(self.data_type, value,
                                case_sensitive=self.case_sensitive,
                                choices=self.get_choices())
        return _value  # type: ignore


def Option(
        default: Any,
        *keyword_args: str,
        help: Optional[str] = None,
        # Only for type Literal
        case_sensitive: bool = True,
        arg_name: Optional[str] = None,
        choices: Optional[Any] = None
) -> Any:
    return CommandOption(
        default=default,
        help=help,
        keyword_args=keyword_args,
        case_sensitive=case_sensitive,
        arg_name=arg_name,
        choices=choices
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
            keyword_args[_keyword_arg] = KeywordParam(_arg.arg_name or _arg.name, _arg.validate)

    # Positional arguments
    if len(_input_pos_args) != len(positional_args):
        raise PosParamsCountError(
            f'Expected {len(positional_args)} positional values but got {len(_input_pos_args)}',
            expected_count=len(positional_args),
            count=len(_input_pos_args)
        )

    fn_args = {
        _param.arg_name or _param.name: _param.validate(_param_value)
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
        if (_arg.arg_name or _arg.name) not in fn_args:
            if _arg.is_required:
                raise KeywordParamMissingError(
                    f'Missing value for required keyword parameter {_arg.arg_name or _arg.name!r}',
                    _arg.arg_name or _arg.name)
            fn_args[_arg.arg_name or _arg.name] = None if _arg.default is ... else _arg.default

    return fn_args


def run_function(fn: Callable, *args, loop: Optional[asyncio.AbstractEventLoop] = None, **kwargs):
    """ Runs an async / non async function """
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

    for (param_name, param_type), option in zip(get_type_hints_derived(f).items(),
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
            fn_args[_opt.name] = _args.pop(_opt.arg_name, None) or _args.pop(_opt.name, None)

        for _der in _derived:
            fn_args = _der.update_args(fn_args, loop=loop)

        _args[self.param_name] = run_function(self.processor, **fn_args, loop=loop)
        return _args

    def __repr__(self):
        if hasattr(self, 'param_name'):
            return f'<CommandDerivedOption param_name={self.param_name} processor={self.processor}/>'
        else:
            return f'<CommandDerivedOption processor={self.processor}/>'


R = TypeVar('R')


def Derived(
        processor: Callable[..., Union[Coroutine[Any, Any, R], R]]
) -> R:
    return CommandDerivedOption(processor=processor)  # type: ignore
