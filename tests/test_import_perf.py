"""Import time regression tests.

These tests ensure startup performance doesn't regress.
Run with: uv run pytest tests/test_import_perf.py -v
"""

import subprocess
import sys

import pytest

# Thresholds in milliseconds (with some margin for CI variability)
CORE_IMPORT_THRESHOLD_MS = 120  # piou core without TUI
TUI_IMPORT_THRESHOLD_MS = 200  # piou + TUI


def measure_import_time(import_statement: str, runs: int = 3) -> float:
    """Measure import time by running Python subprocess."""
    times = []
    for _ in range(runs):
        result = subprocess.run(
            [
                sys.executable,
                "-X",
                "importtime",
                "-c",
                import_statement,
            ],
            capture_output=True,
            text=True,
        )
        # Parse the last line which has total import time
        # Format: "import time:      self |    cumulative | module"
        for line in reversed(result.stderr.strip().split("\n")):
            if "import time:" in line and "piou" in line:
                parts = line.split("|")
                if len(parts) >= 2:
                    cumulative_us = int(parts[1].strip())
                    times.append(cumulative_us / 1000)  # Convert to ms
                    break
    return min(times) if times else 0


@pytest.mark.parametrize(
    "import_stmt,threshold_ms,description",
    [
        pytest.param(
            "from piou import Cli, Option",
            CORE_IMPORT_THRESHOLD_MS,
            "core",
            id="core-import",
        ),
        pytest.param(
            "from piou.tui import TuiContext",
            TUI_IMPORT_THRESHOLD_MS,
            "tui",
            id="tui-import",
        ),
    ],
)
def test_import_time(import_stmt: str, threshold_ms: float, description: str):
    """Verify import time stays under threshold to catch performance regressions."""
    actual_ms = measure_import_time(import_stmt)
    assert actual_ms < threshold_ms, (
        f"piou {description} import took {actual_ms:.1f}ms, "
        f"exceeds threshold of {threshold_ms}ms. "
        f"Check for heavy imports added at module level."
    )
