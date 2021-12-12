import re
from dataclasses import dataclass, field
from typing import Any, List

_split_reg = re.compile(r'\s?(-\w|--\w+)[=\s]')


@dataclass
class CommandArgs:
    default: Any
    help: str = None
    keyword_args: List[str] = None

    name: str = field(init=False, default=None)
    data_type: Any = field(init=False, default=Any)

    # @property
    # def name(self):
    #     return self._name


def CmdArg(
        *args,
        help: str = None
):
    default = ... if args[0] is ... else None
    keyword_args = args if default is None else []
    return CommandArgs(
        default=default,
        help=help,
        keyword_args=keyword_args
    )


CommandParams = List[CommandArgs]


def _get_cmd_args(cmd: str):
    positional_args = []
    keywork_params = {}

    is_positional_arg = True
    last_position = 0

    cmd_split = _split_reg.split(cmd)
    for i, _arg in enumerate(cmd_split):
        if is_positional_arg and _arg.startswith('-'):
            is_positional_arg = False

        if is_positional_arg:
            positional_args.append(_arg)
        elif i > last_position:
            last_position = i + 1
            keywork_params[_arg] = cmd_split[last_position]

    return positional_args, keywork_params


class PosParamsCountError(Exception):
    pass


class ParamNotFoundError(Exception):
    pass


def parse_args(cmd_args: List[str],
               positional_params: CommandParams,
               keyword_params: CommandParams) -> dict:
    positional_args, keyword_args = _get_cmd_args(' '.join(cmd_args))

    # Positional arguments

    if len(positional_params) != len(positional_args):
        raise PosParamsCountError(f'Expected {len(positional_params)} positional values but got {len(positional_args)}')
    fn_args = {
        _param.name: _param_value
        for _param, _param_value in zip(positional_params, positional_args)
    }

    # Keyword Arguments

    _keyword_mapping = {
        _keyword_arg: cmd.name
        for cmd in keyword_params
        for _keyword_arg in cmd.keyword_args
    }

    for _keyword_arg_key, _keyword_arg_value in keyword_args.items():
        _keyword_param = _keyword_mapping.get(_keyword_arg_key)
        if not _keyword_param:
            raise ParamNotFoundError(f'Could not found param {_keyword_arg_key}')
        fn_args[_keyword_param] = _keyword_arg_value

    return fn_args
