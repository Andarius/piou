import datetime as dt
import inspect
import json
import re
import shlex
from collections import namedtuple
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional, get_args, get_origin, Literal, TypeVar, Generic

from .exceptions import ParamNotFoundError, PosParamsCountError

T = TypeVar('T', str, int, float, dt.date, dt.datetime, Path, dict, Literal[None], list)


def validate_type(data_type: Any, value: str):
    if data_type is Any or data_type is bool:
        return value
    elif data_type is str:
        return str(value)
    elif data_type is int:
        return int(value)
    elif data_type is float:
        return float(value)
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
        if value not in possible_fields:
            possible_fields = ', '.join(possible_fields)
            raise ValueError(f'"{value}" is not a valid value for Literal[{possible_fields}]')
        return value
    elif data_type is list or get_origin(data_type) is list:
        list_type = get_args(data_type)
        return [validate_type(list_type[0] if list_type else str,
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

    _name: Optional[str] = field(init=False, default=None)
    data_type: type[T] = field(init=False, default=Any)  # noqa

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
        return validate_type(self.data_type, value)  # type: ignore


def Option(
        default: Any,
        *keyword_args: str,
        help: str = None
):
    return CommandOption(
        default=default,
        help=help,
        keyword_args=keyword_args,
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

        curr_type = types[keyword_arg_to_name(_arg)]

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


def get_default_args(func):
    signature = inspect.signature(func)
    return [v.default if v is not inspect.Parameter.empty else None
            for v in signature.parameters.values()]


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
    _input_pos_args, _input_keyword_args = get_cmd_args(' '.join(input_args),
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
            raise ParamNotFoundError(f'Could not find param {_keyword_arg_key}',
                                     _keyword_arg_key)
        fn_args[_keyword_param.name] = _keyword_param.validate(_keyword_arg_value)

    # We fill optional fields with None
    for _arg in options:
        if _arg.name not in fn_args:
            fn_args[_arg.name] = None if _arg.default is ... else _arg.default

    return fn_args
