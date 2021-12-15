import abc
from dataclasses import dataclass

from ..command import Command, Option


@dataclass
class Formatter(abc.ABC):

    @abc.abstractmethod
    def print_help(self,
                   commands: dict[str, Command],
                   options: list[Option]) -> None:
        ...

    @abc.abstractmethod
    def print_cmd_error(self, cmd: str) -> None:
        ...
