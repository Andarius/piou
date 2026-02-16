from __future__ import annotations

from textual.widgets import Static

from .app import TuiApp


class StreamingMessage(Static):
    """A widget that accumulates text incrementally and scrolls to keep up.

    Mount this in the messages area via ``TuiContext.mount_widget()`` and call
    ``append()`` to push new chunks (e.g. LLM tokens). Each call updates the
    display and triggers autoscroll via ``TuiApp._scroll_to_bottom()`` so the
    ``_auto_scroll`` flag is respected.
    """

    def __init__(self, initial: str = "", **kwargs) -> None:
        super().__init__(initial, **kwargs)
        self._text = initial

    def append(self, text: str) -> None:
        """Append text to the message and refresh the display."""
        self._text += text
        self.update(self._text)
        if not isinstance(self.app, TuiApp):
            raise TypeError(f"StreamingMessage must be used inside a TuiApp, got {type(self.app).__name__}")
        self.call_after_refresh(self.app._scroll_to_bottom)
