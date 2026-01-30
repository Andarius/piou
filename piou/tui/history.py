from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class History:
    file: Path
    entries: list[str] = field(default_factory=list)
    index: int = -1
    last_error: str | None = None

    def __post_init__(self) -> None:
        if not self.file.exists():
            return
        try:
            lines = self.file.read_text(encoding="utf-8").splitlines()
        except (OSError, UnicodeDecodeError) as exc:
            self.last_error = f"Failed to read history file {self.file}: {exc}"
            return
        self.entries = [line for line in reversed(lines) if line]
        self.last_error = None

    def append(self, entry: str) -> bool:
        """Add entry to history, persist to file, and reset navigation index."""
        self.entries.insert(0, entry)
        self.index = -1
        try:
            with self.file.open("a", encoding="utf-8") as f:
                f.write(entry + "\n")
        except OSError as exc:
            self.last_error = f"Failed to append history file {self.file}: {exc}"
            return False
        self.last_error = None
        return True

    def save(self, max_entries: int = 1000) -> bool:
        """Save and truncate history file to max entries."""
        try:
            entries = self.entries[:max_entries]
            self.file.write_text("\n".join(entries), encoding="utf-8")
        except OSError as exc:
            self.last_error = f"Failed to save history file {self.file}: {exc}"
            return False
        self.last_error = None
        return True

    def navigate(self, direction: str) -> str | None:
        """Navigate history up/down, return entry or None if at boundary."""
        if not self.entries:
            return None
        if direction == "up":
            self.index = min(self.index + 1, len(self.entries) - 1)
        else:
            self.index = max(self.index - 1, -1)
        return self.entries[self.index] if self.index >= 0 else None

    def reset_index(self) -> None:
        """Reset navigation index."""
        self.index = -1
