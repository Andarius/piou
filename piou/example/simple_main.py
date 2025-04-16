from piou import Cli, Option
from typing import Optional

cli = Cli(description="A CLI tool")


@cli.main(help="Run command")
def foo_main(
    bar: int = Option(..., help="Bar positional argument (required)"),
    baz: str = Option(..., "-b", "--baz", help="Baz keyword argument (required)"),
    foo: Optional[str] = Option(None, "--foo", help="Foo keyword argument"),
):
    """
    A longer description on what the function is doing.
    You can run it with:
    ```bash
     poetry run python -m piou.example.simple_main 1 -b baz
    ```
    And you are good to go!
    """
    pass


if __name__ == "__main__":
    cli.run()
