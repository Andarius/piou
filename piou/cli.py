import os
import sys
from dataclasses import dataclass, field
from typing import Any, Callable

from .command import CommandGroup, ShowHelpError, ShowTuiError, clean_multiline, OnCommandRun
from .utils import cleanup_event_loop
from .exceptions import (
    CommandNotFoundError,
    PosParamsCountError,
    KeywordParamNotFoundError,
    KeywordParamMissingError,
    InvalidChoiceError,
    InvalidValueError,
    CommandError,
)
from .formatter import Formatter, get_formatter


@dataclass
class Cli:
    """Main class to create a CLI application."""

    description: str | None = None
    """Description of the CLI that will be displayed when displaying the help"""
    formatter: Formatter = field(default_factory=get_formatter)
    """Formatter to use to display help and errors. Uses PIOU_FORMATTER env var or auto-detects."""
    propagate_options: bool = False
    """
    Propagate the options to sub-command functions or not.
    When set to None, it depends if a processor is passed or not otherwise it
    follows the boolean
    """
    on_cmd_run: OnCommandRun | None = None
    """ Function called before running the actual function.
    For instance, you can use this to get the arguments passed
    for monitoring
    """
    tui: bool = os.getenv("PIOU_TUI", "0") == "1"
    """Run in interactive TUI mode instead of CLI mode. Requires piou[tui]."""
    _on_tui_ready: Callable[[], None] | None = field(default=None, repr=False)
    """Internal: Callback called when the TUI is ready."""
    hide_internal_errors: bool = True
    """Hide piou internal frames from exception tracebacks. Set to False to show full tracebacks."""
    _group: CommandGroup = field(init=False, default_factory=CommandGroup)
    """The main command group that will contain all the commands and options"""

    def __post_init__(self):
        self._group.description = clean_multiline(self.description) if self.description else None
        self._group.propagate_options = self.propagate_options
        self._group.on_cmd_run = self.on_cmd_run

    @property
    def group(self) -> CommandGroup:
        """The root command group."""
        return self._group

    @property
    def commands(self):
        return self._group.commands

    def run(self, **kwargs):
        """Run the CLI application, parsing the command line arguments."""
        try:
            _, *args = sys.argv
        except ValueError:
            args = []

        if self.tui:
            self.tui_run(*args, **kwargs)
            return

        self.run_with_args(*args)

    def run_with_args(self, *args):
        """Run the CLI application with the given arguments."""
        try:
            return self._group.run_with_args(*args)
        except CommandNotFoundError as e:
            e.input_args = args
            self.formatter.print_invalid_command(e.valid_commands, e.input_command)
            sys.exit(1)
        except ShowHelpError as e:
            self.formatter.print_help(group=e.group, command=e.command, parent_args=e.parent_args)
        except ShowTuiError as e:
            self.tui_run(inline=e.inline)
        except KeywordParamNotFoundError as e:
            if not e.cmd:
                raise
            self.formatter.print_keyword_param_error(e.cmd, e.param)
            sys.exit(1)
        except KeywordParamMissingError as e:
            if not e.cmd:
                raise
            self.formatter.print_param_error(e.param, e.cmd)
            sys.exit(1)
        except PosParamsCountError as e:
            if not e.cmd:
                raise
            self.formatter.print_count_error(e.expected_count, e.count, e.cmd)
            sys.exit(1)
        except InvalidChoiceError as e:
            self.formatter.print_invalid_value_error(e.value, e.literal_choices, e.regex_patterns)
            sys.exit(1)
        except InvalidValueError as e:
            self.formatter.print_error(str(e))
            sys.exit(1)
        except CommandError as e:
            self.formatter.print_error(e.message)
            sys.exit(1)
        except Exception as e:
            self.formatter.print_exception(e, hide_internals=self.hide_internal_errors)
            sys.exit(1)
        finally:
            cleanup_event_loop()
        return None

    def command(
        self,
        cmd: str | None = None,
        help: str | None = None,
        description: str | None = None,
        is_main: bool = False,
    ):
        """
        Decorator to mark a function as a command
        If `is_main` is set to True, the command will be the main command and no command name should be passed.
        """
        if is_main and cmd is not None:
            raise ValueError("Main command should not have a command name")
        return self._group.command(cmd=cmd, help=help, description=description, is_main=is_main)

    def main(
        self,
        help: str | None = None,
        description: str | None = None,
    ):
        """Decorator to mark a function as the main command"""
        return self.command(cmd=None, help=help, description=description, is_main=True)

    def processor(self):
        """Decorator to mark a function as a processor for options"""
        return self._group.processor()

    def add_option(self, *args, help: str | None = None, data_type: Any = bool, default: Any = False):
        """Add an option to the CLI application."""
        self._group.add_option(*args, help=help, data_type=data_type, default=default)

    def set_options_processor(self, fn: Callable):
        """Function to call with all the options before running `run` or `run_with_args`"""
        self._group.set_options_processor(fn)

    def add_command(self, cmd: str, f, help: str | None = None, description: str | None = None):
        """Add a command to the CLI application."""
        self._group.add_command(cmd=cmd, f=f, help=help, description=description)

    def add_command_group(self, group: CommandGroup):
        """Add a command group to the CLI application."""
        self._group.add_group(group)

    def add_sub_parser(
        self,
        cmd: str,
        help: str | None = None,
        description: str | None = None,
        propagate_options: bool = False,
    ) -> CommandGroup:
        """Add a sub-command group to the CLI application."""
        group = CommandGroup(
            name=cmd,
            help=help,
            description=description,
            propagate_options=propagate_options,
        )
        self.add_command_group(group)
        return group

    # TUI methods

    def tui_on_ready(self, fn: Callable[[], None]) -> Callable[[], None]:
        """Decorator to register a callback when the TUI is ready."""
        self._on_tui_ready = fn
        return fn

    def tui_cli(self, inline: bool | None = None):
        """Create and return a TuiCli instance."""
        from .tui import TuiCli

        _inline = inline if inline is not None else os.getenv("PIOU_TUI_INLINE", "0") == "1"
        return TuiCli(self, inline=_inline)

    def tui_app(
        self,
        initial_input: str | None = None,
        css: str | None = None,
        css_path: str | None = None,
    ):
        """Create and return a TuiApp instance. Shortcut for tui_cli().get_app()."""
        return self.tui_cli().get_app(initial_input=initial_input, css=css, css_path=css_path)

    def tui_run(
        self,
        *args: str,
        inline: bool | None = None,
        css: str | None = None,
        css_path: str | None = None,
    ):
        """Run the CLI in interactive TUI mode. Requires piou[tui]."""
        try:
            tui = self.tui_cli(inline=inline)
        except ImportError:
            self.formatter.print_error("TUI mode requires textual. Install piou\\[tui] or 'textual' package.")
            sys.exit(1)

        tui.run(*args, css=css, css_path=css_path)
