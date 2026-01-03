"""Example of using piou's TUI adapter.

Run with:
    python -m examples.tui_example
"""

from typing import Literal

from piou import Cli, Option

cli = Cli(description="Interactive CLI Demo", tui=True)


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


if __name__ == "__main__":
    cli.run()
