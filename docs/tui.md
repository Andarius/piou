---
title: "TUI Mode"
---

!!! warning "Preview Feature"
    TUI mode is currently in preview. APIs may change in future releases.

## Overview

Piou includes an optional interactive TUI (Terminal User Interface) mode powered by [Textual](https://textual.textualize.io/){.highlight-link}. Instead of running commands one at a time, you get a persistent interface with command suggestions, history, and rich output.

<img alt="TUI demo" src="../static/tui-demo.gif" width="800"/>

## Installation

TUI mode requires the `textual` package. Install it with the `tui` extra:

```bash
pip install piou[tui]
```

## Enabling TUI Mode

There are three ways to enable TUI mode:

=== "Constructor argument"

    ```python
    from piou import Cli

    cli = Cli(description="My CLI", tui=True)
    ```

=== "Environment variable"

    ```bash
    PIOU_TUI=1 python my_cli.py
    ```

=== "Runtime flag"

    ```bash
    python my_cli.py --tui
    ```

## Usage

Once in TUI mode, you interact with your CLI through an input prompt:

- **Commands start with `/`** - Type `/hello` to run the `hello` command
- **Arguments follow the command** - `/hello World --loud`
- **Subcommands use `:`** - `/stats:uploads` runs the `uploads` subcommand of `stats`

### Keyboard Shortcuts

| Key | Action |
|-----|--------|
| `Tab` | Accept suggestion and show argument placeholder |
| `Up/Down` | Cycle through suggestions or command history |
| `Enter` | Execute the command |
| `Ctrl+C` | Clear input (press twice to exit) |
| `Escape` | Quit the TUI |

### Command Suggestions

As you type, suggestions appear below the input:

1. Type `/` to see all available commands
2. Continue typing to filter (e.g., `/he` shows `/hello`)
3. Use `Up/Down` arrows to select
4. Press `Tab` to accept and see argument hints

### Subcommand Navigation

For nested commands, use `:` to navigate:

```
/stats:        → shows subcommands of stats
/stats:up      → filters to subcommands starting with "up"
/stats:uploads → runs the uploads subcommand
```

### Command History

Your command history is persisted to `~/.{cli_name}_history`. Use `Up/Down` arrows when the suggestion list is empty to navigate through previous commands.

## Example

```python
from piou import Cli, Option

cli = Cli(description="Interactive CLI Demo", tui=True)

@cli.command(cmd="hello", help="Say hello to someone")
def hello(
    name: str = Option(..., help="Name to greet"),
    loud: bool = Option(False, "-l", "--loud", help="Shout the greeting"),
):
    message = f"Hello, {name}!"
    if loud:
        message = message.upper()
    print(message)

# Subcommands
stats = cli.add_sub_parser(cmd="stats", help="View statistics")

@stats.command(cmd="uploads", help="Show upload statistics")
def stats_uploads(
    days: int = Option(7, "-d", "--days", help="Number of days"),
):
    print(f"Upload stats for {days} days...")

if __name__ == "__main__":
    cli.run()
```

Run it:

```bash
python my_cli.py
# or
python my_cli.py --tui
# or
PIOU_TUI=1 python my_cli.py
```

Then in the TUI:

```
> /hello World --loud
HELLO, WORLD!

> /stats:uploads -d 30
Upload stats for 30 days...
```

## Limitations

- TUI mode captures stdout/stderr, so interactive prompts inside commands won't work as expected
- The `/help` command shows the CLI help; individual command help is shown when you press `Tab` or run `/command --help`