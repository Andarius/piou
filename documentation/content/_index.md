---
title: "Introduction"
date: 2023-10-27
weight: 1
---

<img alt="Piou logo" src="/images/piou.jpg" width="250" class="mb-8 rounded-lg shadow-md"/>

**Piou** is a CLI tool to build beautiful command-line interfaces with type validation.

[![Python versions](https://img.shields.io/pypi/pyversions/piou)](https://pypi.python.org/pypi/piou)
[![Latest PyPI version](https://img.shields.io/pypi/v/piou?logo=pypi)](https://pypi.python.org/pypi/piou)

## Quick Example

It is as simple as:

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

The output will look like this:

`python -m examples.simple -h`

![example](/images/simple-output.png)
