from __future__ import annotations

import asyncio
import dataclasses
import datetime as dt
import inspect
import json
import re
import shlex
from collections import namedtuple
from dataclasses import dataclass, field
from enum import Enum
from inspect import iscoroutinefunction
from pathlib import Path
from typing import (
    Annotated,
    Any,
    get_args,
    get_origin,
    get_type_hints,
    Literal,
    TypeVar,
    Generic,
    Callable,
    Union,
    Coroutine,
    cast,
)

from typing_extensions import LiteralString

from types import EllipsisType, UnionType, NoneType

from uuid import UUID

from .exceptions import (
    PosParamsCountError,
    KeywordParamNotFoundError,
    KeywordParamMissingError,
    InvalidChoiceError,
    InvalidValueError,
)


class Password(str):
    pass


class Secret(str):
    pass


T = TypeVar("T", str, int, float, dt.date, dt.datetime, Path, dict, list, Password, EllipsisType, None)


def extract_optional_type(t: Any):
    _origin = get_origin(t)
    if _origin is Union or _origin is UnionType:
        types = tuple(x for x in get_args(t) if x is not NoneType)
        return Union[types]  # type: ignore
    return t


def get_literals_union_args(literal: Any):
    values = []
    if get_origin(literal) is not Literal:
        return values

    for _l in get_args(literal):
        if get_origin(_l) is Union:
            values += get_literals_union_args(_l)
        elif get_origin(_l) is Literal:
            values += get_args(_l)
        else:
            values.append(_l)
    return values


def extract_annotated_option(type_hint: Any) -> tuple[Any, CommandOption | CommandDerivedOption | None]:
    """
    Extract the base type and CommandOption/CommandDerivedOption from an Annotated type hint.

    Args:
        type_hint: A type hint that may be Annotated[T, Option(...)] or a regular type

    Returns:
        A tuple of (base_type, option) where:
        - base_type: The actual type (e.g., int, str) extracted from Annotated or the original type
        - option: The CommandOption/CommandDerivedOption if found in annotations, None otherwise

    Examples:
        >>> extract_annotated_option(Annotated[int, Option(...)])
        (int, CommandOption(...))
        >>> extract_annotated_option(int)
        (int, None)
        >>> extract_annotated_option(Annotated[str, Option(..., "-f", "--foo")])
        (str, CommandOption(..., keyword_args=("-f", "--foo")))
    """
    if get_origin(type_hint) is not Annotated:
        return type_hint, None

    args = get_args(type_hint)
    if not args:
        return type_hint, None

    base_type = args[0]
    option = None

    # Look for CommandOption or CommandDerivedOption in the annotations
    for arg in args[1:]:
        if isinstance(arg, (CommandOption, CommandDerivedOption)):
            option = arg
            break

    return base_type, option


def get_type_hints_derived(f):
    """Get type hints for a function, handling Derived options and Annotated types.

    For Derived options without explicit type annotations, infers the type
    from the processor function's return type.

    For Annotated types, returns the full Annotated type (base type extraction
    is handled by extract_annotated_option() in extract_function_info()).
    """
    # Use include_extras=True to preserve Annotated metadata
    hints = get_type_hints(f, include_extras=True)
    fn_parameters = inspect.signature(f).parameters
    _all_hints = {}
    for v in fn_parameters.values():
        _value = hints.get(v.name)

        # Check for Derived in Annotated type hint (Annotated[T, Derived(...)])
        if _value is not None and get_origin(_value) is Annotated:
            args = get_args(_value)
            for arg in args[1:]:
                if isinstance(arg, CommandDerivedOption):
                    # For Annotated[T, Derived(...)], T is the type we want
                    # Keep the full Annotated type - extraction happens in extract_function_info
                    break

        # Handle legacy syntax: no type hint but Derived in default value
        if _value is None and isinstance(v.default, CommandDerivedOption):
            try:
                _value = get_type_hints(v.default.processor, include_extras=True)["return"]
            except KeyError:
                raise ValueError(
                    f"Could not find a return type for attribute {v.name!r}."
                    f"Did you forget to specify the return type of the function?"
                )
        _all_hints[v.name] = _value

    return _all_hints


def validate_value(
    data_type: Any,
    value: str,
    *,
    case_sensitive: bool = True,
    choices: list[Any] | None = None,
    raise_path_does_not_exist: bool = True,
):
    """
    Converts `value` to `data_type`, if not possible raises the appropriate error
    Options:
     - case_sensitive: If True, will not lowercase the value before checking if it's in the choices
     - choices: If set, will check if the value is in the choices
     - raise_path_does_not_exist: If True, will raise a FileNotFoundError if the path does not exist
    """
    _data_type = extract_optional_type(data_type)

    if choices:
        _choices = choices if case_sensitive else [x.lower() for x in choices]
        _value = value if case_sensitive else value.lower()
        if _value not in _choices:
            raise InvalidChoiceError(value, choices)

    if _data_type is Any or _data_type is bool:
        return value
    elif _data_type is str or _data_type is Password:
        return str(value)
    elif _data_type is LiteralString:
        return cast(LiteralString, str(value))
    elif _data_type is int:
        try:
            return int(value)
        except ValueError:
            raise InvalidValueError(value, "int", "must be a valid integer")
    elif _data_type is float:
        try:
            return float(value)
        except ValueError:
            raise InvalidValueError(value, "float", "must be a valid number")
    elif _data_type is UUID:
        try:
            return UUID(value)
        except ValueError:
            raise InvalidValueError(value, "UUID", "must be a valid UUID format")
    elif _data_type is dt.date:
        try:
            return dt.date.fromisoformat(value)
        except ValueError:
            raise InvalidValueError(value, "date", "must be in ISO format (YYYY-MM-DD)")
    elif _data_type is dt.datetime:
        try:
            return dt.datetime.fromisoformat(value)
        except ValueError:
            raise InvalidValueError(value, "datetime", "must be in ISO format")
    elif _data_type is Path:
        p = Path(value)
        if raise_path_does_not_exist and not p.exists():
            raise FileNotFoundError(f'File not found: "{value}"')
        return p
    elif _data_type is dict:
        try:
            return json.loads(value)
        except json.JSONDecodeError as e:
            raise InvalidValueError(value, "dict", f"must be valid JSON: {e.msg}")
    elif inspect.isclass(_data_type) and issubclass(_data_type, Enum):
        try:
            return _data_type[value].value
        except KeyError:
            valid_values = [e.name for e in _data_type]
            raise InvalidChoiceError(value, valid_values)
    elif _data_type is list or get_origin(_data_type) is list:
        list_type = get_args(_data_type)
        return [validate_value(list_type[0] if list_type else str, x) for x in value.split(" ")]
    elif get_origin(_data_type) is Literal:
        return value
    else:
        raise NotImplementedError(f'No parser implemented for data type "{data_type}"')


_KEYWORD_TO_NAME_REG = re.compile(r"^-+")


def keyword_arg_to_name(keyword_arg: str) -> str:
    """Formats a string from '--quiet-v2' to 'quiet_v2'"""
    return _KEYWORD_TO_NAME_REG.sub("", keyword_arg).replace("-", "_")


@dataclass
class CommandOption(Generic[T]):
    default: T
    help: str | None = None
    keyword_args: tuple[str, ...] = field(default_factory=tuple)

    choices: list[T] | Callable[[], list[T]] | None = None

    _name: str | None = field(init=False, default=None)
    _data_type: type[T] = field(init=False, default=Any)  # pyright: ignore[reportAssignmentType]

    # Only for literal types
    case_sensitive: bool = True
    hide_choices: bool = False

    # For dynamic derived
    arg_name: str | None = None

    # Only for Path
    raise_path_does_not_exist: bool = True

    @property
    def data_type(self):
        return self._data_type

    @property
    def literal_values(self):
        return get_literals_union_args(self.data_type)

    @data_type.setter
    def data_type(self, v: type[T]):
        if self.choices and get_literals_union_args(v):
            raise ValueError("Pick either a Literal type or choices")
        self._data_type = v

    @property
    def is_password(self):
        return self.data_type == Password

    @property
    def name(self):
        return self._name or keyword_arg_to_name(sorted(self.keyword_args)[0])

    @name.setter
    def name(self, name: str | None):
        self._name = name

    @property
    def names(self) -> list[str]:
        names = []
        if self._name:
            names.append(self._name)
        for keyword_arg in self.keyword_args:
            names.append(keyword_arg_to_name(keyword_arg))
        return names

    @property
    def is_required(self):
        return self.default is ...

    @property
    def is_positional_arg(self):
        return len(self.keyword_args) == 0

    def get_choices(self) -> list[T] | None:
        _choices = self.choices() if callable(self.choices) else self.choices
        return self.literal_values or _choices

    def validate(self, value: str) -> T:
        _value = validate_value(
            self.data_type,
            value,
            case_sensitive=self.case_sensitive,
            choices=self.get_choices(),
            raise_path_does_not_exist=self.raise_path_does_not_exist,
        )
        return _value  # type: ignore


def Option(
    default: Any,
    *keyword_args: str,
    help: str | None = None,
    # Only for type Literal
    case_sensitive: bool = True,
    arg_name: str | None = None,
    choices: Any | None = None,
    # Only for Path
    raise_path_does_not_exist: bool = True,
) -> Any:
    return CommandOption(
        default=default,
        help=help,
        keyword_args=keyword_args,
        case_sensitive=case_sensitive,
        arg_name=arg_name,
        choices=choices,
        raise_path_does_not_exist=raise_path_does_not_exist,
    )


def _split_cmd(cmd: str) -> list[str]:
    """
    Utility to split a string containing arrays like --foo 1 2 3
    from ['--foo', '1', '2', '3'] to ['--foo', '1 2 3']
    """

    def reset_buff():
        nonlocal buff, cmd_split
        cmd_split.append(" ".join(buff))
        buff = []

    is_pos_arg = True
    buff = []
    cmd_split = []
    for arg in shlex.split(cmd):
        if arg.startswith("-"):
            if buff:
                reset_buff()
            is_pos_arg = False
        else:
            if is_pos_arg:
                cmd_split.append(arg)
                continue
            else:
                buff.append(arg)

        if not buff:
            cmd_split.append(arg)
    if buff:
        reset_buff()
    return cmd_split


def get_cmd_args(cmd: str, types: dict[str, Any]) -> tuple[list[str], dict[str, str]]:
    """
    Parse a command string into positional arguments and keyword parameters.

    This function takes a shell-like command string and separates it into:
    1. Positional arguments (everything before the first flag)
    2. Keyword parameters (flags and their values)

    The parsing follows these rules:
    - Arguments before the first "-" or "--" flag are treated as positional
    - Boolean-typed flags are set to True when present (no value expected)
    - Non-boolean flags consume the next argument as their value
    - Multi-value arguments are grouped together as space-separated strings
    - Unknown flags raise KeywordParamNotFoundError

    Examples:
        >>> get_cmd_args("file1 --verbose --count 5", {"verbose": bool, "count": int})
        (["file1"], {"--verbose": True, "--count": "5"})

        >>> get_cmd_args("--files a.txt b.txt --output result", {"files": list, "output": str})
        ([], {"--files": "a.txt b.txt", "--output": "result"})

        >>> get_cmd_args("input.txt output.txt", {})
        (["input.txt", "output.txt"], {})
    """
    positional_args = []
    keyword_params = {}

    is_positional_arg = True
    skip_position = None

    cmd_split = _split_cmd(cmd)

    for i, _arg in enumerate(cmd_split):
        if skip_position is not None and i <= skip_position:
            continue

        # Once we encounter the first argument starting with -,
        # all subsequent arguments are treated as keyword arguments
        # All arguments before the first - argument are positional
        if _arg.startswith("-"):
            is_positional_arg = False

        if is_positional_arg:
            positional_args.append(_arg)
            continue

        # Converts keyword argument format (--my-param) to parameter name (my_param)
        # Looks up the expected type for validation
        try:
            curr_type = types[keyword_arg_to_name(_arg)]
        except KeyError:
            raise KeywordParamNotFoundError(f"Could not find parameter {_arg!r}", _arg)

        # Boolean parameters: Simply set to True when present (flags like --verbose)
        if curr_type is bool:
            keyword_params[_arg] = True
        else:
            # Value parameters: Take the next argument as their value and mark that position to be skipped
            keyword_params[_arg] = (
                cmd_split[i + 1]
                if i + 1 < len(cmd_split)
                # In case of "store_true"
                else True
            )
            skip_position = i + 1

    return positional_args, keyword_params


def get_default_args(func) -> list[CommandOption]:
    signature = inspect.signature(func)
    return [v.default for v in signature.parameters.values() if v is not inspect.Parameter.empty]


def parse_input_args(
    args: tuple[Any, ...], commands: set[str], global_option_names: set[str] | None = None
) -> tuple[str | None, list[str], list[str]]:
    """
    Split command-line arguments into global options, command name, and command options.

    Args:
        args: Command-line arguments (typically from sys.argv[1:])
        commands: Valid command names (may include "__main__" for single-command CLIs)
        global_option_names: Global option names (e.g., {'-q', '--quiet'}). When provided,
                           these options are treated as global regardless of position.

    Returns:
        (command_name, global_options, command_options)
        - command_name: Command to execute or None if not found ("__main__" for single-command CLIs)
        - global_options: Arguments that are global options (includes values)
        - command_options: Arguments that are command-specific options

    Rules:
        - Global options can appear before or after the command
        - Unknown args before command are treated as global (backward compatibility)
        - Args after command are command-specific unless they match global option names
        - If no command found but "__main__" exists, all args become command options
        - Without global_option_names, uses simple positional parsing

    Examples:
        >>> parse_input_args(("--verbose", "deploy", "--env", "prod"),
        ...                  {"deploy"}, {"--verbose"})
        ("deploy", ["--verbose"], ["--env", "prod"])

        >>> parse_input_args(("deploy", "--env", "prod", "--verbose"),
        ...                  {"deploy"}, {"--verbose"})
        ("deploy", ["--verbose"], ["--env", "prod"])
    """
    # Handle main-only CLI
    if "__main__" in commands and len(commands) == 1:
        return "__main__", [], list(args)

    # Find the command
    cmd = None
    cmd_index = None
    for i, arg in enumerate(args):
        if arg in commands:
            cmd = arg
            cmd_index = i
            break

    # If no command found but __main__ exists, use __main__
    if cmd is None and "__main__" in commands:
        return "__main__", [], list(args)

    # If no command found at all
    if cmd is None:
        return None, list(args), []

    if cmd_index is None:
        raise ValueError(f"Command {cmd!r} not found in arguments: {args}")
    # Split args around the command
    before_cmd = list(args[:cmd_index])
    after_cmd = list(args[cmd_index + 1 :])

    # If no global option names provided, use simple positional logic
    if not global_option_names:
        return cmd, before_cmd, after_cmd

    # Separate global options from command options
    global_options = []
    cmd_options = []

    # Process args before command
    i = 0
    while i < len(before_cmd):
        arg = before_cmd[i]
        if arg in global_option_names:
            global_options.append(arg)
            # Check if next arg is a value for this option
            if i + 1 < len(before_cmd) and not before_cmd[i + 1].startswith("-"):
                i += 1
                global_options.append(before_cmd[i])
        else:
            global_options.append(arg)  # Unknown args before command are global
        i += 1

    # Process args after command
    i = 0
    while i < len(after_cmd):
        arg = after_cmd[i]
        if arg in global_option_names:
            global_options.append(arg)
            # Check if next arg is a value for this option
            if i + 1 < len(after_cmd) and not after_cmd[i + 1].startswith("-") and after_cmd[i + 1] not in commands:
                i += 1
                global_options.append(after_cmd[i])
        else:
            cmd_options.append(arg)  # Everything else after command is command-specific
        i += 1

    return cmd, global_options, cmd_options


KeywordParam = namedtuple("KeywordParam", ["name", "validate"])


def convert_args_to_dict(input_args: list[str], options: list[CommandOption]) -> dict:
    """
    Convert raw command-line arguments into a validated dictionary ready for function execution.

    Takes parsed command arguments and validates them against defined options,
    performing type conversion, validation, and filling in default values.

    The conversion process:
    1. Parses input_args into positional and keyword arguments using option definitions
    2. Validates positional argument count matches expected parameters
    3. Validates and converts each argument value according to its CommandOption type
    4. Fills in default values for optional parameters not provided
    5. Raises specific errors for missing required parameters or invalid values


    Examples:
        >>> # Define options for a command
        >>> options = [
        ...     CommandOption(default=..., help="Input file"),  # positional, required
        ...     CommandOption(default=False, keyword_args=("--verbose",), data_type=bool),
        ...     CommandOption(default=1, keyword_args=("--count",), data_type=int)
        ... ]

        >>> # Convert arguments
        >>> convert_args_to_dict(["input.txt", "--verbose", "--count", "5"], options)
        {"input_file": "input.txt", "verbose": True, "count": 5}

        >>> # Missing required positional argument
        >>> convert_args_to_dict(["--verbose"], options)
        PosParamsCountError: Expected 1 positional values but got 0

        >>> # Unknown keyword argument
        >>> convert_args_to_dict(["input.txt", "--unknown"], options)
        KeywordParamNotFoundError: Could not find parameter '--unknown'

        >>> # Using defaults for optional parameters
        >>> convert_args_to_dict(["input.txt"], options)
        {"input_file": "input.txt", "verbose": False, "count": 1}
    """
    _input_pos_args, _input_keyword_args = get_cmd_args(
        " ".join(f"'{x}'" for x in input_args),
        {name: opt.data_type for opt in options for name in opt.names},
    )
    positional_args, keyword_args = [], {}
    for _arg in options:
        if _arg.is_positional_arg:
            positional_args.append(_arg)
        for _keyword_arg in _arg.keyword_args:
            keyword_args[_keyword_arg] = KeywordParam(_arg.arg_name or _arg.name, _arg.validate)

    # Positional arguments
    if len(_input_pos_args) != len(positional_args):
        raise PosParamsCountError(
            f"Expected {len(positional_args)} positional values but got {len(_input_pos_args)}",
            expected_count=len(positional_args),
            count=len(_input_pos_args),
        )

    fn_args = {
        _param.arg_name or _param.name: _param.validate(_param_value)
        for _param, _param_value in zip(positional_args, _input_pos_args)
    }
    # Keyword Arguments
    for _keyword_arg_key, _keyword_arg_value in _input_keyword_args.items():
        _keyword_param = keyword_args.get(_keyword_arg_key)
        if not _keyword_param:
            raise KeywordParamMissingError(
                f"Missing value for required keyword parameter {_keyword_arg_key!r}",
                _keyword_arg_key,
            )
        fn_args[_keyword_param.name] = _keyword_param.validate(_keyword_arg_value)

    # We fill optional fields with None and check for missing ones
    for _arg in options:
        if (_arg.arg_name or _arg.name) not in fn_args:
            if _arg.is_required:
                raise KeywordParamMissingError(
                    f"Missing value for required keyword parameter {_arg.arg_name or _arg.name!r}",
                    _arg.arg_name or _arg.name,
                )
            fn_args[_arg.arg_name or _arg.name] = None if _arg.default is ... else _arg.default

    return fn_args


_LOOP: asyncio.AbstractEventLoop | None = None
_LOOP_CREATED: bool = False  # True if we created the loop (not from get_running_loop)


def cleanup_event_loop():
    """Close the event loop if we created it. Call after CLI execution completes."""
    global _LOOP, _LOOP_CREATED
    if _LOOP_CREATED and _LOOP is not None and not _LOOP.is_closed():
        _LOOP.close()
        _LOOP = None
        _LOOP_CREATED = False


def run_function(fn: Callable, *args, **kwargs):
    global _LOOP, _LOOP_CREATED
    """Runs an async / non async function"""
    if iscoroutinefunction(fn):
        if _LOOP is None:
            try:
                _LOOP = asyncio.get_running_loop()
            except RuntimeError:
                _LOOP = asyncio.new_event_loop()
                _LOOP_CREATED = True

        main_task = _LOOP.create_task(fn(*args, **kwargs))

        try:
            return _LOOP.run_until_complete(main_task)
        except KeyboardInterrupt:
            # Cancel the main task and all its children
            main_task.cancel()
            # Give tasks a chance to handle cancellation
            try:
                _LOOP.run_until_complete(main_task)
            except asyncio.CancelledError:
                pass
            raise
    else:
        return fn(*args, **kwargs)


def extract_function_info(
    f,
    from_derived: bool = False,
) -> tuple[list[CommandOption], list[CommandDerivedOption]]:
    """Extracts the options from a function arguments.

    Supports two syntaxes for defining options:

    1. Default value syntax (original):
        def foo(bar: int = Option(..., "-b", "--bar")):
            pass

    2. Annotated syntax (new):
        def foo(bar: Annotated[int, Option(..., "-b", "--bar")]):
            pass

    Both syntaxes can be mixed in the same function.
    """
    options: list[CommandOption] = []
    derived_opts: list[CommandDerivedOption] = []
    type_hints = get_type_hints_derived(f)
    default_args = get_default_args(f)

    for (param_name, param_type), default_value in zip(type_hints.items(), default_args):
        # Check if option is defined via Annotated syntax
        base_type, annotated_option = extract_annotated_option(param_type)

        # Determine the option source: Annotated takes precedence over default value
        if annotated_option is not None:
            option = annotated_option
            param_type = base_type
        else:
            option = default_value

        if isinstance(option, CommandOption):
            # Making a copy in case of reuse
            _option = dataclasses.replace(option)
            if from_derived and _option.arg_name is None:
                # This is to avoid errors when reusing the same parameter name
                # for different derived functions
                _option.arg_name = f"__{f.__name__}.{param_name}"
            _option.name = param_name
            _option.data_type = param_type
            options.append(_option)
        elif isinstance(option, CommandDerivedOption):
            _option = option  # dataclasses.replace(option)
            _option.param_name = param_name
            _options, _ = extract_function_info(_option.processor, from_derived=True)
            options += _options
            derived_opts.append(_option)
        else:
            pass

    return options, derived_opts


@dataclass
class CommandDerivedOption:
    processor: Callable
    """Processor function, can be async """
    param_name: str | None = field(init=False)

    def update_args(self, args: dict) -> dict:
        if self.param_name is None:
            raise ValueError("param_name not set. Did you forget to set it?")
        _args = args.copy()
        fn_args = {}
        _options, _derived = extract_function_info(self.processor, from_derived=True)
        for _opt in _options:
            # Use `is not None` instead of `or` to preserve falsy values like 0, False, ""
            val = _args.pop(_opt.arg_name, None)
            fn_args[_opt.name] = val if val is not None else _args.pop(_opt.name, None)

        for _der in _derived:
            fn_args = _der.update_args(fn_args)

        _args[self.param_name] = run_function(self.processor, **fn_args)
        return _args

    def __repr__(self):
        if hasattr(self, "param_name"):
            return f"<CommandDerivedOption param_name={self.param_name} processor={self.processor}/>"
        else:
            return f"<CommandDerivedOption processor={self.processor}/>"


R = TypeVar("R")


def Derived(processor: Callable[..., Coroutine[Any, Any, R] | R]) -> R:
    return CommandDerivedOption(processor=processor)  # type: ignore
