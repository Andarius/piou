---
title: "Option Reference"
---

## Overview

`Option` defines command-line arguments with type validation, default values, and help text. It supports both positional and keyword arguments.

```python
from piou import Option
```

## Basic Syntax

### Positional Arguments

Arguments without flags are positional. They are required when using `...` (Ellipsis) as default:

```python
@cli.command()
def greet(
    name: str = Option(..., help="Name to greet"),  # required positional
    count: int = Option(1, help="Number of times"),  # optional positional with default
):
    pass
```

Usage: `greet Alice 3`

### Keyword Arguments

Add flag names to create keyword arguments:

```python
@cli.command()
def fetch(
    url: str = Option(..., "-u", "--url", help="URL to fetch"),  # required keyword
    timeout: int = Option(30, "-t", "--timeout", help="Timeout in seconds"),  # optional
):
    pass
```

Usage: `fetch --url https://example.com -t 60`

### Required vs Optional

- **Required**: Use `...` (Ellipsis) as default
- **Optional**: Provide a default value (including `None`)

```python
required_arg: str = Option(..., "--name")      # Must be provided
optional_arg: str = Option("default", "--name") # Has fallback
nullable_arg: str | None = Option(None, "--name")  # Can be omitted
```

## Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `default` | `Any` | Default value. Use `...` for required arguments. |
| `*keyword_args` | `str` | Flag names (e.g., `"-f"`, `"--foo"`). Omit for positional args. |
| `help` | `str \| None` | Help text shown in `--help` output. |
| `choices` | `list \| Callable` | Restrict values to a list or callable returning a list. |
| `case_sensitive` | `bool` | Whether choice matching is case-sensitive. Default: `True`. |
| `raise_path_does_not_exist` | `bool` | For `Path` types, raise error if file doesn't exist. Default: `True`. |
| `show_first` | `int \| None` | For `Secret` types, show first N characters. |
| `show_last` | `int \| None` | For `Secret` types, show last N characters. |
| `replacement` | `str` | Masking character for secrets. Default: `"*"`. |
| `arg_name` | `str \| None` | Override the argument name (used in dynamic Derived). |

## Supported Types

Piou automatically validates and converts values based on type hints:

| Type | Format | Example |
|------|--------|---------|
| `str` | Any string | `"hello"` |
| `int` | Integer | `42` |
| `float` | Decimal number | `3.14` |
| `bool` | Flag (presence = True) | `--verbose` |
| `Path` | File path (must exist) | `./file.txt` |
| `MaybePath` | File path (may not exist) | `./new-file.txt` |
| `date` | ISO format | `2024-01-15` |
| `datetime` | ISO format | `2024-01-15T10:30:00` |
| `UUID` | UUID format | `550e8400-e29b-41d4-a716-446655440000` |
| `dict` | JSON object | `'{"key": "value"}'` |
| `list[T]` | Space-separated values | `item1 item2 item3` |
| `Literal["a", "b"]` | One of the literal values | `a` |
| `Enum` | Enum member name | `DEBUG` |
| `Password` | String (fully masked in help) | `secret123` |
| `Secret` | String (partially masked) | `sk-****` |

### Path Types

```python
from pathlib import Path
from piou import Option, MaybePath

# File must exist (raises FileNotFoundError otherwise)
config: Path = Option(..., "--config")

# File may not exist yet
output: MaybePath = Option(..., "--output")

# Or disable existence check explicitly
log: Path = Option(..., "--log", raise_path_does_not_exist=False)
```

### Boolean Flags

Boolean options act as flags—their presence sets the value to `True`:

```python
verbose: bool = Option(False, "--verbose", "-v")
```

Usage: `command --verbose` sets `verbose=True`

### List Types

Lists are parsed as space-separated values:

```python
files: list[str] = Option(..., "--files")
numbers: list[int] = Option([], "--nums")
```

Usage: `command --files a.txt b.txt c.txt`

## Choices

### Static Choices

```python
env: str = Option(..., "--env", choices=["dev", "staging", "prod"])
```

### Literal Type (Alternative)

```python
from typing import Literal

env: Literal["dev", "staging", "prod"] = Option(..., "--env")
```

### Dynamic Choices

Provide a callable that returns choices at runtime:

```python
def get_environments() -> list[str]:
    return ["dev", "staging", "prod"]

env: str = Option(..., "--env", choices=get_environments)
```

Async callables are also supported:

```python
async def fetch_envs() -> list[str]:
    return await api.get_environments()

env: str = Option(..., "--env", choices=fetch_envs)
```

### Regex Patterns

Use `Regex()` to allow values matching a pattern:

```python
from piou import Regex

# Accept "prod", "staging", or any "dev-{number}" pattern
env: str = Option(..., "--env", choices=[
    "prod",
    "staging",
    Regex(r"dev-\d+"),  # matches dev-1, dev-123, etc.
])
```

For case-insensitive regex, use `re.IGNORECASE`:

```python
import re
from piou import Regex

name: str = Option(..., "--name", choices=[Regex(r"test.*", re.IGNORECASE)])
```

### Case Sensitivity

Disable case sensitivity for literal choices:

```python
# Accepts "yes", "YES", "Yes", etc.
confirm: Literal["yes", "no"] = Option(..., "--confirm", case_sensitive=False)
```

Note: `case_sensitive` only affects literal string choices. For regex, use `re.IGNORECASE`.

## Secret Types

### Password (Full Masking)

Values are completely hidden in help output:

```python
from piou import Password

db_pass: Password = Option("secret", "--password")
# Help shows: --password [default: ********]
```

### Secret (Partial Masking)

Reveal part of the value using `show_first` or `show_last`:

```python
from piou import Secret

# Show first 3 characters
api_key: Secret = Option("sk-12345678", "--api-key", show_first=3)
# Help shows: --api-key [default: sk-*****]

# Show last 4 characters
card: Secret = Option("4111111111111234", "--card", show_last=4)
# Help shows: --card [default: ************1234]
```

### Custom Mask Character

```python
token: Secret = Option("abc123", "--token", show_last=2, replacement="●")
# Help shows: --token [default: ●●●●23]
```

## Annotated Syntax

As an alternative to default value syntax, you can use `Annotated`:

```python
from typing import Annotated
from piou import Option

@cli.command()
def greet(
    name: Annotated[str, Option(..., help="Name to greet")],
    count: Annotated[int, Option(1, "-c", "--count", help="Repeat count")],
):
    pass
```

Both syntaxes can be mixed and are equivalent:

```python
# These are equivalent:
name: str = Option(..., "--name", help="User name")
name: Annotated[str, Option(..., "--name", help="User name")]
```

## Complete Example

```python
from pathlib import Path
from typing import Literal
from piou import Cli, Option, Password, MaybePath, Regex

cli = Cli(description="Database migration tool")

@cli.command(cmd="migrate", help="Run database migrations")
def migrate(
    # Positional arguments
    direction: Literal["up", "down"] = Option(..., help="Migration direction"),

    # Required keyword arguments
    database: str = Option(..., "-d", "--database", help="Database name"),

    # Optional with defaults
    host: str = Option("localhost", "--host", help="Database host"),
    port: int = Option(5432, "--port", help="Database port"),

    # Boolean flag
    dry_run: bool = Option(False, "--dry-run", help="Preview without applying"),

    # Password (masked in help)
    password: Password = Option("", "--password", help="Database password"),

    # Path that may not exist
    output: MaybePath = Option(None, "--output", help="Output log file"),

    # Dynamic choices with regex
    env: str = Option("dev", "--env", choices=["prod", "staging", Regex(r"dev-\d+")]),
):
    pass

if __name__ == "__main__":
    cli.run()
```