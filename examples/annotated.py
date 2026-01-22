from typing import Literal

from piou import Annotated, Cli, Derived, Option

cli = Cli(description="A CLI tool using Annotated syntax")


@cli.command(cmd="foo", help="Run foo command")
def foo_main(
    bar: Annotated[int, Option(..., help="Bar positional argument (required)")],
    baz: Annotated[str, Option(..., "-b", "--baz", help="Baz keyword argument (required)")],
    foo: Annotated[str | None, Option(None, "--foo", help="Foo keyword argument")],
):
    """
    A longer description on what the function is doing.
    You can run it with:
    ```bash
     python -m examples.annotated foo 1 -b baz
    ```
    And you are good to go!
    """
    print(f"bar={bar}, baz={baz}, foo={foo}")


def processor(a: int = Option(1, "-a"), b: int = Option(2, "-b")) -> int:
    return a + b


@cli.command(cmd="derived", help="Run derived command with Annotated syntax")
def derived_main(
    value: Annotated[int, Derived(processor)],
    mode: Annotated[Literal["debug", "release"], Option("debug", "--mode", help="Run mode")],
):
    """
    Example using Annotated with Derived options.
    You can run it with:
    ```bash
     python -m examples.annotated derived -a 3 -b 2 --mode release
    ```
    """
    print(f"value={value}, mode={mode}")


if __name__ == "__main__":
    cli.run()
