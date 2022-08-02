import sys
from dataclasses import dataclass, field
from typing import Optional, Any, Callable
import asyncio

from .command import CommandGroup, ShowHelpError, clean_multiline, OnCommandRun
from .exceptions import (
    CommandNotFoundError, PosParamsCountError,
    KeywordParamNotFoundError, KeywordParamMissingError
)
from .formatter import Formatter, RichFormatter


def get_loop():
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    return loop


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
    on_cmd_run: Optional[OnCommandRun] = None
    """ Function called before running the actual function.
    For instance, you can use this to get the arguments passed
    for monitoring
    """
    _group: CommandGroup = field(init=False, default_factory=CommandGroup)

    # _loop: asyncio.AbstractEventLoop = field(init=False, default_factory=get_loop)

    def __post_init__(self):
        self._group.description = clean_multiline(self.description) if self.description else None
        self._group.propagate_options = self.propagate_options
        self._group.on_cmd_run = self.on_cmd_run

    @property
    def commands(self):
        return self._group.commands

    def run(self):
        try:
            _, *args = sys.argv
        except ValueError:
            return
        self.run_with_args(*args)

    def run_with_args(self, *args, loop: Optional[asyncio.AbstractEventLoop] = None):
        _loop = loop or get_loop()
        try:
            return self._group.run_with_args(*args, loop=_loop)
        except CommandNotFoundError as e:
            e.input_args = args
            # self.formatter.print_cmd_error(e.valid_commands)
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
        # finally:
        #     if self._loop is not None:
        #         self._loop.close()

    def command(self, cmd: Optional[str] = None, help: Optional[str] = None, description: Optional[str] = None):
        return self._group.command(cmd=cmd, help=help, description=description)

    def processor(self):
        return self._group.processor()

    def add_option(self, *args, help: Optional[str] = None, data_type: Any = bool, default: Any = False):
        self._group.add_option(*args, help=help, data_type=data_type, default=default)

    def set_options_processor(self, fn: Callable):
        """ Function to call with all the options before running `run` or `run_with_args`"""
        self._group.set_options_processor(fn)

    def add_command(self, cmd: str, f, help: Optional[str] = None, description: Optional[str] = None):
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
