from dataclasses import dataclass, field
from typing import Callable, Optional

from .utils import CommandParams


@dataclass
class Command:
    name: str
    help: Optional[str]
    fn: Callable
    positional_params: CommandParams = field(default_factory=list)
    keyword_params: CommandParams = field(default_factory=list)

    @property
    def params(self) -> CommandParams:
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
    help: Optional[str]
    args: tuple[str, ...]
