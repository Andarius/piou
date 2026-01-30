from __future__ import annotations

import os
import re
import sys
from pathlib import Path
from typing import Literal, TYPE_CHECKING, cast

from ..utils import _SecretBase
from ..command import CommandOption

if TYPE_CHECKING:
    from .base import Formatter

FormatterType = Literal["raw", "rich"]


def mask_secret(value: str, show_first: int = 0, show_last: int = 0, replacement: str = "*") -> str:
    """Mask a secret value by replacing hidden characters with `replacement`.

    Optionally keeps `show_first` characters visible at the beginning
    and `show_last` characters at the end.
    """
    if not value:
        return replacement * 6
    total_len = len(value)
    if show_first + show_last >= total_len:
        return value
    prefix = value[:show_first] if show_first > 0 else ""
    suffix = value[-show_last:] if show_last > 0 else ""
    hidden_len = total_len - show_first - show_last
    mask = replacement * min(hidden_len, 6)
    return f"{prefix}{mask}{suffix}"


def get_formatter(formatter_type: FormatterType | None = None) -> Formatter:
    """Return a Formatter instance based on `formatter_type`.

    If None, uses PIOU_FORMATTER env var or defaults to 'rich' if available.
    """
    from .base import Formatter

    _formatter_type = (
        formatter_type if formatter_type is not None else os.environ.get("PIOU_FORMATTER", "").lower() or None
    )

    if _formatter_type == "raw":
        return Formatter()
    elif _formatter_type == "rich":
        try:
            from .rich_formatter import RichFormatter

            return RichFormatter()
        except ImportError:
            raise ImportError("Rich is not installed. Install it with: pip install rich")

    # Default: use Rich if available
    try:
        from .rich_formatter import RichFormatter

        return RichFormatter()
    except ImportError:
        return Formatter()


def get_program_name() -> str:
    """
    Get the program name for display in usage messages.

    Handles both direct script execution and module execution (python -m module_name).
    When run as a module, returns the module name instead of __main__.py.
    """
    program_name = os.path.basename(sys.argv[0])
    if program_name == "__main__.py":
        import __main__

        if hasattr(__main__, "__file__") and __main__.__file__:
            module_path = Path(__main__.__file__).parent
            program_name = module_path.name
        else:
            main_module = sys.modules.get("__main__")
            if main_module and hasattr(main_module, "__package__") and main_module.__package__:
                program_name = main_module.__package__

    return program_name


def fmt_option_raw(option: CommandOption, show_full: bool = False) -> str:
    """Format a command option for display (plain text)."""
    if option.is_positional_arg:
        return f"<{option.name}>"
    elif show_full:
        first_arg, *other_args = option.keyword_args
        required = "*" if option.is_required else ""
        if other_args:
            other_args_str = ", ".join(other_args)
            return f"{first_arg} ({other_args_str}){required}"
        else:
            return f"{first_arg}{required}"
    else:
        return "[" + sorted(option.keyword_args)[-1] + "]"


def fmt_cmd_options_raw(options: list[CommandOption]) -> str:
    """Format command options for display in the usage section (plain text)."""
    return " ".join([fmt_option_raw(x) for x in options]) if options else ""


def fmt_choice(choice: str | re.Pattern[str]) -> str:
    """Format a choice for display, converting regex patterns to /pattern/ format."""
    if isinstance(choice, re.Pattern):
        return f"/{choice.pattern}/"
    return str(choice)


def fmt_help(
    option: CommandOption,
    show_default: bool,
    *,
    markdown_open: str | None = None,
    markdown_close: str | None = None,
) -> str | None:
    """Format the help text for a command option."""
    _choices = option.get_choices()
    _markdown_open, _markdown_close = markdown_open or "", markdown_close or ""

    if show_default and option.default is not None and not option.is_required:
        if option.is_secret:
            if option.show_first is not None or option.show_last is not None:
                _show_first, _show_last, _replacement = (
                    option.show_first or 0,
                    option.show_last or 0,
                    option.replacement,
                )
            else:
                _secret = cast(type[_SecretBase], option.data_type)
                _show_first, _show_last, _replacement = _secret.show_first, _secret.show_last, _secret.replacement
            default_str = mask_secret(str(option.default), _show_first, _show_last, _replacement)
        else:
            default_str = option.default
        default_str = f"{_markdown_open}(default: {default_str}){_markdown_close}"
        return option.help + f" {default_str}" if option.help else default_str
    elif _choices is not None and not option.hide_choices:
        if len(_choices) <= 3:
            possible_choices = ", ".join(fmt_choice(_choice) for _choice in _choices)
            choices_help = f"{_markdown_open}(choices are: {possible_choices}){_markdown_close}"
        else:
            sep = " \n - "
            possible_choices = sep + sep.join(fmt_choice(_choice) for _choice in _choices)
            choices_help = f"\n{_markdown_open}Possible choices are:{_markdown_close}" + possible_choices
        return option.help + f" {choices_help}" if option.help else choices_help
    else:
        return option.help
