---
title: "Advanced Usage"
---

## Derived Options

Derived options allow you to group multiple arguments into a single object or reuse common argument patterns across commands (like database connection parameters).

  name: material
  custom_dir: overrides


### Static Derived

```python
from piou import Cli, Option, Derived, Password
import psycopg2

def get_pg_conn(
        pg_user: str = Option('postgres', '--pg-user'),
        pg_pwd: Password = Option('postgres', '--pg-pwd'),
        pg_host: str = Option('localhost', '--pg-host'),
        pg_port: int = Option(5432, '--pg-port'),
        pg_db: str = Option('postgres', '--pg-db')
):
    conn = psycopg2.connect(dbname=pg_db, user=pg_user, password=pg_pwd,
                            host=pg_host, port=pg_port)
    return conn

@cli.command(help='Run foo command')
def foo(pg_conn=Derived(get_pg_conn)):
    # pg_conn is the connection object returned by get_pg_conn
    ...
```

### Dynamic Derived

You can also pass arguments to your derived generator functions:

```python
def get_pg_url_dynamic(source: Literal['db1', 'db2']):
    def _derived(
            pg_host: str = Option(..., f'--host-{source}', arg_name=f'--host-{source}'),
            ...
    ):
        return f'...'
    return _derived

@cli.command()
def dynamic(url_1: str = Derived(get_pg_url_dynamic('db1'))):
    ...
```

<img alt="dynamic derived output" src="../static/dynamic-derived.svg" width="800"/>

## On Command Run

For debugging or auditing, you can hook into the command execution lifecycle using `on_cmd_run`.

```python
from piou import Cli, CommandMeta

def on_cmd_run(meta: CommandMeta):
    print(f"Running command: {meta.cmd_name}")
    print(f"Args: {meta.cmd_args}")

cli = Cli(description='A CLI tool', on_cmd_run=on_cmd_run)
```

## Formatters

Piou provides two built-in formatters for help output and error messages.

### RichFormatter (Default)

The default formatter uses [Rich](https://rich.readthedocs.io/) for colorful, styled terminal output.

```python
from piou import Cli
from piou.formatter import RichFormatter

cli = Cli(formatter=RichFormatter(
    cmd_color='cyan',
    option_color='cyan',
    default_color='white',
    show_default=True,
    use_markdown=True,
    code_theme='solarized-dark',
))
```

**Options:**

- `cmd_color` - Color for command names
- `option_color` - Color for option flags
- `default_color` - Color for default values
- `show_default` - Show default values in help output
- `use_markdown` - Parse descriptions as Markdown
- `code_theme` - Pygments theme for code blocks (see [Pygments styles](https://pygments.org/styles/))

### Raw Formatter (Plain Text)

For plain text output without Rich dependencies, use the base `Formatter`:

```python
from piou import Cli
from piou.formatter import Formatter

cli = Cli(formatter=Formatter())
```

### Selecting Formatter

You can select the formatter in several ways:

**1. Environment variable:**

```bash
# Use raw (plain text) formatter
PIOU_FORMATTER=raw python your_cli.py --help

# Use Rich formatter (default)
PIOU_FORMATTER=rich python your_cli.py --help
```

**2. Using `get_formatter()`:**

```python
from piou import Cli
from piou.formatter import get_formatter

# Auto-detect (uses Rich if available, falls back to raw)
cli = Cli(formatter=get_formatter())

# Force specific formatter
cli = Cli(formatter=get_formatter('raw'))
cli = Cli(formatter=get_formatter('rich'))
```

**3. Direct instantiation:**

```python
from piou import Cli
from piou.formatter import Formatter, RichFormatter

cli = Cli(formatter=Formatter())        # Raw
cli = Cli(formatter=RichFormatter())    # Rich
```

### Custom Formatter

You can create your own formatter by subclassing `Formatter`:

```python
from piou.formatter import Formatter

class MyFormatter(Formatter):
    def print_cli_help(self, group):
        # Custom help output
        ...

    def print_error(self, message):
        # Custom error output
        ...
```

## Secret and Password Types

Piou provides special types for handling sensitive values that should be masked in help output.

### Password (Full Masking)

Use `Password` when values should be completely hidden:

```python
from piou import Cli, Option, Password

@cli.command()
def connect(
    password: Password = Option("secret123", "--password", help="Database password"),
):
    pass
```

### Secret (Partial Masking)

Use `Secret` with `show_first` or `show_last` on the Option to reveal part of the value:

```python
from piou import Cli, Option, Secret

@cli.command()
def auth(
    # Show first 3 chars: "sk-******"
    api_key: Secret = Option("sk-12345678", "--api-key", help="API key", show_first=3),
    # Show last 4 chars: "******1234"
    card: Secret = Option("4111111111111234", "--card", help="Card number", show_last=4),
):
    pass
```

Both `Password` and `Secret` types are supported by all formatters to hide or partially mask default values in help output.
