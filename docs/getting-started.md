---
title: "Installation & Setup"
---

## Installation

=== "pip"

    ```bash
    pip install piou
    ```

=== "uv"

    ```bash
    uv add piou
    ```

=== "conda"

    ```bash
    conda install piou -c conda-forge
    ```

### Optional: Raw Formatter

By default, Piou uses [Rich](https://rich.readthedocs.io/) for colorful terminal output. If you prefer plain text output, you can use the raw formatter:

```bash
# Via environment variable
PIOU_FORMATTER=raw python your_cli.py --help

# Or programmatically
from piou import Cli
from piou.formatter import get_formatter

cli = Cli(formatter=get_formatter('raw'))
```

## Why Piou?

I could not find a library that provided:

1.  The same developer experience as **FastAPI**.
2.  Customization of the interface (to build a CLI similar to **Poetry**).
3.  Type validation / casting.

**Typer** is the closest alternative in terms of experience but lacks the possibility to format the output in a custom way using external libraries (like **Rich**).

**Piou** provides all these possibilities and lets you define your own Formatter.
