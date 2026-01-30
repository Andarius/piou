---
title: "TUI Mode"
---

!!! warning "Beta Feature"
    TUI mode is currently in beta. APIs may change in future releases.

## Overview

Piou includes an optional interactive TUI (Terminal User Interface) mode powered by [Textual](https://textual.textualize.io/){.highlight-link}. Instead of running commands one at a time, you get a persistent interface with command suggestions, history, and rich output.

<img alt="TUI demo" src="../static/tui-demo.gif" width="720"/>

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

## Shell Commands

You can run shell commands directly by prefixing with `!`:

```
> !ls -la
> !git status
> !echo "Hello from shell"
```

## TuiContext

Commands can interact with the TUI through `TuiContext`. Inject it using `TuiOption()`:

```python
from piou import Cli, Option
from piou.tui import TuiContext, TuiOption

cli = Cli(description="My CLI", tui=True)

@cli.command(cmd="greet")
def greet(name: str = Option(...), ctx: TuiContext = TuiOption()):
    ctx.notify(f"Hello, {name}!", title="Greeting")
```

### Available Methods

| Method | Description |
|--------|-------------|
| `ctx.is_tui` | `True` if running in TUI mode |
| `ctx.notify(message, title, severity)` | Show a toast notification |
| `ctx.mount_widget(widget)` | Mount a Textual widget to the output |
| `ctx.prompt(message)` | Await user input (async) |
| `ctx.set_hint(text)` | Set hint text below input |
| `ctx.set_rule_above(...)` | Style the rule above input |
| `ctx.set_rule_below(...)` | Style the rule below input |
| `ctx.set_prompt_style(style)` | Change the input prompt style |

All methods are no-ops in CLI mode, so your commands work in both modes.

### Notifications

```python
@cli.command(cmd="process")
def process(ctx: TuiContext = TuiOption()):
    ctx.notify("Starting...", title="Process", severity="information")
    # ... do work ...
    ctx.notify("Done!", severity="information")
    # severity can be: "information", "warning", "error"
```

### Mounting Widgets

Mount any Textual widget to display rich output:

```python
from textual.widgets import DataTable, ProgressBar

@cli.command(cmd="stats")
async def stats(ctx: TuiContext = TuiOption()):
    table = DataTable()
    table.add_columns("Name", "Value")
    table.add_row("Users", "1,234")
    table.add_row("Events", "56,789")
    ctx.mount_widget(table)
```

### Prompting for Input

```python
@cli.command(cmd="confirm")
async def confirm(ctx: TuiContext = TuiOption()):
    response = await ctx.prompt("Are you sure? (y/n) ")
    if response and response.lower() == "y":
        print("Confirmed!")
    else:
        print("Cancelled")
```

## Lifecycle Hooks

### tui_on_ready

Run code when the TUI is fully initialized:

```python
@cli.tui_on_ready
def on_ready():
    print("TUI is ready!")
```

## Custom Styling

### CSS Parameter

Pass custom CSS to style the TUI:

```python
cli = Cli(
    description="Styled CLI",
    tui=True,
)

# In your app setup or via TuiApp directly:
app = cli.tui_app(css="""
    #name {
        color: cyan;
        text-style: bold;
    }
    .suggestion.selected {
        background: darkblue;
    }
""")
```

### CSS Classes

| Class | Element |
|-------|---------|
| `.suggestion` | Command suggestion items |
| `.selected` | Currently selected suggestion |
| `.message` | User input messages |
| `.output` | Command output |
| `.error` | Error output |

### Widget IDs

| ID | Element |
|----|---------|
| `#name` | CLI name header |
| `#description` | CLI description |
| `#messages` | Messages container |
| `#input-row` | Input row container |
| `#prompt` | Input prompt (`> `) |
| `#suggestions` | Suggestions container |
| `#command-help` | Command help display |
| `#hint` | Hint text |
| `#rule-above` | Rule above input |
| `#rule-below` | Rule below input |

### PromptStyle

Customize the input prompt:

```python
from piou.tui import PromptStyle

@cli.command(cmd="login")
async def login(ctx: TuiContext = TuiOption()):
    # Change prompt for password input
    prev_style = ctx.set_prompt_style(PromptStyle(text="Password: ", css_class="password-prompt"))
    password = await ctx.prompt()
    # Restore previous style
    if prev_style:
        ctx.set_prompt_style(prev_style)
```

## Limitations

- TUI mode captures stdout/stderr, so interactive prompts inside commands won't work as expected (use `ctx.prompt()` instead)
- The `/help` command shows the CLI help; individual command help is shown when you press `Tab` or run `/command --help`