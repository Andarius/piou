<picture>
  <source media="(prefers-color-scheme: dark)" srcset="https://github.com/Andarius/piou/raw/master/docs/static/piou-dark.png">
  <source media="(prefers-color-scheme: light)" srcset="https://github.com/Andarius/piou/raw/master/docs/static/piou.jpg">
  <img alt="Piou logo"
    src="https://github.com/Andarius/piou/raw/master/docs/static/piou.jpg"
    width="250"/>
</picture>

# Piou

[![Python versions](https://img.shields.io/pypi/pyversions/piou)](https://pypi.python.org/pypi/piou)
[![Latest PyPI version](https://img.shields.io/pypi/v/piou?logo=pypi)](https://pypi.python.org/pypi/piou)
[![CI](https://github.com/Andarius/piou/actions/workflows/ci.yml/badge.svg)](https://github.com/Andarius/piou/actions/workflows/ci.yml)
[![Latest conda-forge version](https://img.shields.io/conda/vn/conda-forge/piou?logo=conda-forge)](https://anaconda.org/conda-forge/piou)

A CLI tool to build beautiful command-line interfaces with type validation.

## Quick Example

```python
from piou import Cli, Option

cli = Cli(description='A CLI tool')


@cli.command(cmd='foo', help='Run foo command')
def foo_main(
        bar: int = Option(..., help='Bar positional argument (required)'),
        baz: str = Option(..., '-b', '--baz', help='Baz keyword argument (required)'),
        foo: str | None = Option(None, '--foo', help='Foo keyword argument'),
):
    """
    A longer description on what the function is doing.
    """
    pass


if __name__ == '__main__':
    cli.run()
```

![example](https://github.com/Andarius/piou/raw/master/docs/static/simple-output.svg)

## Installation

```bash
pip install piou
```

Or with [uv](https://docs.astral.sh/uv/):

```bash
uv add piou
```

Or with [conda](https://docs.conda.io/):

```bash
conda install piou -c conda-forge
```

### Without Rich (Raw Formatter)

By default, Piou uses [Rich](https://github.com/Textualize/rich) for beautiful terminal output. If you prefer plain text output or want to minimize dependencies, you can use the raw formatter:

```bash
# Install without Rich formatting (Rich is still installed but not used)
pip install piou[raw]

# Or force raw output via environment variable
PIOU_FORMATTER=raw python your_cli.py --help
```

## Documentation

Full documentation is available at **[andarius.github.io/piou](https://andarius.github.io/piou)**.

### Features

- FastAPI-like developer experience with type hints
- Custom formatters (Rich-based by default)
- Nested command groups / sub-commands
- Derived options for reusable argument patterns
- Async command support
- Type validation and casting
- **Interactive TUI mode** with command suggestions and history

## Why Piou?

I could not find a library that provided:

- The same developer experience as [FastAPI](https://fastapi.tiangolo.com/)
- Customization of the interface (to build a CLI similar to [Poetry](https://python-poetry.org/))
- Type validation / casting

[Typer](https://github.com/tiangolo/typer) is the closest alternative but lacks the possibility to format the output in a custom way using external libraries (like [Rich](https://github.com/Textualize/rich)).

**Piou** provides all these possibilities and lets you define your own Formatter.

## Interactive TUI Mode

Piou includes an optional interactive TUI (Text User Interface) mode powered by [Textual](https://textual.textualize.io/).
This provides a rich terminal experience with command suggestions, history, and inline completions.

### Installation

```bash
pip install piou[tui]
```

### Usage

Enable TUI mode by setting `tui=True` when creating your CLI:

```python
from piou import Cli, Option

cli = Cli(description='My Interactive CLI', tui=True)

@cli.command(cmd='hello', help='Say hello')
def hello(name: str = Option(..., help='Name to greet')):
    print(f'Hello, {name}!')

if __name__ == '__main__':
    cli.run()
```

Or via the `--tui` flag:

```bash
python my_cli.py --tui
```

Or via the `PIOU_TUI=1` environment variable:

```bash
PIOU_TUI=1 python my_cli.py
```

### TUI Features

- **Command suggestions**: Type `/` to see available commands with descriptions
- **Subcommand navigation**: Use `:` to navigate subcommands (e.g., `/stats:uploads`)
- **Inline completions**: See argument placeholders as you type
- **Command history**: Navigate previous commands with up/down arrows (persisted across sessions)
- **Rich output**: ANSI colors and formatting preserved in output
- **Keyboard shortcuts**:
  - `Tab` - Confirm selected suggestion
  - `Up/Down` - Navigate suggestions or history
  - `Ctrl+C` - Clear input (press twice to exit)
  - `Escape` - Quit

<img alt="TUI Demo" src="https://github.com/Andarius/piou/raw/master/docs/static/tui-demo.gif" width="600"/>

### Advanced Example: HTTP Benchmark

The TUI mode supports mounting custom Textual widgets for rich interactive displays. This example benchmarks HTTP libraries with live progress grids:

<img alt="HTTP Benchmark TUI" src="https://github.com/Andarius/piou/raw/master/docs/static/bench_1000.gif" width="700"/>

See [examples/http_bench_tui.py](examples/http_bench_tui.py) for the full implementation using `TuiContext` and custom widgets.

## Development

### Running Tests

```bash
uv run pytest
```

### Generating Documentation

```bash
# Build docs
uv run --group docs mkdocs build

# Serve locally
uv run --group docs mkdocs serve
```

### Generating Screenshots and GIFs

Terminal recordings are created with [VHS](https://github.com/charmbracelet/vhs). Install it first:

```bash
# Ubuntu/Debian
sudo apt install vhs ttyd

# macOS
brew install vhs

# Or via Go
go install github.com/charmbracelet/vhs@latest
```

Then generate recordings from tape files:

```bash
vhs docs/static/tui-demo.tape
```

Tape files are located in `docs/static/` and define scripted terminal sessions that produce GIFs.