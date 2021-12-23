# Piou

[![Python versions](https://img.shields.io/pypi/pyversions/piou)](https://pypi.python.org/pypi/piou)
[![Latest PyPI version](https://img.shields.io/pypi/v/piou?logo=pypi)](https://pypi.python.org/pypi/piou)
[![CircleCI](https://circleci.com/gh/Andarius/piou/tree/master.svg?style=shield)](https://app.circleci.com/pipelines/github/Andarius/piou?branch=master)
[![Latest conda-forge version](https://img.shields.io/conda/vn/conda-forge/piou?logo=conda-forge)](https://anaconda.org/conda-forge/piou)

A CLI tool to build beautiful command-line interfaces with type validation.

It is as simple as

```python
from piou import Cli, Option

cli = Cli(description='A CLI tool')


@cli.command(cmd='foo',
             help='Run foo command')
def foo_main(
        foo1: int = Option(..., help='Foo arguments'),
        foo2: str = Option(..., '-f', '--foo2', help='Foo2 arguments'),
        foo3: str = Option(None, '-g', '--foo3', help='Foo3 arguments'),
):
    pass


if __name__ == '__main__':
    cli.run()
```

The output will look like this:

![example](https://github.com/Andarius/piou/raw/master/docs/simple-output.png)

# Install

You can install `piou` with either:

- `pip install piou`
- `conda install piou -c conda-forge`

# Features

## Commands

```python
from piou import Cli, Option

cli = Cli(description='A CLI tool')


@cli.command(cmd='foo',
             help='Run foo command')
def foo_main(
        foo1: int = Option(..., help='Foo arguments'),
        foo2: str = Option(..., '-f', '--foo2', help='Foo2 arguments'),
        foo3: str = Option(None, '-g', '--foo3', help='Foo3 arguments'),
):
    pass


@cli.command(cmd='bar',
             help='Run foo command')
def bar_main(
        foo1: int = Option(..., help='Foo arguments'),
        foo2: str = Option(..., '-f', '--foo2', help='Foo2 arguments'),
        foo3: str = Option(None, '-g', '--foo3', help='Foo3 arguments'),
):
    pass


if __name__ == '__main__':
    cli.run()
```  

In this case, `foo1` is a positional argument while `foo2` and `foo3` are keyword arguments.

You can optionally specify global options that will be passed to all commands:

```python
cli = Cli(description='A CLI tool')

cli.add_option('-q', '--quiet', help='Do not output any message')
```

The **help** can also be extracted from the function docstring, both functions here have the same one.

```python
@cli.command(cmd='bar', help='Run foo command')
def bar_main():
    pass


@cli.command(cmd='bar2')
def bar_2_main():
    """
    Run foo command
    """
    pass
```

## Sub-commands

You can group commands into sub-commands:

```python
from piou import Cli, Option

cli = Cli(description='A CLI tool')

sub_cmd = cli.add_sub_parser(cmd='sub', description='A sub command')

sub_cmd.add_option('--dry-run', help='Run in dry run mode')


@sub_cmd.command(cmd='foo', help='Run baz command')
def baz_bar_main(**kwargs):
    pass


@sub_cmd.command(cmd='bar', help='Run toto command')
def toto_main(
        foo1: int = Option(..., help='Foo arguments'),
        foo2: str = Option(..., '-f', '--foo2', help='Foo2 arguments'),
):
    pass


if __name__ == '__main__':
    cli.run()

```

![example](https://github.com/Andarius/piou/raw/master/docs/sub-cmd-output.png)

## Complete example

Here is a more complete example that you can try by running `python -m piou.test`

```python
from piou import Cli, Option

cli = Cli(description='A CLI tool')

cli.add_option('-q', '--quiet', help='Do not output any message')
cli.add_option('--verbose', help='Increase verbosity')


@cli.command(cmd='foo',
             help='Run foo command')
def foo_main(
        quiet: bool,
        verbose: bool,
        foo1: int = Option(..., help='Foo arguments'),
        foo2: str = Option(..., '-f', '--foo2', help='Foo2 arguments'),
        foo3: str = Option(None, '-g', '--foo3', help='Foo3 arguments'),
):
    pass


@cli.command(cmd='bar', help='Run bar command')
def bar_main(**kwargs):
    pass


sub_cmd = cli.add_sub_parser(cmd='sub', description='A sub command')
sub_cmd.add_option('--test', help='Test mode')


@sub_cmd.command(cmd='bar', help='Run baz command')
def baz_bar_main(
        **kwargs
):
    pass


@sub_cmd.command(cmd='toto', help='Run toto command')
def toto_main(
        test: bool,
        quiet: bool,
        verbose: bool,
        foo1: int = Option(..., help='Foo arguments'),
        foo2: str = Option(..., '-f', '--foo2', help='Foo2 arguments'),
):
    pass


if __name__ == '__main__':
    cli.run()
```
