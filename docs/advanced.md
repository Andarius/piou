---
title: "Advanced Usage"
---

## Derived Options

Derived options allow you to group multiple arguments into a single object or reuse common argument patterns across commands (like database connection parameters).

  name: material
  custom_dir: overrides


### Static Derived

```python
from piou import Cli, Option, Derived, Password
import psycopg2

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
    # pg_conn is the connection object returned by get_pg_conn
    ...
```

### Dynamic Derived

You can also pass arguments to your derived generator functions:

```python
def get_pg_url_dynamic(source: Literal['db1', 'db2']):
    def _derived(
            pg_host: str = Option(..., f'--host-{source}', arg_name=f'--host-{source}'),
            ...
    ):
        return f'...'
    return _derived

@cli.command()
def dynamic(url_1: str = Derived(get_pg_url_dynamic('db1'))):
    ...
```

<img alt="dynamic derived output" src="../static/dynamic-derived.svg" width="800"/>

## On Command Run

For debugging or auditing, you can hook into the command execution lifecycle using `on_cmd_run`.

```python
from piou import Cli, CommandMeta

def on_cmd_run(meta: CommandMeta):
    print(f"Running command: {meta.cmd_name}")
    print(f"Args: {meta.cmd_args}")

cli = Cli(description='A CLI tool', on_cmd_run=on_cmd_run)
```

## Custom Formatter

You can customize the help output and error messages by subclassing `Formatter`.

The default is the **RichFormatter**, which supports:
- `cmd_color`
- `option_color`
- `default_color`
- `show_default`

It also supports the `Password` type to hide default values in help output.
