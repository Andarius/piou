from __future__ import annotations

from textual.containers import Vertical
from textual.widgets import Static


class ValuePicker(Vertical):
    """Grid-based picker for option value suggestions.

    Displays choices in a multi-column grid (column-major order) when there are
    more items than `col_size`. Handles up/down (within column) and left/right
    (across columns) navigation.
    """

    DEFAULT_CSS = """
    ValuePicker {
        background: transparent;
        margin-bottom: 1;
        height: auto;
        display: none;
    }

    ValuePicker .vp-item {
        background: transparent;
        padding: 0;
        margin: 0;
        height: 1;
        color: #cc8800;
    }

    ValuePicker .vp-item.vp-selected {
        color: #ffaa00;
    }
    """

    def __init__(self, col_size: int = 10, **kwargs) -> None:
        super().__init__(**kwargs)
        self.col_size = col_size
        self.values: list[str] = []
        self.selected_index: int = -1
        self._grid_cols: int = 0

    @property
    def has_selection(self) -> bool:
        return self.selected_index >= 0

    @property
    def selected_value(self) -> str | None:
        if 0 <= self.selected_index < len(self.values):
            return self.values[self.selected_index]
        return None

    def set_values(self, values: list[str]) -> None:
        """Populate the picker with a list of values."""
        self.remove_children()
        self.values = list(values)
        self.selected_index = 0 if values else -1

        if not values:
            self.display = False
            self._grid_cols = 0
            return

        count = len(values)
        col_width = max(len(v) for v in values) + 2

        if count > self.col_size:
            num_cols = -(-count // self.col_size)
            num_rows = -(-count // num_cols)
            self._grid_cols = num_cols

            # Reorder column-major → row-major for CSS grid display
            reordered: list[str] = []
            for row in range(num_rows):
                for col in range(num_cols):
                    idx = col * num_rows + row
                    if idx < count:
                        reordered.append(values[idx])

            self.values = reordered
            for i, val in enumerate(reordered):
                text = f"{val:<{col_width}}"
                classes = "vp-item vp-selected" if i == 0 else "vp-item"
                self.mount(Static(text, classes=classes))

            self.styles.layout = "grid"
            self.styles.grid_size_columns = num_cols
        else:
            self._grid_cols = 0
            for i, val in enumerate(values):
                text = f"{val:<{col_width}}"
                classes = "vp-item vp-selected" if i == 0 else "vp-item"
                self.mount(Static(text, classes=classes))

        self.display = True

    def clear(self) -> None:
        """Clear all values and hide the picker."""
        self.remove_children()
        self.values = []
        self.selected_index = -1
        self._grid_cols = 0
        self.styles.layout = "vertical"
        self.display = False

    def navigate(self, key: str) -> str | None:
        """Handle navigation keys. Returns the newly selected value, or None."""
        if not self.values:
            return None

        n = len(self.values)
        step = self._grid_cols if self._grid_cols > 0 else 1

        if key == "down":
            new_idx = self.selected_index + step
            if new_idx < n:
                self.selected_index = new_idx
            else:
                # Wrap to top of next column (or first column)
                col = self.selected_index % step
                next_col = (col + 1) % step if step > 1 else 0
                self.selected_index = next_col
        elif key == "up":
            new_idx = self.selected_index - step
            if new_idx >= 0:
                self.selected_index = new_idx
            else:
                # Wrap to bottom of previous column
                col = self.selected_index % step
                prev_col = (col - 1) % step if step > 1 else 0
                last_in_col = prev_col + ((n - 1 - prev_col) // step) * step
                self.selected_index = min(last_in_col, n - 1)
        elif key == "right" and self._grid_cols > 0:
            new_idx = self.selected_index + 1
            self.selected_index = new_idx if new_idx < n else 0
        elif key == "left" and self._grid_cols > 0:
            new_idx = self.selected_index - 1
            self.selected_index = new_idx if new_idx >= 0 else n - 1

        self._update_highlight()
        return self.selected_value

    def _update_highlight(self) -> None:
        for i, child in enumerate(self.query(".vp-item")):
            child.set_class(i == self.selected_index, "vp-selected")
