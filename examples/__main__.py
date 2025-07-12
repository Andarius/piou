from enum import Enum
from pathlib import Path
from typing import Literal, Union, Optional

from typing_extensions import LiteralString

from piou import Cli, Option
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
UnionLiteral = Union[Literal["foo1"], Literal["foo2"]]


class AnEnum(Enum):
    value_1 = "value-1"
    value_2 = "value-2"


@cli.command(cmd="foo", help="Run foo command")
def foo_main(
    foo1: int = Option(..., help="Foo argument"),
    foo2: str = Option(..., "-f", "--foo2", help="Foo2 argument"),
    foo3: Optional[str] = Option(None, "-g", "--foo3", help="Foo3 argument"),
    foo4: Optional[Literal["foo", "bar"]] = Option(None, "--foo4", help="Foo4 argument", case_sensitive=False),
    foo5: Optional[list[int]] = Option(None, "--foo5", help="Foo5 arguments"),
    foo6: LongLiteral = Option("foo1", "--foo6", help="Foo6 argument"),
    foo7: Optional[LongLiteral] = Option(None, "--foo7", help="Foo7 argument"),
    foo8: Optional[UnionLiteral] = Option(None, "--foo8", help="Foo8 argument"),
    foo9: Optional[str] = Option(None, "--foo9", help="Foo9 argument", choices=[f"item{i}" for i in range(4)]),
    foo10: AnEnum = Option(AnEnum.value_1, "--foo10", help="Foo10 argument"),
    foo11: Optional[LiteralString] = Option(None, "--foo11", help="Foo11 argument"),
    foo12: Optional[dict] = Option(None, "--foo12", help="Foo12 argument"),
    foo13: Optional[int] = Option(None, "--foo13", help="Foo13 argument", choices=lambda: list(range(10))),
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
    ]:
        print(f"{name} = {value} ({type(value)})")


@cli.command(cmd="bar", help="Run bar command")
def bar_main(**kwargs):
    pass


@cli.command(cmd="error", help="Raise an error")
def error_main():
    raise CommandError("An error occurred")


sub_cmd = cli.add_sub_parser(cmd="sub", help="A sub command")
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
    foo3: Optional[str] = Option(None, "--foo3", help="Foo3 argument"),
):
    for name, value in [("test", test), ("foo1", foo1), ("foo2", foo2), ("foo3", foo3)]:
        print(f"{name} = {value} ({type(value)})")


if __name__ == "__main__":
    cli.run()
