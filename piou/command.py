from dataclasses import dataclass, field
from typing import Callable, Optional

from .utils import CommandOption


@dataclass
class Command:
    name: str
    help: Optional[str]
    fn: Callable
    options: list[CommandOption] = field(default_factory=list)

    @property
    def positional_args(self) -> list[CommandOption]:
        return [opt for opt in self.options if opt.is_positional_arg]

    @property
    def keyword_args(self) -> list[CommandOption]:
        return [opt for opt in self.options if not opt.is_positional_arg]

    def run(self, *args, **kwargs):
        return self.fn(*args, **kwargs)

    def __post_init__(self):
        keyword_params = [x for x in self.options if not x.is_positional_arg]
        if not keyword_params:
            return

        _keyword_args = set()
        for _param in keyword_params:
            for _keyword_arg in _param.keyword_args:
                if _keyword_arg in _keyword_args:
                    raise ValueError(f'Duplicate keyword args found "{_keyword_arg}"')
                _keyword_args.add(_keyword_arg)
