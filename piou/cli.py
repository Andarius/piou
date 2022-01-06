import sys
from dataclasses import dataclass, field
from typing import Optional, Any, Callable

from .command import CommandGroup, ShowHelpError, clean_multiline
from .exceptions import (
    CommandNotFoundError, PosParamsCountError,
    KeywordParamNotFoundError, KeywordParamMissingError
)
from .formatter import Formatter, RichFormatter


@dataclass
class Cli:
    description: Optional[str] = None
    """Description of the CLI that will be displayed when displaying the help"""
    formatter: Formatter = field(default_factory=RichFormatter)
    """Formatter to use to display help and errors"""
    propagate_options: Optional[bool] = None
    """
    Propagate the options to sub-command functions or not. 
    When set to None, it depends if a processor is passed or not otherwise it 
    follows the boolean
    """

    _group: CommandGroup = field(init=False, default_factory=CommandGroup)

    def __post_init__(self):
        self._group.description = clean_multiline(self.description) if self.description else None
        self._group.propagate_options = self.propagate_options

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

    def command(self, cmd: str, help: str = None, description: str = None):
        return self._group.command(cmd=cmd, help=help, description=description)

    def add_option(self, *args, help: str = None, data_type: Any = bool, default: Any = False):
        self._group.add_option(*args, help=help, data_type=data_type, default=default)

    def set_options_processor(self, fn: Callable):
        """ Function to call with all the options before running `run` or `run_with_args`"""
        self._group.set_options_processor(fn)

    def add_command(self, cmd: str, f, help: str = None, description: str = None):
        self._group.add_command(cmd=cmd, f=f, help=help, description=description)

    def add_command_group(self, group: CommandGroup):
        self._group.add_group(group)

    def add_sub_parser(self, cmd: str,
                       help: Optional[str] = None,
                       description: Optional[str] = None,
                       propagate_options: Optional[bool] = None) -> CommandGroup:
        group = CommandGroup(name=cmd, help=help, description=description, propagate_options=propagate_options)
        self.add_command_group(group)
        return group
