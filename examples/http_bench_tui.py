"""HTTP library benchmark TUI example using piou with TuiContext.

Compares the speed of aiohttp, httpx, and niquests making concurrent requests,
displaying live progress and results via TUI widgets.

Run with:
    python -m examples.http_bench_tui

Requires:
    pip install niquests aiohttp httpx
"""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass

from rich.text import Text
from textual.containers import Horizontal
from textual.widgets import DataTable, Static

from piou import Cli, Option
from piou.tui import TuiContext, TuiOption

cli = Cli(description="HTTP Library Benchmark", tui=True)

LIBRARIES = ["aiohttp", "httpx", "niquests"]


@dataclass
class BenchResult:
    library: str
    elapsed: float = 0.0
    requests: int = 0
    error: str | None = None

    @property
    def rps(self) -> float:
        return self.requests / self.elapsed if self.elapsed > 0 else 0


async def bench_library(
    lib: str,
    url: str,
    count: int,
    on_progress: asyncio.Queue[tuple[str, int]] | None = None,
    track_progress: bool = True,
) -> BenchResult:
    """Benchmark a single library."""
    result = BenchResult(library=lib, requests=count)
    completed = 0

    async def report_progress() -> None:
        nonlocal completed
        if not track_progress:
            return
        completed += 1
        if on_progress is not None:
            await on_progress.put((lib, completed))

    match lib:
        case "aiohttp":
            import aiohttp

            async def _fetch(client, url: str) -> None:
                async with client.get(url) as r:
                    await r.read()
                await report_progress()

            before = time.perf_counter()
            timeout = aiohttp.ClientTimeout(total=60)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                await asyncio.gather(*[_fetch(session, url) for _ in range(count)])
            result.elapsed = time.perf_counter() - before

        case "httpx":
            import httpx

            async def _fetch(client, url: str) -> None:
                await client.get(url)
                await report_progress()

            before = time.perf_counter()
            async with httpx.AsyncClient(http2=True, timeout=60) as client:
                await asyncio.gather(*[_fetch(client, url) for _ in range(count)])
            result.elapsed = time.perf_counter() - before

        case "niquests":
            import niquests

            async def _fetch(client, url: str) -> None:
                await client.get(url)
                await report_progress()

            before = time.perf_counter()
            async with niquests.AsyncSession(timeout=60) as session:
                await asyncio.gather(*[_fetch(session, url) for _ in range(count)])
            result.elapsed = time.perf_counter() - before
        case _:
            raise ValueError(f"Unknown library: {lib}")

    return result


@cli.command(cmd="grid", help="Side-by-side grid comparison with live progress")
async def grid_view(
    url: str = Option("https://httpbingo.org/get", "-u", "--url", help="URL"),
    count: int = Option(1_000, "-n", "--count", help="Requests per library"),
    best_of: int = Option(1, "-b", "--best-of", help="Best of X runs"),
    ctx: TuiContext = TuiOption(),
):
    """Visual side-by-side comparison using square grids."""
    ctx.notify(f"Starting grid comparison (best of {best_of})...", title="Grid View")

    # Mount info and grid widget in TUI mode
    ctx.mount_widget(Static(f"Target: {url}"))
    info_widget = Static(f"Requests per library: {count} | Best of {best_of}\n")
    ctx.mount_widget(info_widget)
    grid_widget = SideBySideGrids(
        [(lib, 0, count) for lib in LIBRARIES],
        grid_size=10,
    )
    ctx.mount_widget(grid_widget)

    # Track best results per library
    best_results: dict[str, BenchResult] = {}

    for run in range(best_of):
        # Reset progress for new round
        grid_widget.reset_progress(run + 1, best_of)
        info_widget.update(f"Requests per library: {count} | Round {run + 1}/{best_of}\n")

        # Progress queue for real-time updates
        progress_queue: asyncio.Queue[tuple[str, int]] = asyncio.Queue()
        stop_event = asyncio.Event()

        async def progress_consumer() -> None:
            """Consume progress updates and refresh grids."""
            while not stop_event.is_set():
                try:
                    lib, completed = await asyncio.wait_for(progress_queue.get(), timeout=0.1)
                    grid_widget.update_library_progress(lib, completed)
                except asyncio.TimeoutError:
                    continue

        # Start progress consumer
        consumer_task = asyncio.create_task(progress_consumer())

        # Run all benchmarks concurrently
        bench_results = await asyncio.gather(*[bench_library(lib, url, count, progress_queue) for lib in LIBRARIES])

        # Stop consumer
        stop_event.set()
        await consumer_task

        # Keep best result for each library
        for result in bench_results:
            if result.error is None:
                if result.library not in best_results or result.elapsed < best_results[result.library].elapsed:
                    best_results[result.library] = result

    # Update with best results
    final_results = list(best_results.values())
    grid_widget.set_results(final_results)

    # Show winner notification
    if len(final_results) >= 2:
        fastest = min(final_results, key=lambda r: r.elapsed)
        slowest = max(final_results, key=lambda r: r.elapsed)
        speedup = ((slowest.elapsed / fastest.elapsed) - 1) * 100
        ctx.notify(f"{fastest.library} wins! {speedup:.1f}% faster", title="Complete", severity="information")


@cli.command(cmd="bench", help="Raw benchmark without progress tracking")
async def bench_raw(
    url: str = Option("https://httpbingo.org/get", "-u", "--url", help="URL"),
    count: int = Option(100, "-n", "--count", help="Requests per library"),
    best_of: int = Option(1, "-b", "--best-of", help="Best of X runs"),
    ctx: TuiContext = TuiOption(),
):
    """Run benchmarks without progress overhead for raw speed comparison."""
    from textual.widgets import ProgressBar

    ctx.mount_widget(Static(f"Benchmarking {url} x{count} (best of {best_of})"))
    status = Static("Starting...")
    ctx.mount_widget(status)
    progress_bar = ProgressBar(total=best_of * len(LIBRARIES))
    ctx.mount_widget(progress_bar)

    best_results: dict[str, BenchResult] = {}

    for run in range(best_of):
        for lib in LIBRARIES:
            status.update(f"Testing [cyan]{lib}[/] (round {run + 1}/{best_of})")
            result = await bench_library(lib, url, count, track_progress=False)
            if result.error is None:
                if lib not in best_results or result.elapsed < best_results[lib].elapsed:
                    best_results[lib] = result
            progress_bar.advance(1)

    # Show results in a table
    sorted_results = sorted(best_results.values(), key=lambda r: r.elapsed)
    if not sorted_results:
        status.update("No successful results")
        return
    slowest_time = sorted_results[-1].elapsed

    table = DataTable()
    table.add_columns("Library", "Time", "Req/s", "vs slowest")
    for r in sorted_results:
        diff = ((slowest_time / r.elapsed) - 1) * 100
        diff_str = "slowest" if diff == 0 else f"+{diff:.0f}%"
        table.add_row(r.library, f"{r.elapsed:.3f}s", f"{r.rps:.0f}", diff_str)

    status.update("Complete!")
    ctx.mount_widget(table)


@cli.command(cmd="table", help="Show results in a table format")
async def table_view(
    url: str = Option("https://httpbingo.org/get", "-u", "--url", help="URL"),
    count: int = Option(50, "-n", "--count", help="Requests"),
    ctx: TuiContext = TuiOption(),
):
    """Benchmark and display results in a DataTable widget."""
    ctx.notify("Running benchmark...", title="Table View")

    status = Static("Starting...")
    ctx.mount_widget(status)

    results: list[BenchResult] = []

    for lib in LIBRARIES:
        status.update(f"Testing [cyan]{lib}[/]...")
        result = await bench_library(lib, url, count)
        results.append(result)

    table = DataTable()
    table.add_columns("Library", "Time", "Req/s", "Latency", "Status")

    for r in sorted(results, key=lambda x: x.elapsed if x.error is None else 999):
        if r.error:
            table.add_row(r.library, "-", "-", "-", r.error)
        else:
            latency = (r.elapsed / r.requests) * 1000
            table.add_row(
                r.library,
                f"{r.elapsed:.3f}s",
                f"{r.rps:.0f}",
                f"{latency:.1f}ms",
                "OK",
            )

    ctx.mount_widget(table)
    ctx.notify("Results ready", title="Done", severity="information")


# Layout


class SquareGrid(Static):
    """Visual grid of squares showing progress as filled cells."""

    DEFAULT_CSS = """
    SquareGrid {
        width: 1fr;
        height: auto;
        border: round $primary;
        padding: 1;
        margin: 0 1;
        content-align: center middle;
    }
    """

    COLORS = ["green", "yellow", "cyan", "magenta"]

    def __init__(
        self,
        label: str,
        completed: int,
        total: int,
        color: str = "green",
        grid_size: int = 8,
    ):
        super().__init__()
        self.label = label
        self.completed = completed
        self.total = total
        self.color = color
        self.grid_size = grid_size
        self.result: BenchResult | None = None
        self.is_winner: bool = False
        self.pct_diff: float = 0.0
        self.current_round: int = 0
        self.total_rounds: int = 1

    def update_progress(self, completed: int) -> None:
        """Update progress and trigger refresh."""
        self.completed = completed
        self.refresh()

    def set_result(self, result: BenchResult, is_winner: bool = False, pct_diff: float = 0.0) -> None:
        """Set the benchmark result and refresh."""
        self.result = result
        self.is_winner = is_winner
        self.pct_diff = pct_diff
        self.completed = self.total  # Mark as complete
        # Change border color for winner
        if is_winner:
            self.styles.border = ("round", "gold")
        self.refresh()

    def set_round(self, current: int, total: int) -> None:
        """Set the current round info."""
        self.current_round = current
        self.total_rounds = total
        self.refresh()

    def render(self) -> Text:
        # Calculate grid dimensions to fit total requests
        cells_needed = self.grid_size * self.grid_size
        scale = max(1, (self.total + cells_needed - 1) // cells_needed)
        filled_cells = min(self.completed // scale, cells_needed)

        grid_width = self.grid_size * 2  # Each cell is "■ " (char + space)

        # Header: round info or result info with label
        if self.result is not None and not self.result.error:
            # Show emoji before, label, then % after
            if self.pct_diff == 0:
                header_str = f"{self.label} (slowest)"
            elif self.is_winner:
                header_str = f"🏆 {self.label} +{self.pct_diff:.0f}%"
            else:
                header_str = f"{self.label} +{self.pct_diff:.0f}%"
            header = Text.assemble((f"{header_str:^{grid_width}}", f"bold {self.color}"))
        elif self.total_rounds > 1 and self.result is None:
            round_str = f"{self.current_round}/{self.total_rounds}"
            label_str = self.label.center(grid_width - len(round_str))
            header = Text()
            header.append(round_str, style="dim")
            header.append(label_str, style=f"bold {self.color}")
        else:
            header = Text.assemble((f"{self.label:^{grid_width}}", f"bold {self.color}"))

        lines = [header]

        # Build the grid
        filled_char = "■"
        empty_char = "□"

        for row in range(self.grid_size):
            row_text = Text()
            for col in range(self.grid_size):
                cell_idx = row * self.grid_size + col
                if cell_idx < filled_cells:
                    row_text.append(filled_char + " ", style=self.color)
                else:
                    row_text.append(empty_char + " ", style="dim")
            lines.append(row_text)

        # Footer: show progress percentage and result if available
        pct = (self.completed / self.total * 100) if self.total > 0 else 0
        if self.result is not None:
            if self.result.error:
                lines.append(Text(f"{self.result.error:^{grid_width}}", style="red"))
            else:
                stats_str = f"{self.result.elapsed:.2f}s | {self.result.rps:.0f} req/s"
                lines.append(Text(f"{stats_str:^{grid_width}}", style=f"bold {self.color}"))
        else:
            lines.append(Text(f"{pct:.0f}%".center(grid_width), style=f"bold {self.color}"))

        return Text("\n").join(lines)


class SideBySideGrids(Horizontal):
    """Side-by-side comparison of multiple square grids using Horizontal layout."""

    DEFAULT_CSS = """
    SideBySideGrids {
        width: 100%;
        height: auto;
    }
    """

    COLORS = ["green", "yellow", "cyan", "magenta"]

    def __init__(self, grids: list[tuple[str, int, int]], grid_size: int = 8):
        super().__init__()
        self.grids_data = list(grids)  # List of (label, completed, total)
        self.grid_size = grid_size
        self._grid_widgets: list[SquareGrid] = []

    def compose(self):
        """Compose individual SquareGrid widgets horizontally."""
        for i, (label, completed, total) in enumerate(self.grids_data):
            color = self.COLORS[i % len(self.COLORS)]
            grid = SquareGrid(
                label=label,
                completed=completed,
                total=total,
                color=color,
                grid_size=self.grid_size,
            )
            self._grid_widgets.append(grid)
            yield grid

    def reset_progress(self, current_round: int = 0, total_rounds: int = 1) -> None:
        """Reset progress for all grids to 0 and update round info."""
        for grid in self._grid_widgets:
            grid.update_progress(0)
            grid.set_round(current_round, total_rounds)

    def update_library_progress(self, lib: str, completed: int) -> None:
        """Update progress for a specific library grid."""
        for grid in self._grid_widgets:
            if grid.label == lib:
                grid.update_progress(completed)
                break

    def set_results(self, results: list[BenchResult]) -> None:
        """Set results for all grids with winner and percentage diff."""
        valid = [r for r in results if r.error is None]
        fastest = min(valid, key=lambda r: r.elapsed) if valid else None
        slowest = max(valid, key=lambda r: r.elapsed) if valid else None

        for result in results:
            for grid in self._grid_widgets:
                if grid.label == result.library:
                    is_winner = fastest is not None and result.library == fastest.library
                    pct_diff = 0.0
                    # Show how much faster than slowest (based on req/s)
                    if slowest and result.error is None and result.library != slowest.library and slowest.rps > 0:
                        pct_diff = ((result.rps / slowest.rps) - 1) * 100
                    grid.set_result(result, is_winner=is_winner, pct_diff=pct_diff)
                    break


if __name__ == "__main__":
    cli.run()
