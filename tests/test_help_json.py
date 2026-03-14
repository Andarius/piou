import json
from typing import Annotated, Literal

import pytest
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


def _help_json(cli, capsys, *args) -> dict:
    cli.run_with_args(*args)
    return json.loads(capsys.readouterr().out)


class TestBasicCli:
    @pytest.mark.parametrize(
        "args, expected_name, expected_commands",
        [
            pytest.param(
                ("--help-json",),
                None,
                {"greet", "deploy"},
                id="root-structure",
            ),
            pytest.param(
                ("greet", "--help-json"),
                "greet",
                None,
                id="subcommand",
            ),
        ],
    )
    def test_structure(self, capsys, args, expected_name, expected_commands):
        data = _help_json(_make_cli(), capsys, *args)
        assert data["name"] == expected_name
        if expected_commands is not None:
            assert set(data["commands"]) == expected_commands

    def test_command_arguments(self, capsys):
        data = _help_json(_make_cli(), capsys, "--help-json")
        greet = data["commands"]["greet"]
        assert greet["help"] == "Say hello"
        arg = greet["arguments"][0]
        assert arg == {
            "name": "name",
            "type": "str",
            "required": True,
            "positional": True,
            "help": "Name to greet",
        }

    def test_command_with_flags(self, capsys):
        data = _help_json(_make_cli(), capsys, "--help-json")
        deploy = data["commands"]["deploy"]
        assert deploy["description"] == "Deploy the application"
        args_by_name = {a["name"]: a for a in deploy["arguments"]}
        env = args_by_name["env"]
        assert env["flags"] == ["-e", "--env"]
        assert env["required"] is True
        assert env["choices"] == ["prod", "staging"]
        force = args_by_name["force"]
        assert force["flags"] == ["-f", "--force"]
        assert force["required"] is False
        assert force["default"] is False


class TestNestedGroups:
    @pytest.mark.parametrize(
        "args, expected_name, expected_has_commands",
        [
            pytest.param(
                ("--help-json",),
                None,
                True,
                id="root-shows-group",
            ),
            pytest.param(
                ("db", "--help-json"),
                "db",
                True,
                id="group-level",
            ),
        ],
    )
    def test_nested_group(self, capsys, args, expected_name, expected_has_commands):
        cli = Cli(description="Nested CLI")
        db = cli.add_command_group("db", help="Database commands")

        @db.command(cmd="migrate", help="Run migrations")
        def migrate(version: int = Option(..., "-v", "--version")):
            pass

        data = _help_json(cli, capsys, *args)
        if expected_name is None:
            db_data = data["commands"]["db"]
        else:
            assert data["name"] == expected_name
            db_data = data
        assert db_data["help"] == "Database commands"
        assert "migrate" in db_data["commands"]
        mig = db_data["commands"]["migrate"]
        assert mig["arguments"][0]["name"] == "version"
        assert mig["arguments"][0]["type"] == "int"


class TestChoices:
    @pytest.mark.parametrize(
        "args, choices_fn, expected",
        [
            pytest.param(
                ("--help-json",),
                ["fast", "slow"],
                ["fast", "slow"],
                id="static",
            ),
            pytest.param(
                ("--help-json",),
                lambda: ["a", "b", "c"],
                "<dynamic>",
                id="dynamic-not-resolved",
            ),
            pytest.param(
                ("--help-json=full",),
                lambda: ["a", "b", "c"],
                ["a", "b", "c"],
                id="dynamic-resolved",
            ),
        ],
    )
    def test_choices(self, capsys, args, choices_fn, expected):
        cli = Cli()

        @cli.command(cmd="run")
        def run(mode: str = Option("a", "--mode", choices=choices_fn)):
            pass

        data = _help_json(cli, capsys, *args)
        arg = data["commands"]["run"]["arguments"][0]
        assert arg["choices"] == expected

    def test_hidden_choices(self, capsys):
        from piou.utils import CommandOption

        cli = Cli()
        opt = CommandOption("x", keyword_args=("--mode",), choices=["x", "y"], hide_choices=True)

        @cli.command(cmd="run")
        def run(mode: Annotated[str, opt]):
            pass

        data = _help_json(cli, capsys, "--help-json")
        arg = data["commands"]["run"]["arguments"][0]
        assert "choices" not in arg

    def test_literal_choices(self, capsys):
        cli = Cli()

        @cli.command(cmd="run")
        def run(env: Literal["dev", "prod"] = Option("dev", "--env")):
            pass

        data = _help_json(cli, capsys, "--help-json")
        arg = data["commands"]["run"]["arguments"][0]
        assert arg["choices"] == ["dev", "prod"]


class TestSecrets:
    def test_secret_default_hidden(self, capsys):
        from piou.utils import Secret

        cli = Cli()

        @cli.command(cmd="login")
        def login(token: Secret = Option("s3cret", "--token")):
            pass

        data = _help_json(cli, capsys, "--help-json")
        arg = data["commands"]["login"]["arguments"][0]
        assert "default" not in arg
        assert arg["required"] is False


class TestMainCommand:
    def test_main_excluded(self, capsys):
        cli = Cli()

        @cli.command(cmd="visible", help="Visible")
        def visible():
            pass

        @cli.main(help="Main command")
        def main_cmd(x: str = Option("a", "--x")):
            pass

        data = _help_json(cli, capsys, "--help-json")
        assert "__main__" not in data.get("commands", {})
        assert "visible" in data["commands"]


class TestDerived:
    def test_derived_options_serialized(self, capsys):
        cli = Cli()

        def make_greeting(name: str = Option(..., "--name"), upper: bool = Option(False, "--upper")) -> str:
            return name.upper() if upper else name

        @cli.command(cmd="hello", help="Hello")
        def hello(greeting: Annotated[str, Derived(make_greeting)]):
            pass

        data = _help_json(cli, capsys, "--help-json")
        args_by_name = {a["name"]: a for a in data["commands"]["hello"]["arguments"]}
        assert "name" in args_by_name
        assert "upper" in args_by_name
        assert not any(n.startswith("__") for n in args_by_name)


class TestNegativeFlags:
    def test_negative_flag_in_output(self, capsys):
        cli = Cli()

        @cli.command(cmd="run")
        def run(verbose: bool = Option(True, "--verbose/--no-verbose")):
            pass

        data = _help_json(cli, capsys, "--help-json")
        arg = data["commands"]["run"]["arguments"][0]
        assert arg["flags"] == ["--verbose"]
        assert arg["negative_flag"] == "--no-verbose"


class TestGroupOptions:
    def test_group_options(self, capsys):
        cli = Cli()
        cli.add_option("-v", "--verbose", help="Verbose output")

        @cli.command(cmd="run")
        def run():
            pass

        data = _help_json(cli, capsys, "--help-json")
        assert "options" in data
        opt = data["options"][0]
        assert opt["name"] == "verbose"
        assert opt["flags"] == ["-v", "--verbose"]
