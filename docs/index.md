---
title: "Introduction"
---

<img alt="Piou logo" src="./static/piou-dark.png" width="250"/>

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

<img alt="example" src="./static/simple-output.svg" width="800"/>

`python -m examples.simple foo -h`

<img alt="foo command help" src="./static/simple-output-foo.svg" width="800"/>
