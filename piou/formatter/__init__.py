import os
from typing import Literal

from .base import Formatter

try:
    from .rich_formatter import RichFormatter

    HAS_RICH = True
except ImportError:
    RichFormatter = None  # type: ignore[misc, assignment]
    HAS_RICH = False

FormatterType = Literal["raw", "rich"]


def get_formatter(formatter_type: FormatterType | None = None) -> Formatter:
    """
    Return a formatter based on the specified type.

    Args:
        formatter_type: The formatter to use. If None, uses PIOU_FORMATTER env var
                       or defaults to 'rich' if available.

    Returns:
        Formatter instance (RichFormatter or base Formatter)
    """
    if formatter_type is None:
        formatter_type = os.environ.get("PIOU_FORMATTER", "").lower() or None  # type: ignore[assignment]

    if formatter_type == "raw":
        return Formatter()
    elif formatter_type == "rich":
        if HAS_RICH and RichFormatter is not None:
            return RichFormatter()
        raise ImportError("Rich is not installed. Install it with: pip install rich")

    # Default: use Rich if available
    if HAS_RICH and RichFormatter is not None:
        return RichFormatter()
    return Formatter()


def get_default_formatter() -> Formatter:
    """Return the best available formatter (RichFormatter if available, else Formatter)."""
    return get_formatter()
