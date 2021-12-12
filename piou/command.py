from dataclasses import dataclass
from typing import Callable, List, Tuple
from .utils import CommandParams


@dataclass
class Command:
    name: str
    help: str
    fn: Callable
    positional_params: CommandParams = None
    keyword_params: CommandParams = None

    @property
    def parameters(self) -> 'List[Command]':
        return [
            *self.positional_params,
            *self.keyword_params
        ]

    def run(self, *args, **kwargs):
        return self.fn(*args, **kwargs)

    def __post_init__(self):
        if not self.keyword_params:
            return

        _keyword_args = set()
        for _param in self.keyword_params:
            for _keyword_arg in _param.keyword_args:
                if _keyword_arg in _keyword_args:
                    raise ValueError(f'Duplicate keyword args found "{_keyword_arg}"')
                _keyword_args.add(_keyword_arg)


@dataclass
class Option:
    help: str
    args: Tuple[str]
