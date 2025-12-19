from __future__ import annotations
import textwrap
from dataclasses import dataclass, field
from functools import wraps
from inspect import getdoc
from typing import Any, NamedTuple, Callable

from .exceptions import DuplicatedCommandError, CommandException, CommandNotFoundError
from .utils import (
    CommandOption,
    CommandDerivedOption,
    extract_function_info,
    parse_input_args,
    run_function,
    convert_args_to_dict,
)


class ParentArg(NamedTuple):
    cmd: str
    options: list[CommandOption]
    input_options: list[str]
    options_processor: Callable | None = None
    propagate_args: bool = False


ParentArgs = list[ParentArg]


def clean_multiline(s: str) -> str:
    return textwrap.dedent(s).strip()


@dataclass
class Command:
    name: str
    fn: Callable
    help: str | None = None
    options: list[CommandOption] = field(default_factory=list)
    description: str | None = None
    derived_options: list[CommandDerivedOption] = field(default_factory=list)

    @property
    def positional_args(self) -> list[CommandOption]:
        return [opt for opt in self.options if opt.is_positional_arg]

    @property
    def keyword_args(self) -> list[CommandOption]:
        return sorted(
            [opt for opt in self.options if not opt.is_positional_arg],
            key=lambda x: (-x.is_required, x.name),
        )

    @property
    def options_sorted(self) -> list[CommandOption]:
        """Sorts with the following order:
        - positional
        - keyword required
        - keyword optional
        """
        return self.positional_args + self.keyword_args

    def run(self, *args, **kwargs):
        run_function(self.fn, *args, **kwargs)

    def __post_init__(self):
        self.description = clean_multiline(self.description) if self.description else None

        keyword_params = [x for x in self.options if not x.is_positional_arg]
        if not keyword_params:
            return

        _keyword_args = set()
        for _param in keyword_params:
            for _keyword_arg in _param.keyword_args:
                if _keyword_arg in _keyword_args:
                    raise ValueError(f'Duplicate keyword args found "{_keyword_arg}"')
                _keyword_args.add(_keyword_arg)


@dataclass
class CommandMeta:
    cmd_name: str
    fn_args: dict
    cmd_args: dict


OnCommandRun = Callable[[CommandMeta], None]


@dataclass
class CommandGroup:
    """A group of commands that can be used to organize commands and options"""

    name: str | None = None
    """ Name of the command group, used to identify it in the CLI"""
    help: str | None = None
    """ Short line to explain the command group"""
    description: str | None = None
    """ Description of the command group"""
    options_processor: Callable | None = None
    """ Function to process the options before running the command."""
    propagate_options: bool = False
    """ If set to True, the options will be propagated to the sub-commands."""
    on_cmd_run: OnCommandRun | None = None
    """ Function to call when a command is run, with the command name and arguments."""
    # _formatter: Formatter = field(init=False, default=None)
    _options: list[CommandOption] = field(init=False, default_factory=list)
    """ List of options for the command group, can be used to add global options."""
    _commands: dict[str, Command] = field(init=False, default_factory=dict)
    """ Dictionary of commands for the command group, can be used to add commands."""
    _command_groups: dict[str, CommandGroup] = field(init=False, default_factory=dict)
    """ Dictionary of sub-command groups for the command group, can be used to add sub-groups."""
    #

    def __post_init__(self):
        self.description = clean_multiline(self.description) if self.description else None

    @property
    def commands(self) -> dict:
        """Returns a dictionary of commands and command groups, sorted by command name."""
        return {k: self._commands.get(k) or self._command_groups[k] for k in sorted(self.command_names)}

    @property
    def options(self):
        """Returns a list of options, sorted by whether they are required or not."""
        return sorted(self._options, key=lambda x: x.is_required, reverse=True)

    def add_sub_parser(self, help: str | None = None, description: str | None = None):
        """Adds a sub-parser to the command group, which can be used to add sub-commands."""
        cls = type(self)
        return cls(help=help, description=description)  # noqa

    def add_option(
        self,
        *args: str,
        help: str | None = None,
        data_type: Any = bool,
        default: Any = False,
    ):
        """Adds an option to the command group."""
        opt = CommandOption(
            default=default,
            help=help,
            keyword_args=args,
        )
        opt.data_type = data_type
        self._options.append(opt)

    @property
    def command_names(self) -> set[str]:
        """Returns a set of command names, including both commands and command groups."""
        return set(self._commands.keys()) | (self._command_groups.keys())

    def add_group(self, group: CommandGroup):
        """Adds a sub-command group to the command group."""
        if group.name is None:
            raise NotImplementedError("A group must have a name")

        if group.name in self.command_names:
            raise DuplicatedCommandError(f"Duplicated command found for {group.name!r}", group.name)
        group.on_cmd_run = self.on_cmd_run
        self._command_groups[group.name] = group

    def add_command(
        self,
        f,
        cmd: str | None = None,
        help: str | None = None,
        description: str | None = None,
        is_main: bool = False,
    ):
        """Adds a command to the command group."""

        cmd_name = "__main__" if is_main else cmd or f.__name__
        if cmd_name in self.commands:
            raise DuplicatedCommandError(f"Duplicated command found for {cmd_name!r}", cmd_name)

        if cmd_name == "__main__" and self.commands:
            raise CommandException("Main command cannot be added with other commands")
        if cmd_name != "__main__" and "__main__" in self.commands:
            raise CommandException(f"Command {cmd_name!r} cannot be added with main command")

        _options, _derived_options = extract_function_info(f)
        self._commands[cmd_name] = Command(
            name=cmd_name,
            fn=f,
            options=_options,
            derived_options=_derived_options,
            help=help,
            description=description or getdoc(f),
        )

    def command(
        self,
        cmd: str | None = None,
        help: str | None = None,
        description: str | None = None,
        is_main: bool = False,
    ):
        """Decorator to mark a function as a command."""

        def _command(f):
            @wraps(f)
            def wrapper(*args, **kwargs):
                return f(*args, **kwargs)

            self.add_command(f, cmd=cmd, help=help, description=description, is_main=is_main)
            return wrapper

        return _command

    def processor(self):
        """Decorator to mark a function as an option processor."""

        def _processor(f):
            @wraps(f)
            def wrapper(*args, **kwargs):
                return f(*args, **kwargs)

            options, _ = extract_function_info(f)
            for option in options:
                self._options.append(option)
            self.set_options_processor(f)
            return wrapper

        return _processor

    def run_with_args(self, *args, parent_args: ParentArgs | None = None):
        """Runs the command with the given arguments."""

        # Collect all global option names from current group and parent args
        global_option_names = set()
        for option in self.options:
            global_option_names.update(option.keyword_args)

        # Add parent global options
        if parent_args:
            for parent_arg in parent_args:
                for option in parent_arg.options:
                    global_option_names.update(option.keyword_args)
        # Splits the input arguments into:
        # - cmd: The command name to execute
        # - global_options: Options that apply to the current command group
        # - cmd_options: Options specific to the sub-command
        cmd, global_options, cmd_options = parse_input_args(args, self.command_names, global_option_names)
        # Determines if cmd refers to a sub-command group or a direct command
        command_group = self._command_groups.get(cmd) if cmd else None
        command = (command_group or self)._commands.get(cmd) if cmd else None

        parent_args = parent_args or []
        # If we have a command group, we need to run it with the given command
        if command_group:
            # Maintains a chain of parent command contexts for nested command structures
            # If it's a command group, recursively calls run_with_args on the sub-group
            if cmd is None:
                raise NotImplementedError('"cmd" cannot be empty')
            parent_args.append(
                ParentArg(
                    cmd,
                    self.options,
                    global_options,
                    options_processor=self.options_processor,
                    propagate_args=self.propagate_options,
                )
            )
            return command_group.run_with_args(*cmd_options, parent_args=parent_args)

        # Checks if help was requested and raises a special exception to display help
        if set(global_options + cmd_options) & {"-h", "--help"}:
            raise ShowHelpError(group=command_group or self, parent_args=parent_args, command=command)

        if not command:
            raise CommandNotFoundError(list(self.command_names))

        args_dict = {}
        # Creates parallel lists that include:
        # - Command options + current group options + all parent options (if in sub-command)
        # - Command input + global input + all parent inputs (if in sub-command)
        # - Processors from each level
        # - Propagation settings for each level
        options, input_options, processors, propagate_args = (
            # Command options / current group options / parent options (optional)
            [command.options, self._options],
            [cmd_options, global_options],
            [None, self.options_processor],
            [True, self.propagate_options],
        )

        for parent_arg in parent_args:
            options.append(parent_arg.options)
            input_options.append(parent_arg.input_options)
            processors.append(parent_arg.options_processor)
            propagate_args.append(parent_arg.propagate_args)

        # For each level (command → group → parents):
        # - Converts raw input arguments to a dictionary using option definitions
        # - Runs any processor function with the arguments
        # - If propagation is enabled, merges arguments into the final args dictionary
        for _opts, _input_opts, _processor, _propagate in zip(options, input_options, processors, propagate_args):
            try:
                _arg_dict = convert_args_to_dict(_input_opts, _opts)
            except CommandException as e:
                e.cmd = cmd
                raise e
            if _processor:
                _processor(**_arg_dict)
            if _propagate is not False:
                args_dict.update(_arg_dict)

        cmd_args = args_dict.copy()
        for _derived in command.derived_options:
            args_dict = _derived.update_args(args_dict)

        # Optionally calls a monitoring/logging hook
        if self.on_cmd_run:
            full_command_name = ".".join([x.cmd for x in parent_args] + [command.name])
            self.on_cmd_run(CommandMeta(full_command_name, fn_args=args_dict, cmd_args=cmd_args))

        return command.run(**args_dict)

    def set_options_processor(self, fn: Callable):
        """Sets the options processor function for the command group."""
        self.options_processor = fn


class ShowHelpError(Exception):
    """Exception raised to show help for a command or command group."""

    def __init__(
        self,
        group: CommandGroup,
        command: Command | None = None,
        parent_args: ParentArgs | None = None,
    ):
        self.command = command
        self.group = group
        self.parent_args = parent_args
