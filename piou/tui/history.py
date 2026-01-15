from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class History:
    file: Path
    entries: list[str] = field(default_factory=list)
    index: int = -1

    def __post_init__(self) -> None:
        if self.file.exists():
            try:
                self.entries = self.file.read_text().strip().split("\n")
            except Exception:
                pass

    def append(self, entry: str) -> None:
        """Add entry to history, persist to file, and reset navigation index."""
        self.entries.insert(0, entry)
        self.index = -1
        try:
            with self.file.open("a") as f:
                f.write(entry + "\n")
        except Exception:
            pass

    def save(self, max_entries: int = 1000) -> None:
        """Save and truncate history file to max entries."""
        try:
            entries = self.entries[:max_entries]
            self.file.write_text("\n".join(entries))
        except Exception:
            pass

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
