"""
Example demonstrating flexible global options positioning.

Global options can be placed at any position in the command line:
- Before the subcommand: mycli -v sub action
- After the subcommand:  mycli sub -v action
- After the command:     mycli sub action -v
- Mixed positions:       mycli -v sub -vv action
"""

from piou import Cli, Option
from piou.command import CommandGroup

cli = Cli(description="Demo: global options at any position")

# Global options defined at CLI level
cli.add_option("-v", "--verbose", help="Enable verbose output")
cli.add_option("-vv", "--debug", help="Enable debug output")
cli.add_option("-c", "--config", help="Config file path", data_type=str, default="")


def on_process(verbose: bool = False, debug: bool = False, config: str = ""):
    """Process global options before command execution."""
    print(f"Global options: {verbose=}, {debug=}, {config=}")


cli.set_options_processor(on_process)

# Create a command group (subcommand)
bench_group = CommandGroup(name="bench", help="Benchmark commands")
cli.add_command_group(bench_group)


@bench_group.command()
def run(
    iterations: int = Option(10, "-n", "--iterations", help="Number of iterations"),
):
    """Run the benchmark."""
    print(f"Running benchmark with {iterations} iterations")


@bench_group.command()
def report():
    """Generate benchmark report."""
    print("Generating report...")


# Direct command on CLI
@cli.command()
def status():
    """Show current status."""
    print("Status: OK")


if __name__ == "__main__":
    cli.run()
