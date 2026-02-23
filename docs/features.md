---
title: "Core Features"
---

## Commands

Commands are the core building blocks of your CLI. You define them using decorators.

```python
from piou import Cli, Option

cli = Cli(description='A CLI tool')

@cli.command(cmd='foo', help='Run foo command')
def foo_main(
        foo1: int = Option(help='Foo arguments'),
        foo2: str = Option('-f', '--foo2', help='Foo2 arguments'),
        foo3: str | None = Option(None, '-g', '--foo3', help='Foo3 arguments'),
):
    pass
```

In this case:
- `foo1` is a required **positional** argument (no keyword flags, default is `...`).
- `foo2` is a required **keyword** argument (has flags, default is `...`).
- `foo3` is an optional **keyword** argument (has flags, default is `None`).

!!! tip "Optional Ellipsis"
    `Option()` defaults to required (`...`), so `Option(help='...')` is equivalent to `Option(..., help='...')`.

### Global Options

You can specify global options that apply to all commands:

```python
cli = Cli(description='A CLI tool')
cli.add_option('-q', '--quiet', help='Do not output any message')
```

### Docstrings as Descriptions

The description can also be extracted from the function docstring:

```python
@cli.command(cmd='bar2')
def bar_2_main():
    """
    Run foo command
    """
    pass
```

### Async Support

A command can also be asynchronous; it will be run automatically using `asyncio.run`.

```python
@cli.command(cmd='bar', help='Run foo command')
async def bar_main():
    pass
```

## Default Command (Main)

Use the `@cli.main()` decorator (or `is_main=True`) to define a default command that runs when no named command is matched.

```python
@cli.main()
def run_main():
    pass
```

Run it directly:
```bash
python -m examples.simple -h
```

`@cli.main()` can also coexist with named commands. Named commands always take priority, and unmatched input falls back to the default command:

```python
cli = Cli(description='My CLI')

@cli.main()
def default(name: str = Option(...)):
    print(f'Hello {name}')

@cli.command('greet', help='Greet someone')
def greet(name: str = Option(..., '--name')):
    print(f'Greetings, {name}!')
```

```bash
python run.py world          # runs default: "Hello world"
python run.py greet --name a # runs greet: "Greetings, a!"
```

## Command Groups / Sub-commands

You can nest commands arbitrarily deep using command groups.

```python
sub_cmd = cli.add_command_group('sub', help='A sub command')
sub_cmd.add_option('--test', help='Test mode')

@sub_cmd.command(cmd='bar', help='Run bar command')
def sub_bar_main(**kwargs):
    pass
```

Running `python run.py sub -h` will show the specific help for that group.

<img alt="sub command output" src="../static/sub-cmd-output.svg" width="800"/>

## Options Processor

Sometimes you need to intercept global options before a command runs (e.g., to set up logging level).

```python
from piou import Cli, Option

cli = Cli(description='A CLI tool')

@cli.processor()
def processor(verbose: bool = Option(False, '--verbose', help='Increase verbosity')):
    print(f'Processing {verbose=}')
```

By default, processed options are consumed. To pass them down to the command functions as well, use `propagate_options=True` when creating the `Cli` or sub-parser.

You can also use `set_options_processor()` instead of the decorator. Options defined via `Option()` in the function signature are automatically extracted and registered as global options:

```python
cli = Cli(description='A CLI tool')

def processor(
    verbose: bool = Option(False, '-v', '--verbose'),
    log_level: str | None = Option(None, '--log-level'),
):
    ...

cli.set_options_processor(processor)
```

This is equivalent to using the `@cli.processor()` decorator.

## Error Handling

### CommandError

Use `CommandError` to display a user-friendly error message and exit with code 1, without showing a traceback.

```python
from piou import Cli, Option
from piou.exceptions import CommandError

cli = Cli(description='A CLI tool')

@cli.command(cmd='deploy', help='Deploy the application')
def deploy_main(
    env: str = Option(help='Target environment'),
):
    if env not in ('staging', 'production'):
        raise CommandError(f'Unknown environment: {env!r}')
    ...
```

When raised inside a command, `CommandError` is caught by `Cli.run()` and the message is printed using the configured formatter — no Python traceback is shown to the user.

<img alt="command error output" src="../static/command-error-output.svg" width="800"/>
