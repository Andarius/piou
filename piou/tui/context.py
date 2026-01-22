from __future__ import annotations

from contextvars import ContextVar
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Literal

from ..utils import Derived

if TYPE_CHECKING:
    from textual.widget import Widget

    from .cli import TuiApp

SeverityLevel = Literal["information", "warning", "error"]


@dataclass
class TuiContext:
    """Context object available to CLI commands for TUI interaction.

    Provides access to TUI features when running in TUI mode,
    with no-op fallbacks when running in standard CLI mode.

    Usage:
        from piou import get_tui_context, TuiOption

        @cli.command()
        def my_command(name: str, ctx: TuiContext = TuiOption()):
            ctx.notify(f"Hello, {name}!")
    """

    tui: TuiApp | None = field(default=None, init=False)

    @property
    def is_tui(self) -> bool:
        """Return True if running in TUI mode."""
        return self.tui is not None

    def notify(
        self,
        message: str,
        *,
        title: str = "",
        severity: SeverityLevel = "information",
    ) -> None:
        """Show a toast notification.

        In TUI mode, displays a toast notification.
        In CLI mode, this is a no-op.

        Args:
            message: The notification message
            title: Optional title for the notification
            severity: One of "information", "warning", or "error"
        """
        if self.tui is not None:
            self.tui.notify(message, title=title, severity=severity)

    def mount_widget(self, widget: Widget) -> None:
        """Mount a Textual widget to the messages area.

        In TUI mode, mounts the widget.
        In CLI mode, this is a no-op.

        Args:
            widget: A Textual Widget to mount
        """
        if self.tui is not None:
            self.tui.mount_widget(widget)


_current_tui_context: ContextVar[TuiContext] = ContextVar("piou_tui_context", default=TuiContext())


def get_tui_context() -> TuiContext:
    """Get the current TUI execution context.

    Returns a TuiContext object that provides access to TUI features
    when running in TUI mode, with no-op fallbacks in CLI mode.

    Usage:
        from piou import get_tui_context

        @cli.command()
        def my_command():
            ctx = get_tui_context()
            if ctx.is_tui:
                ctx.notify("Running in TUI mode!")
    """
    return _current_tui_context.get()


def set_tui_context(ctx: TuiContext) -> None:
    """Set the current TUI execution context. Used internally by TuiApp."""
    _current_tui_context.set(ctx)


def TuiOption() -> TuiContext:
    """Inject the current TUI context into a command.

    Use this as a default value for a TuiContext parameter to get
    automatic context injection.

    Usage:
        from piou import TuiContext, TuiOption

        @cli.command()
        def my_command(name: str, ctx: TuiContext = TuiOption()):
            ctx.notify(f"Hello, {name}!")

    Returns:
        The current TuiContext (injected at runtime)
    """
    return Derived(get_tui_context)
