from dataclasses import dataclass, field
from typing import Callable, Optional

from .utils import CommandArg


@dataclass
class Option:
    help: Optional[str]
    args: tuple[str, ...]


@dataclass
class Command:
    name: str
    help: Optional[str]
    fn: Callable
    command_args: list[CommandArg] = field(default_factory=list)

    def run(self, *args, **kwargs):
        return self.fn(*args, **kwargs)

    def __post_init__(self):
        keyword_params = [x for x in self.command_args if not x.is_positional_arg]
        if not keyword_params:
            return

        _keyword_args = set()
        for _param in keyword_params:
            for _keyword_arg in _param.keyword_args:
                if _keyword_arg in _keyword_args:
                    raise ValueError(f'Duplicate keyword args found "{_keyword_arg}"')
                _keyword_args.add(_keyword_arg)

    def print_help(self):
        pass

    @property
    def options(self) -> list[Option]:
        return [Option(help=x.help, args=x.keyword_args or [x.name]) for x in self.command_args]
