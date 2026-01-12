from .base import Formatter
from .utils import FormatterType, get_formatter

try:
    from .rich_formatter import RichFormatter

    HAS_RICH = True
except ImportError:
    RichFormatter = None  # type: ignore[misc, assignment]
    HAS_RICH = False
