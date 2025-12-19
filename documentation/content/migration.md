---
title: "Migration Guide"
date: 2023-10-27
weight: 5
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
```

> **Note**: You can disable case sensitivity with `Option(..., case_sensitive=False)`.

### 2. Boolean Flags (Store True)

**Argparse:**
```python
parser.add_argument('--verbose', action='store_true')
```

**Piou:**
```python
verbose: bool = Option(False, '--verbose')
```
