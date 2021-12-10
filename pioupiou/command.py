from dataclasses import dataclass
from typing import Callable, List, Tuple
from .utils import CommandParams


@dataclass
class Command:
    name: str
    help: str
    fn: Callable
    positional_params: CommandParams = None
    optional_params: CommandParams = None

    @property
    def parameters(self) -> 'List[Command]':
        return [
            *self.positional_params,
            *self.optional_params
        ]

    def run(self, *args, **kwargs):
        return self.fn(*args, **kwargs)

    def __post_init__(self):
        if not self.optional_params:
            return

        _optional_args = set()
        for _param in self.optional_params:
            for _opt_arg in _param.optional_args:
                if _opt_arg in _optional_args:
                    raise ValueError(f'Duplicate optional arg found "{_opt_arg}"')
                _optional_args.add(_opt_arg)

@dataclass
class Option:
    help: str
    args: Tuple[str]
