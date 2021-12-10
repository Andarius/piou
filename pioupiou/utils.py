import re
from dataclasses import dataclass, field
from typing import Any, NamedTuple, List, Union


_split_reg = re.compile(r'\s?(-\w|--\w+)[=\s]')


@dataclass
class CommandArgs:
    default: Any
    help: str
    optional_args: List[str] = None

    _name: str = field(init=False)
    _data_type: Any = field(init=False)

    @property
    def name(self):
        return self._name


def CmdArg(
        *args,
        help: str = None
):
    default = ... if args[0] is ... else None
    optional_args = args if default is None else []
    return CommandArgs(
        default=default,
        help=help,
        optional_args=optional_args
    )


CommandParams = List[CommandArgs]


def _get_cmd_args(cmd: str):
    positional_args = []
    optional_args = {}

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
            optional_args[_arg] = cmd_split[last_position]

    return positional_args, optional_args


class PosParamsCountError(Exception):
    pass


class ParamNotFoundError(Exception):
    pass


def parse_args(cmd_args: List[str],
               positional_params: CommandParams,
               optional_params: CommandParams) -> dict:
    positional_args, optional_args = _get_cmd_args(' '.join(cmd_args))

    # Positional arguments

    if len(positional_params) != len(positional_args):
        raise PosParamsCountError(f'Expected {len(positional_params)} positional values but got {len(positional_args)}')
    fn_args = {
        _param.name: _param_value
        for _param, _param_value in zip(positional_params, positional_args)
    }

    # Optional Arguments
    _optional_mapping = {
        _optional_arg: cmd.name
        for cmd in optional_params
        for _optional_arg in cmd.optional_args
    }

    for _optional_arg_key, _optional_arg_value in optional_args.items():
        _optional_param = _optional_mapping.get(_optional_arg_key)
        if not _optional_param:
            raise ParamNotFoundError(f'Could not found param {_optional_arg_key}')
        fn_args[_optional_param] = _optional_arg_value

    return fn_args
