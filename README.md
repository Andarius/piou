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


@cli.command(cmd='foo', help='Run foo command')
def foo_main(
        bar: int = Option(..., help='Bar positional argument (required)'),
        baz: str = Option(..., '-b', '--baz', help='Baz keyword argument (required)'),
        foo: str = Option(None, '--foo', help='Foo keyword argument'),
):
    pass


if __name__ == '__main__':
    cli.run()
```

The output will look like this:

![example](https://github.com/Andarius/piou/raw/master/docs/simple-output.png)

# Why ?

I could not find a library that provided:

- the same developer experience than [FastAPI](https://fastapi.tiangolo.com/)
- customization of the interface (to build a CLI similar to the one of [Poetry](https://python-poetry.org/))
- type validation / casting

[Typer](https://github.com/tiangolo/typer) is the closest alternative in terms of experience but lacks the possibility
to format the output is a custom way using external libraries (like [Rich](https://github.com/Textualize/rich)).

**Piou** provides all these possibilities and lets you define your own [Formatter](#custom-formatter).

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
             help='Run bar command')
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

A command can also be asynchronous, it will be run automatically using `asyncio.run`.

```python
@cli.command(cmd='bar', help='Run foo command')
async def bar_main():
    pass
```

## Command Groups / Sub-commands

You can group commands into sub-commands:

```python
from piou import Cli, Option

cli = Cli(description='A CLI tool')


@cli.command(cmd='foo', help='Run foo command')
def foo_main():
    pass

sub_cmd = cli.add_sub_parser(cmd='sub', description='A sub command')
sub_cmd.add_option('--test', help='Test mode')


@sub_cmd.command(cmd='bar', help='Run bar command')
def sub_bar_main(**kwargs):
    pass


@sub_cmd.command(cmd='foo', help='Run foo command')
def sub_foo_main(
        test: bool,
        foo1: int = Option(..., help='Foo argument'),
        foo2: str = Option(..., '-f', '--foo2', help='Foo2 argument'),
):
    pass


if __name__ == '__main__':
    cli.run()
```
So when running `python run.py sub -h` it will output the following:  

![example](https://github.com/Andarius/piou/raw/master/docs/sub-cmd-output.png)

## Options processor

Sometimes, you want to run a function using the global arguments before running the actual command (for instance
initialize a logger based on the `verbose` level).

To do so, you use `set_options_processor` that will receive all the current global options of the CLI.

```python
from piou import Cli

cli = Cli(description='A CLI tool')

cli.add_option('--verbose', help='Increase verbosity')

def processor(verbose: bool):
    print(f'Processing {verbose=}')

cli.set_options_processor(processor)
``` 

By default, when a processor is set, the global arguments will not be passed downstream.  
If you still want them to be passed to the functions by setting  

```python
cli = Cli(description='A CLI tool', propagate_options=True)
```

or in the case of a **sub-command**  

```python
cli.add_sub_parser(cmd='sub', description='A sub command', propagate_options=True)
```


## Help / Errors Formatter

You can customize the help and the different errors displayed by the CLI by passing a Formatter.  
The default one is the **Rich formatter** based on the [Rich](https://github.com/Textualize/rich) package:
 - `cmd_color`: set the color of the command in the help
 - `option_color`: set the color of the positional / keyword arguments in the help
 - `show_default`: show the default values if the keyword arguments (if available)

You can create your own Formatter by subclassing the `Formatter` class (see the [Rich formatter](https://github.com/Andarius/piou/blob/master/piou/formatter/rich_formatter.py)
for example).

## Complete example

You can try a more complete example by running `python -m piou.test`


## Moving from `argparse`  

If you are migrating code from `argparse` to `piou` here are some differences:
 - `add_argument('--pick', choices=['foo', 'bar'])` is replaced with 
`pick: Literal['foo', 'bar'] = Option(None, '--pick')`
 - `add_argument('--verbose', action='store_true')` is replaced with `verbose: bool = Option(False, '--verbose')`
