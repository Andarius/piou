from __future__ import annotations

import asyncio
import importlib
import sys
from collections.abc import AsyncIterator, Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..command import CommandGroup

__all__ = ("Watcher",)


@dataclass
class Watcher:
    """Watches command source files and reloads them on changes."""

    group: CommandGroup
    on_reload: Callable[[], None] | None = None
    _dirs: set[Path] = field(default_factory=set, init=False)
    _stop_event: asyncio.Event | None = field(default=None, init=False)

    @property
    def active(self) -> bool:
        return self._stop_event is not None and not self._stop_event.is_set()

    def start(self) -> None:
        """Initialize watching state (call before running the watch loop)."""
        self._dirs = self._collect_dirs()
        self._stop_event = asyncio.Event()

    def stop(self) -> None:
        """Stop watching and clear state."""
        if self._stop_event:
            self._stop_event.set()
            self._stop_event = None
        self._dirs = set()

    async def watch(self) -> AsyncIterator[str | None]:
        """Async generator that yields on file changes.

        Yields None on successful reload, or an error message string on failure.
        The generator exits when stop() is called or if watchfiles is unavailable.
        """
        try:
            from watchfiles import PythonFilter, awatch
        except ImportError:
            yield "Dev mode requires watchfiles. Install piou[tui-reload]"
            return

        if not self._dirs or not self._stop_event:
            return

        async for changes in awatch(*self._dirs, watch_filter=PythonFilter(), stop_event=self._stop_event):
            changed_paths = {Path(path) for _, path in changes}
            reloaded, error = self._reload_modules(changed_paths)
            if reloaded:
                yield error

    def _collect_dirs(self) -> set[Path]:
        """Collect the common root directory of command source files."""
        from ..command import Command, CommandGroup

        paths: list[Path] = []

        def collect(group: CommandGroup) -> None:
            for cmd in group.commands.values():
                if isinstance(cmd, Command):
                    module_name = cmd.fn.__module__
                    if module_name in sys.modules:
                        module = sys.modules[module_name]
                        file_path = getattr(module, "__file__", None)
                        if file_path:
                            paths.append(Path(file_path).parent)
                elif isinstance(cmd, CommandGroup):
                    collect(cmd)

        collect(self.group)
        if not paths:
            return set()
        # Find common ancestor of all paths
        common = paths[0]
        for p in paths[1:]:
            while common not in p.parents and common != p:
                common = common.parent
        return {common}

    def _reload_modules(self, changed_paths: set[Path]) -> tuple[bool, str | None]:
        """Reload changed modules and update command functions.

        Returns (reloaded, error) where reloaded is True if any modules were reloaded,
        and error is an error message on failure or None on success.
        """
        from ..command import Command, CommandGroup

        # Find module names for changed paths
        module_names: set[str] = set()
        for path in changed_paths:
            for name, module in sys.modules.items():
                if getattr(module, "__file__", None) == str(path):
                    module_names.add(name)
                    break

        if not module_names:
            return False, None

        # Reload modules
        for module_name in module_names:
            if module_name not in sys.modules:
                continue
            module = sys.modules[module_name]
            try:
                importlib.reload(module)
            except Exception as e:
                return True, f"Reload failed: {e}"

        # Update command function references
        def update_commands(group: CommandGroup) -> None:
            for cmd in group.commands.values():
                if isinstance(cmd, Command):
                    mod_name = cmd.fn.__module__
                    if mod_name in module_names and mod_name in sys.modules:
                        module = sys.modules[mod_name]
                        fn_name = cmd.fn.__name__
                        if hasattr(module, fn_name):
                            cmd.fn = getattr(module, fn_name)
                elif isinstance(cmd, CommandGroup):
                    update_commands(cmd)

        update_commands(self.group)
        if self.on_reload:
            self.on_reload()
        return True, None
