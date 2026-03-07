import json
from typing import Annotated, Literal

from piou import Cli, Option, Derived


def _make_cli():
    cli = Cli(description="Test CLI")

    @cli.command(cmd="greet", help="Say hello")
    def greet(name: str = Option(..., help="Name to greet")):
        pass

    @cli.command(cmd="deploy", help="Deploy app", description="Deploy the application")
    def deploy(
        env: Literal["prod", "staging"] = Option(..., "-e", "--env", help="Target environment"),
        force: bool = Option(False, "-f", "--force", help="Force deploy"),
    ):
        pass

    return cli


def _capture_help_json(cli, *args) -> dict:
    import io
    import sys

    old_stdout = sys.stdout
    sys.stdout = buf = io.StringIO()
    try:
        cli.run_with_args(*args)
    finally:
        sys.stdout = old_stdout
    return json.loads(buf.getvalue())


class TestBasicCli:
    def test_root_structure(self):
        cli = _make_cli()
        data = _capture_help_json(cli, "--help-json")
        assert data["name"] is None
        assert "commands" in data
        assert set(data["commands"]) == {"greet", "deploy"}

    def test_command_structure(self):
        cli = _make_cli()
        data = _capture_help_json(cli, "--help-json")
        greet = data["commands"]["greet"]
        assert greet["name"] == "greet"
        assert greet["help"] == "Say hello"
        assert len(greet["arguments"]) == 1
        arg = greet["arguments"][0]
        assert arg["name"] == "name"
        assert arg["type"] == "str"
        assert arg["required"] is True
        assert arg["positional"] is True
        assert arg["help"] == "Name to greet"

    def test_command_with_flags(self):
        cli = _make_cli()
        data = _capture_help_json(cli, "--help-json")
        deploy = data["commands"]["deploy"]
        args_by_name = {a["name"]: a for a in deploy["arguments"]}
        env = args_by_name["env"]
        assert env["flags"] == ["-e", "--env"]
        assert env["required"] is True
        assert env["choices"] == ["prod", "staging"]
        force = args_by_name["force"]
        assert force["flags"] == ["-f", "--force"]
        assert force["required"] is False
        assert force["default"] is False

    def test_description(self):
        cli = _make_cli()
        data = _capture_help_json(cli, "--help-json")
        deploy = data["commands"]["deploy"]
        assert deploy["description"] == "Deploy the application"

    def test_subcommand_help_json(self):
        cli = _make_cli()
        data = _capture_help_json(cli, "greet", "--help-json")
        assert data["name"] == "greet"
        assert data["help"] == "Say hello"


class TestNestedGroups:
    def test_nested_group(self):
        cli = Cli(description="Nested CLI")
        db = cli.add_command_group("db", help="Database commands")

        @db.command(cmd="migrate", help="Run migrations")
        def migrate(version: int = Option(..., "-v", "--version")):
            pass

        data = _capture_help_json(cli, "--help-json")
        db_data = data["commands"]["db"]
        assert db_data["name"] == "db"
        assert db_data["help"] == "Database commands"
        assert "migrate" in db_data["commands"]
        mig = db_data["commands"]["migrate"]
        assert mig["arguments"][0]["name"] == "version"
        assert mig["arguments"][0]["type"] == "int"

    def test_nested_subcommand_help_json(self):
        cli = Cli(description="Nested CLI")
        db = cli.add_command_group("db", help="Database commands")

        @db.command(cmd="migrate", help="Run migrations")
        def migrate(version: int = Option(..., "-v", "--version")):
            pass

        data = _capture_help_json(cli, "db", "--help-json")
        assert data["name"] == "db"
        assert "migrate" in data["commands"]


class TestChoices:
    def test_static_choices(self):
        cli = Cli()

        @cli.command(cmd="run")
        def run(mode: str = Option("fast", "--mode", choices=["fast", "slow"])):
            pass

        data = _capture_help_json(cli, "--help-json")
        arg = data["commands"]["run"]["arguments"][0]
        assert arg["choices"] == ["fast", "slow"]

    def test_dynamic_choices_not_resolved(self):
        cli = Cli()

        @cli.command(cmd="run")
        def run(mode: str = Option("a", "--mode", choices=lambda: ["a", "b", "c"])):
            pass

        data = _capture_help_json(cli, "--help-json")
        arg = data["commands"]["run"]["arguments"][0]
        assert arg["choices"] == "<dynamic>"

    def test_dynamic_choices_resolved(self):
        cli = Cli()

        @cli.command(cmd="run")
        def run(mode: str = Option("a", "--mode", choices=lambda: ["a", "b", "c"])):
            pass

        data = _capture_help_json(cli, "--help-json=full")
        arg = data["commands"]["run"]["arguments"][0]
        assert arg["choices"] == ["a", "b", "c"]

    def test_hidden_choices(self):
        from piou.utils import CommandOption

        cli = Cli()
        opt = CommandOption("x", keyword_args=("--mode",), choices=["x", "y"], hide_choices=True)

        @cli.command(cmd="run")
        def run(mode: Annotated[str, opt]):
            pass

        data = _capture_help_json(cli, "--help-json")
        arg = data["commands"]["run"]["arguments"][0]
        assert "choices" not in arg

    def test_literal_choices(self):
        cli = Cli()

        @cli.command(cmd="run")
        def run(env: Literal["dev", "prod"] = Option("dev", "--env")):
            pass

        data = _capture_help_json(cli, "--help-json")
        arg = data["commands"]["run"]["arguments"][0]
        assert arg["choices"] == ["dev", "prod"]


class TestSecrets:
    def test_secret_default_hidden(self):
        from piou.utils import Secret

        cli = Cli()

        @cli.command(cmd="login")
        def login(token: Secret = Option("s3cret", "--token")):
            pass

        data = _capture_help_json(cli, "--help-json")
        arg = data["commands"]["login"]["arguments"][0]
        assert "default" not in arg
        assert arg["required"] is False


class TestMainCommand:
    def test_main_excluded(self):
        cli = Cli()

        @cli.command(cmd="visible", help="Visible")
        def visible():
            pass

        @cli.main(help="Main command")
        def main_cmd(x: str = Option("a", "--x")):
            pass

        data = _capture_help_json(cli, "--help-json")
        assert "__main__" not in data.get("commands", {})
        assert "visible" in data["commands"]


class TestDerived:
    def test_derived_options_serialized(self):
        cli = Cli()

        def make_greeting(name: str = Option(..., "--name"), upper: bool = Option(False, "--upper")) -> str:
            return name.upper() if upper else name

        @cli.command(cmd="hello", help="Hello")
        def hello(greeting: Annotated[str, Derived(make_greeting)]):
            pass

        data = _capture_help_json(cli, "--help-json")
        args_by_name = {a["name"]: a for a in data["commands"]["hello"]["arguments"]}
        assert "name" in args_by_name
        assert "upper" in args_by_name
        # __processor.* args should be filtered
        assert not any(n.startswith("__") for n in args_by_name)


class TestNegativeFlags:
    def test_negative_flag_in_output(self):
        cli = Cli()

        @cli.command(cmd="run")
        def run(verbose: bool = Option(True, "--verbose/--no-verbose")):
            pass

        data = _capture_help_json(cli, "--help-json")
        arg = data["commands"]["run"]["arguments"][0]
        assert arg["flags"] == ["--verbose"]
        assert arg["negative_flag"] == "--no-verbose"


class TestGroupOptions:
    def test_group_options(self):
        cli = Cli()
        cli.add_option("-v", "--verbose", help="Verbose output")

        @cli.command(cmd="run")
        def run():
            pass

        data = _capture_help_json(cli, "--help-json")
        assert "options" in data
        opt = data["options"][0]
        assert opt["name"] == "verbose"
        assert opt["flags"] == ["-v", "--verbose"]
