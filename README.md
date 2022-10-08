<picture>
  <source media="(prefers-color-scheme: dark)" srcset="https://github.com/Andarius/piou/raw/dev/docs/piou-dark.png">
  <source media="(prefers-color-scheme: light)" srcset="https://github.com/Andarius/piou/raw/dev/docs/piou.jpg">
  <img alt="Piou logo" 
    src="https://github.com/Andarius/piou/raw/dev/docs/piou.jpg"
    width="250"/>
</picture>

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
    """
    A longer description on what the function is doing.
    You can run it with:
    ```bash
     poetry run python -m piou.test.simple foo 1 -b baz
    ```
    And you are good to go!
    """
    pass


if __name__ == '__main__':
    cli.run()
```

The output will look like this:

- `python -m piou.test.simple -h`

![example](https://github.com/Andarius/piou/raw/master/docs/simple-output.png)

- `python -m piou.test.simple foo -h`

![example](https://github.com/Andarius/piou/raw/master/docs/simple-output-foo.png)

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

The **description** can also be extracted from the function docstring. Both functions here return the same description.

```python
@cli.command(cmd='bar', description='Run foo command')
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


sub_cmd = cli.add_sub_parser(cmd='sub', help='A sub command')
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

You can also use the decorator syntax:

```python
from piou import Cli, Option

cli = Cli(description='A CLI tool')


@cli.processor()
def processor(verbose: bool = Option(False, '--verbose', help='Increase verbosity')):
    print(f'Processing {verbose=}')
```

By default, when a processor is set, the global arguments will not be passed downstream.
If you still want them to be passed to the functions by setting

```python
cli = Cli(description='A CLI tool', propagate_options=True)
```

or in the case of a **sub-command**

```python
cli.add_sub_parser(cmd='sub', help='A sub command', propagate_options=True)
```

## Derived Options

Sometimes, you want to reuse the options in multiple command and group them into a single output to pass to
the command. For instance, you might want to group a connection string parameter to connect to a database. Here is a
full example:

```python
from piou import Cli, Option, Derived, Password
import psycopg2

cli = Cli(description='A CLI tool')


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
    ...


@cli.command(help='Run bar command')
def bar(pg_conn=Derived(get_pg_conn)):
    ...
```

You can also pass dynamic derived functions to avoid duplicating the derived logic:

```python
import os
from typing import Literal
from piou import Cli, Option, Derived

cli = Cli(description='A CLI tool')


def get_pg_url_dynamic(source: Literal['db1', 'db2']):
    _source_upper = source.upper()
    _host_arg = f'--host-{source}'
    _db_arg = f'--{source}'

    def _derived(
            # We need to specify the `arg_name` here
            pg_host: str = Option(os.getenv(f'PG_HOST_{_source_upper}', 'localhost'),
                                  _host_arg, arg_name=_host_arg),
            pg_db: str = Option(os.getenv(f'PG_DB_{_source_upper}', source),
                                _db_arg, arg_name=_db_arg),
    ):
        return f'postgresql://postgres:postgres@{pg_host}:5432/{pg_db}'

    return _derived


@cli.command(help='Run dynamic command')
def dynamic(url_1: str = Derived(get_pg_url_dynamic('db1')),
            url_2: str = Derived(get_pg_url_dynamic('db2'))):
    ...
```

So that the output will look like this:

![dynamic-derived](https://github.com/Andarius/piou/raw/master/docs/dynamic-derived.png)

## On Command Run

If you want to get the command name and arguments information that are passed to it (in case of general purpose
debugging for instance), you can pass `on_cmd_run` to the CLI.

```python
from piou import Cli, Option, CommandMeta, Derived


def on_cmd_run(meta: CommandMeta):
    pass


cli = Cli(description='A CLI tool',
          on_cmd_run=on_cmd_run)


def processor(a: int = Option(1, '-a'),
              b: int = Option(2, '-b')):
    return a + b


@cli.command()
def test(
        value: int = Derived(processor),
        bar: str = Option(None, '--bar')
):
    pass
```

In this case, `meta` will be equal to:

```python
CommandMeta(cmd_name='test',
            fn_args={'bar': 'bar', 'value': 5},
            cmd_args={'a': 3, 'b': 2, 'bar': 'bar'})
```

## Help / Errors Formatter

You can customize the help and the different errors displayed by the CLI by passing a Formatter.
The default one is the **Rich formatter** based on the [Rich](https://github.com/Textualize/rich) package:

- `cmd_color`: set the color of the command in the help
- `option_color`: set the color of the positional / keyword arguments in the help
- `default_color`: set the color of the default values in the help
- `show_default`: show the default values if the keyword arguments (if available)

You can create your own Formatter by subclassing the `Formatter` class (see
the [Rich formatter](https://github.com/Andarius/piou/blob/master/piou/formatter/rich_formatter.py)
for example).

The **Rich Formatter** supports the `Password` type that will hide the default value when printing help.  
For instance:

```python
from piou import Password, Option


def test(pg_pwd: Password = Option('postgres', '--pg-pwd')):
    ...
```

## Complete example

You can try a more complete example by running `python -m piou.test -h`

## Moving from `argparse`

If you are migrating code from `argparse` to `piou` here are some differences:

### 1. choices:

`add_argument('--pick', choices=['foo', 'bar'])`  
can be replaced with the following:

- `pick: Literal['foo', 'bar'] = Option(None, '--pick')`
- `pick: Literal['foo'] | Literal['bar'] = Option(None, '--pick')`
- `pick: str = Option(None, '--pick', choices=['foo', 'bar'])`

**Notes**:

- You can disable the case sensitivity by passing `Option(None, '--pick', case_sentitive=False)`
- Specifying both a `Literal` type and `choices` will raise an error.

### 2. action=store_true:

`add_argument('--verbose', action='store_true')`  
can be replaced with  
`verbose: bool = Option(False, '--verbose')`
