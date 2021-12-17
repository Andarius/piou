import datetime as dt
import json
import shlex
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional, get_args, get_origin


def validate_type(data_type: Any, value: str):
    if data_type is Any:
        return value
    elif data_type is str:
        return str(value)
    elif data_type is int:
        return int(value)
    elif data_type is float:
        return float(value)
    elif data_type is bytes:
        return bytes(value)
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
    elif data_type is list or get_origin(data_type) is list:
        list_type = get_args(data_type)
        return [validate_type(list_type[0] if list_type else str,
                              x) for x in value.split(' ')]
    else:
        raise NotImplementedError(f'No parser implemented for data type "{data_type}"')


@dataclass
class CommandArg:
    default: Any
    help: Optional[str] = None
    keyword_args: tuple[str, ...] = field(default_factory=tuple)

    name: Optional[str] = field(init=False, default=None)
    data_type: Any = field(init=False, default=Any)

    @property
    def is_required(self):
        return self.default is ...

    @property
    def is_positional_arg(self):
        return len(self.keyword_args) == 0

    def validate(self, value: Any) -> Any:
        return validate_type(self.data_type, value)


def CmdArg(
        default: Any,
        *keyword_args: str,
        help: str = None
):
    return CommandArg(
        default=default,
        help=help,
        keyword_args=keyword_args,
    )


def get_cmd_args(cmd: str) -> tuple[list[str], dict[str, str]]:
    positional_args = []
    keyword_params = {}

    is_positional_arg = True
    skip_position = None

    cmd_split = shlex.split(cmd)
    for i, _arg in enumerate(cmd_split):
        if skip_position is not None and i <= skip_position:
            continue

        if _arg.startswith('-'):
            is_positional_arg = False

        if is_positional_arg:
            positional_args.append(_arg)
        else:
            keyword_params[_arg] = (
                cmd_split[i + 1] if i + 1 < len(cmd_split)
                # In case of "store_true"
                else True
            )
            skip_position = i + 1

    return positional_args, keyword_params


class PosParamsCountError(Exception):
    def __init__(self, msg: str, expected_count: int, count: int):
        super().__init__(msg)
        self.expected_count = expected_count
        self.count = count


class ParamNotFoundError(Exception):
    def __init__(self, msg: str, key: str):
        super().__init__(msg)
        self.key = key


class ShowHelpError(Exception):
    pass


def parse_args(input_args: list[str],
               command_args: list[CommandArg]) -> dict:
    _input_pos_args, _input_keyword_args = get_cmd_args(' '.join(input_args))

    if {'-h', '--help'} & _input_keyword_args.keys():
        raise ShowHelpError()

    positional_args, keyword_args = [], {}
    for _arg in command_args:
        if _arg.is_positional_arg:
            positional_args.append(_arg)
        for _keyword_arg in _arg.keyword_args:
            keyword_args[_keyword_arg] = _arg.name

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
        fn_args[_keyword_param] = _keyword_arg_value

    # We fill optional fields with None
    for _arg in command_args:
        if _arg.name not in fn_args:
            fn_args[_arg.name] = None

    return fn_args
