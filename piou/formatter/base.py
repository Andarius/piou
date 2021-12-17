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
    def print_cmd_help(self,
                       command: Command,
                       options: list[Option]) -> None:
        ...

    @abc.abstractmethod
    def print_cmd_error(self, cmd: str) -> None:
        ...

    @abc.abstractmethod
    def print_param_error(self, key: str) -> None:
        ...

    @abc.abstractmethod
    def print_count_error(self, expected_count: int, count: int) -> None:
        ...
