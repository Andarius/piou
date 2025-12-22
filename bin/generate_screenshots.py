import sys
from pathlib import Path
from unittest.mock import patch
from rich.console import Console
import importlib

# Standardize console for all screenshots
CONSOLE_WIDTH = 100
EXPORT_DIR = Path("docs")


def generate_screenshot(module_name, args, output_filename, title="Terminal"):
    print(f"Generating {output_filename}...")

    # Create a recording console
    console = Console(record=True, width=CONSOLE_WIDTH, color_system="truecolor")

    # Mock sys.argv
    # We set argv[0] to module_name + ".py" so it looks like a real script run
    mock_argv = [f"{module_name.split('.')[-1]}.py"] + args

    with patch("sys.argv", mock_argv), patch("piou.formatter.rich_formatter.Console", return_value=console):
        # Reset modules to force a re-import if necessary, or just import once
        if module_name in sys.modules:
            importlib.reload(sys.modules[module_name])
        else:
            importlib.import_module(module_name)

        # Get the 'cli' object from the module
        cli = getattr(sys.modules[module_name], "cli")

        # Run and catch SystemExit (which piou calls on error or help)
        try:
            cli.run()
        except SystemExit:
            pass

    # Save as SVG
    output_path = EXPORT_DIR / output_filename
    console.save_svg(str(output_path), title=title)
    print(f"Saved to {output_path}")


if __name__ == "__main__":
    # Ensure docs directory exists
    EXPORT_DIR.mkdir(exist_ok=True)

    # 1. simple-output.svg
    generate_screenshot("examples.simple", ["-h"], "simple-output.svg", "simple.py -h")

    # 2. simple-output-foo.svg
    generate_screenshot("examples.simple", ["foo", "-h"], "simple-output-foo.svg", "simple.py foo -h")

    # 3. sub-cmd-output.svg
    # The README sub-command example matches examples.__main__ sub command
    generate_screenshot("examples.__main__", ["sub", "-h"], "sub-cmd-output.svg", "run.py sub -h")

    # 4. dynamic-derived.svg
    generate_screenshot("examples.derived", ["dynamic", "-h"], "dynamic-derived.svg", "derived.py dynamic -h")

    print("\nAll screenshots generated as SVG!")
