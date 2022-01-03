import sys
from dataclasses import dataclass, field
from typing import Optional, Any, Callable

from .command import CommandGroup, ShowHelpError
from .exceptions import (
    CommandNotFoundError, PosParamsCountError,
    KeywordParamNotFoundError,KeywordParamMissingError
)
from .formatter import Formatter, RichFormatter


@dataclass
class Cli:
    description: Optional[str] = None
    formatter: Formatter = field(default_factory=RichFormatter)

    _group: CommandGroup = field(init=False, default_factory=CommandGroup)

    def __post_init__(self):
        self._group.help = self.description

    @property
    def commands(self):
        return self._group.commands

    def run(self):
        try:
            _, *args = sys.argv
        except ValueError:
            return
        self.run_with_args(*args)

    def run_with_args(self, *args):
        try:
            return self._group.run_with_args(*args)
        except CommandNotFoundError as e:
            raise e
        except ShowHelpError as e:
            self.formatter.print_help(group=e.group,
                                      command=e.command,
                                      parent_args=e.parent_args)
        except KeywordParamNotFoundError as e:
            if not e.cmd:
                raise NotImplementedError('Got empty command')
            self.formatter.print_keyword_param_error(e.cmd, e.param)
            return
        except KeywordParamMissingError as e:
            if not e.cmd:
                raise NotImplementedError('Got empty command')
            self.formatter.print_param_error(e.param, e.cmd)
            return
        except PosParamsCountError as e:
            if not e.cmd:
                raise NotImplementedError('Got empty command')
            self.formatter.print_count_error(e.expected_count, e.count, e.cmd)
            return

    def command(self, cmd: str, help: str = None):
        return self._group.command(cmd=cmd, help=help)

    def add_option(self, *args, help: str = None, data_type: Any = bool, default: Any = False):
        self._group.add_option(*args, help=help, data_type=data_type, default=default)

    def set_options_processor(self, fn: Callable):
        """ Function to call with all the options before running `run` or `run_with_args`"""
        self._group.set_options_processor(fn)

    def add_command(self, cmd: str, f, help: str = None):
        self._group.add_command(cmd=cmd, f=f, help=help)

    def add_command_group(self, group: CommandGroup):
        self._group.add_group(group)

    def add_sub_parser(self, cmd: str, description: Optional[str] = None) -> CommandGroup:
        group = CommandGroup(name=cmd, help=description)
        self.add_command_group(group)
        return group
