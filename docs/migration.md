---
title: "Migrating from Argparse"
---

## Moving from `argparse`

If you are migrating from the standard library `argparse`, here are the key mappings.

### 1. Choices

**Argparse:**
```python
parser.add_argument('--pick', choices=['foo', 'bar'])
```

**Piou:**
```python
# Option A: Literal
pick: Literal['foo', 'bar'] = Option(None, '--pick')

# Option B: Union of Literals
pick: Literal['foo'] | Literal['bar'] = Option(None, '--pick')

# Option C: Explicit choices list
pick: str = Option(None, '--pick', choices=['foo', 'bar'])

# Option D: Dynamic choices from a callable
def get_environments() -> list[str]:
    return ['prod', 'staging', 'dev']

env: str = Option(None, '--env', choices=get_environments)

# Option E: Regex patterns in choices
from piou import Regex

# Accept "prod", "staging", or any string matching "dev-\d+" (e.g., "dev-123")
env: str = Option(None, '--env', choices=['prod', 'staging', Regex(r'dev-\d+')])

# Mix literal values with multiple regex patterns
db_name: str = Option(..., '--db', choices=[
    'production',
    Regex(r'dev-\d+'),           # matches dev-456
])
```

> **Note**: You can disable case sensitivity with `Option(..., case_sensitive=False)` for literal choices.
>
> **Note**: Regex patterns use `fullmatch`, meaning the entire value must match the pattern.
> The `case_sensitive` option only affects literal string choices, not regex patterns.
> For case-insensitive regex matching, use `Regex(r'...', re.IGNORECASE)`.

### 2. Boolean Flags (Store True)

**Argparse:**
```python
parser.add_argument('--verbose', action='store_true')
```

**Piou:**
```python
verbose: bool = Option(False, '--verbose')
```
