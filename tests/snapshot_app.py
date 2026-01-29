"""Test app for snapshot testing."""

import tempfile
from pathlib import Path

from piou import Cli, Option
from piou.tui import TuiApp, TuiState, History
from piou.tui.runner import CommandRunner

# Create a sample CLI for snapshot testing
cli = Cli(description="Test CLI for Snapshots")


@cli.command(cmd="hello", help="Say hello to someone")
def hello(
    name: str = Option(..., help="Name to greet"),
    greeting: str = Option("Hello", "-g", "--greeting", help="Custom greeting"),
):
    print(f"{greeting}, {name}!")


@cli.command(cmd="add", help="Add two numbers")
def add(
    a: int = Option(..., help="First number"),
    b: int = Option(..., help="Second number"),
):
    print(f"{a} + {b} = {a + b}")


@cli.command(cmd="echo", help="Echo a message")
def echo(
    message: str = Option(..., help="Message to echo"),
    times: int = Option(1, "-n", "--times", help="Number of times"),
):
    for _ in range(times):
        print(message)


# Use a temp file for history to avoid polluting user's home
_temp_history = Path(tempfile.gettempdir()) / ".piou_test_snapshot_history"

# Create TuiState
commands = list(cli.commands.values())
state = TuiState(
    cli_name="snapshot-test",
    description=cli.description,
    group=cli.group,
    commands=commands,
    commands_map={f"/{cmd.name}": cmd for cmd in commands},
    history=History(file=_temp_history),
    runner=CommandRunner(
        group=cli.group,
        formatter=cli.formatter,
        hide_internal_errors=True,
    ),
    on_ready=None,
)

app = TuiApp(state=state)

if __name__ == "__main__":
    app.run()
