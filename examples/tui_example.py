"""Example of using piou's TUI adapter.

Run with:
    python -m examples.tui_example
"""

import time
from typing import Literal

from piou import Cli, Option
from piou.tui import TuiContext, TuiOption, get_tui_context

cli = Cli(description="Interactive CLI Demo", tui=True)


@cli.tui_on_ready
def processor():
    """Processor that runs before each command to demonstrate TUI notifications."""
    ctx = get_tui_context()
    ctx.notify("TUI Ready!")


@cli.command(cmd="hello", help="Say hello to someone")
def hello(
    name: str = Option(..., help="Name to greet"),
    greeting: str = Option("Hello", "-g", "--greeting", help="Custom greeting"),
    loud: bool = Option(False, "-l", "--loud", help="Shout the greeting"),
):
    """Greet someone with a friendly message."""
    message = f"{greeting}, {name}!"
    if loud:
        message = message.upper()
    print(message)


@cli.command(cmd="add", help="Add two numbers")
def add(
    a: int = Option(..., help="First number"),
    b: int = Option(..., help="Second number"),
):
    """Add two numbers and print the result."""
    result = a + b
    print(f"{a} + {b} = {result}")


@cli.command(cmd="echo", help="Echo a message")
def echo(
    message: str = Option(..., help="Message to echo"),
    times: int = Option(1, "-n", "--times", help="Number of times to repeat"),
):
    """Echo a message multiple times."""
    for _ in range(times):
        print(message)


@cli.command(cmd="format", help="Format text")
def format_text(
    text: str = Option(..., help="Text to format"),
    style: Literal["upper", "lower", "title"] = Option("title", "-s", "--style", help="Text style"),
):
    """Format text in different styles."""
    if style == "upper":
        print(text.upper())
    elif style == "lower":
        print(text.lower())
    else:
        print(text.title())


# Command group with subcommands
stats = cli.add_sub_parser(cmd="stats", help="View statistics")


@stats.command(cmd="uploads", help="Show upload statistics")
def stats_uploads(
    days: int = Option(7, "-d", "--days", help="Number of days to show"),
):
    """Display upload statistics."""
    print(f"Upload statistics for the last {days} days:")
    print("  - Total uploads: 1,234")
    print("  - Total size: 5.6 GB")
    print("  - Average per day: 176 uploads")


@stats.command(cmd="downloads", help="Show download statistics")
def stats_downloads(
    days: int = Option(7, "-d", "--days", help="Number of days to show"),
):
    """Display download statistics."""
    print(f"Download statistics for the last {days} days:")
    print("  - Total downloads: 8,901")
    print("  - Total size: 42.1 GB")
    print("  - Average per day: 1,271 downloads")


# Example using TuiContext for TUI-specific features
@cli.command(cmd="process", help="Process data with notifications")
def process(
    items: int = Option(5, "-n", "--items", help="Number of items to process"),
    ctx: TuiContext = TuiOption(),
):
    """Process items and show TUI notifications."""
    ctx.notify(f"Starting to process {items} items...")

    for i in range(items):
        time.sleep(0.3)
        print(f"Processing item {i + 1}/{items}")

    ctx.notify("Processing complete!", title="Done", severity="information")
    print(f"Successfully processed {items} items")


@cli.command(cmd="warn", help="Show warning notification")
def warn(
    message: str = Option(..., help="Warning message"),
):
    """Show a warning using get_tui_context()."""
    ctx = get_tui_context()
    if ctx.is_tui:
        ctx.notify(message, title="Warning", severity="warning")
    else:
        print(f"WARNING: {message}")


if __name__ == "__main__":
    cli.run()
