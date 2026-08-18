# PEP 810: textual-heavy modules are lazy on Python >= 3.15, ignored on older versions
__lazy_modules__ = ["piou.tui.app", "piou.tui.cli", "piou.tui.widgets"]

from .app import TuiApp, PromptStyle, CssClass
from .cli import TuiCli, TuiState
from .context import TuiContext, TuiOption, get_tui_context, set_tui_context, SeverityLevel
from .history import History
from .widgets import StreamingMessage

__all__ = (
    "CssClass",
    "History",
    "PromptStyle",
    "SeverityLevel",
    "StreamingMessage",
    "TuiApp",
    "TuiCli",
    "TuiContext",
    "TuiOption",
    "TuiState",
    "get_tui_context",
    "set_tui_context",
)
