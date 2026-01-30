"""Test app for snapshot testing."""

from piou import Cli, Option

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


# Needed for snap
app = cli.tui_app()

if __name__ == "__main__":
    cli.run()
