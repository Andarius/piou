import asyncio
from enum import Enum
from pathlib import Path
from typing import Literal

from typing_extensions import LiteralString

from piou import Cli, Option, Password, Secret
from piou.utils import Regex
from piou.exceptions import CommandError
from piou.formatter import RichFormatter

cli = Cli(description="A Cli tool", formatter=RichFormatter(show_default=True))


@cli.processor()
def processor(
    quiet: bool = Option(False, "-q", "--quiet", help="Do not output any message"),
    verbose: bool = Option(False, "--verbose", help="Increase verbosity"),
):
    print(f"Processing {quiet=} and {verbose=}")


LongLiteral = Literal["foo1", "foo2", "foo3", "foo4"]
UnionLiteral = Literal["foo1"] | Literal["foo2"]


class AnEnum(Enum):
    value_1 = "value-1"
    value_2 = "value-2"


@cli.command(cmd="foo", help="Run foo command")
def foo_main(
    foo1: int = Option(..., help="Foo argument"),
    foo2: str = Option(..., "-f", "--foo2", help="Foo2 argument"),
    foo3: str | None = Option(None, "-g", "--foo3", help="Foo3 argument"),
    foo4: Literal["foo", "bar"] | None = Option(None, "--foo4", help="Foo4 argument", case_sensitive=False),
    foo5: list[int] | None = Option(None, "--foo5", help="Foo5 arguments"),
    foo6: LongLiteral = Option("foo1", "--foo6", help="Foo6 argument"),
    foo7: LongLiteral | None = Option(None, "--foo7", help="Foo7 argument"),
    foo8: UnionLiteral | None = Option(None, "--foo8", help="Foo8 argument"),
    foo9: str | None = Option(None, "--foo9", help="Foo9 argument", choices=[f"item{i}" for i in range(4)]),
    foo10: AnEnum = Option(AnEnum.value_1, "--foo10", help="Foo10 argument"),
    foo11: LiteralString | None = Option(None, "--foo11", help="Foo11 argument"),
    foo12: dict | None = Option(None, "--foo12", help="Foo12 argument"),
    foo13: int | None = Option(None, "--foo13", help="Foo13 argument", choices=lambda: list(range(10))),
    foo14: str | None = Option(None, "--foo14", help="Foo14 argument", choices=["prod", "staging", Regex(r"dev-\d+")]),
    foo_bar: int = Option(..., "--foo-bar", help="Foo bar argument"),
):
    """
    Example command
    """
    print("Running foo")
    for name, value in [
        ("foo1", foo1),
        ("foo2", foo2),
        ("foo3", foo3),
        ("foo4", foo4),
        ("foo5", foo5),
        ("foo6", foo6),
        ("foo7", foo7),
        ("foo8", foo8),
        ("foo9", foo9),
        ("foo10", foo10),
        ("foo11", foo11),
        ("foo12", foo12),
        ("foo_bar", foo_bar),
        ("foo13", foo13),
        ("foo14", foo14),
    ]:
        print(f"{name} = {value} ({type(value)})")


@cli.command(cmd="bar", help="Run bar command")
def bar_main(**kwargs):
    pass


@cli.command(cmd="error", help="Raise an error")
def error_main():
    raise CommandError("An error occurred")


sub_cmd = cli.add_sub_parser(cmd="sub", help="A sub command", propagate_options=True)
sub_cmd.add_option("--test", help="Test mode")


@sub_cmd.command(cmd="bar", help="Run bar command")
def sub_bar_main(foo: Path = Option(Path("/tmp"), "--foo", help="Foo argument"), **kwargs):
    print("Running sub-bar command")
    print(f"foo ({type(foo)})")


@sub_cmd.command(cmd="foo", help="Run foo command")
def sub_foo_main(
    test: bool,
    foo1: int = Option(..., help="Foo argument"),
    foo2: str = Option(..., "-f", "--foo2", help="Foo2 argument"),
    foo3: str | None = Option(None, "--foo3", help="Foo3 argument"),
):
    for name, value in [("test", test), ("foo1", foo1), ("foo2", foo2), ("foo3", foo3)]:
        print(f"{name} = {value} ({type(value)})")


async def _task(task_id: int):
    print(f"Task {task_id} starting")
    try:
        await asyncio.sleep(3)
    except asyncio.CancelledError:
        print(f"Task {task_id} cancelled")
    else:
        print(f"Task {task_id} done")


@cli.command("async-main", help="Run async main with TaskGroup")
async def _async_main():
    async with asyncio.TaskGroup() as tg:
        for i in range(3):
            tg.create_task(_task(i))


@cli.command(cmd="secrets", help="Run secrets command")
def secrets_main(
    password: Password = Option("my-password", "--password", help="Password (fully masked)"),
    # Option-style masking configuration
    token: Secret = Option("sk-12345678", "--token", help="API token (shows first 3 chars)", show_first=3),
    card: Secret = Option("4111111111111234", "--card", help="Card number (shows last 4 chars)", show_last=4),
):
    """
    Example using Password and Secret types.
    You can run it with:
    ```bash
     python -m examples secrets --help
     python -m examples secrets --password secret123 --token sk-abcdef --card 1234567890
    ```
    """
    print(f"password={password}, token={token}, card={card}")


if __name__ == "__main__":
    try:
        cli.run()
    except KeyboardInterrupt:
        print("Ctrl+c detected, exiting...")
