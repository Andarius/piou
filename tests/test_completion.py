import shutil
import subprocess
import sys
from contextlib import nullcontext
from typing import Literal

import pytest

from piou import Cli, CommandGroup, Option, Regex
from piou.completion import completion_script, get_candidates


def _make_cli() -> Cli:
    cli = Cli(description="Test CLI", tui=True)
    cli.add_option("-vv", help="Verbose")
    cli.add_option("--log-level", help="Log level", data_type=Literal["debug", "info"], default="info")

    cluster = cli.add_command_group("cluster", help="Manage clusters")
    cluster.add_option("--cluster", help="Cluster name", data_type=str, default=None)
    cluster.add_option("--tags", help="Tags", data_type=list[str], default=None)

    @cluster.command(cmd="new", help="Create a cluster")
    def new(
        name: str = Option(..., help="Cluster name"),
        template: Literal["small", "large"] = Option("small", "--template", help="Template"),
        dry: bool = Option(False, "--dry/--no-dry", help="Dry run"),
        region: str = Option("eu", "--region", choices=lambda: ["eu", "us"]),
        env: str = Option("prod", "--env", choices=["prod", Regex(r"dev-\d+")]),
    ):
        pass

    @cluster.command(cmd="scale", help="Scale a cluster")
    def scale(
        size: Literal["s", "m"] = Option(...), zone: str = Option(..., choices=["eu:west", r"a\b", "x\ny", "t\tab"])
    ):
        pass

    server = CommandGroup(name="server", help="Manage servers")
    monitoring = CommandGroup(name="monitoring", help="Monitoring\tstack")
    for name in ("install", "status"):
        monitoring.add_command(lambda: None, cmd=name, help=f"{name} help")
    server.add_group(monitoring)
    server.add_command(lambda: None, cmd="init", help="Init server")
    cli.add_command_group(server)
    return cli


@pytest.mark.parametrize(
    "words, expected",
    [
        pytest.param([""], ["cluster", "server"], id="root"),
        pytest.param([], ["cluster", "server"], id="no-words"),
        pytest.param(["se"], ["server"], id="partial-word"),
        pytest.param(["server", ""], ["init", "monitoring"], id="nested-group"),
        pytest.param(["server", "monitoring", ""], ["install", "status"], id="deep-group"),
        pytest.param(["-vv", "server", "monitoring", "st"], ["status"], id="after-global-flag"),
        pytest.param(["--log-level", "debug", "server", ""], ["init", "monitoring"], id="after-global-value"),
        pytest.param(
            ["cluster", "new", "-"],
            ["--cluster", "--dry", "--env", "--log-level", "--no-dry", "--region", "--tags", "--template", "-vv"],
            id="command-and-global-options",
        ),
        pytest.param(["cluster", "new", "--te"], ["--template"], id="partial-option"),
        pytest.param(["cluster", "new", "--template", ""], ["small", "large"], id="literal-choices"),
        pytest.param(["cluster", "new", "--template", "l"], ["large"], id="literal-choices-partial"),
        pytest.param(["cluster", "new", "--log-level", ""], ["debug", "info"], id="global-option-choices"),
        pytest.param(["cluster", "new", "--region", ""], [], id="dynamic-choices-not-resolved"),
        pytest.param(["cluster", "new", "--env", ""], ["prod"], id="regex-choices-skipped"),
        pytest.param(["cluster", "--tags", "a", "b", "n"], ["new"], id="list-option-values"),
        pytest.param(["cluster", "new", "--cluster", ""], [], id="free-value"),
        pytest.param(["cluster", "new", "foo", ""], [], id="positional"),
        pytest.param(["cluster", "scale", ""], ["s", "m"], id="positional-literal"),
        pytest.param(
            ["cluster", "scale", "s", ""], ["eu:west", "a\\b", "x\ny", "t\tab"], id="second-positional-choices"
        ),
        pytest.param(["nope", ""], [], id="unknown-command"),
        pytest.param(["server", "nope", ""], [], id="unknown-subcommand"),
    ],
)
def test_get_candidates(words, expected):
    assert sorted(v for v, _ in get_candidates(_make_cli().group, words)) == sorted(expected)


def test_candidates_help():
    assert get_candidates(_make_cli().group, ["server", "i"]) == [("init", "Init server")]


@pytest.mark.parametrize(
    "shell, words, expected",
    [
        pytest.param("zsh", ["server", ""], "init:Init server\nmonitoring:Monitoring stack\n", id="zsh"),
        pytest.param(
            "zsh", ["cluster", "scale", "s", ""], "eu\\:west\na\\\\b\n", id="zsh-escaping-and-unrepresentable-values"
        ),
        pytest.param("fish", ["server", ""], "init\tInit server\nmonitoring\tMonitoring stack\n", id="fish"),
        pytest.param("bash", ["server", ""], "init\nmonitoring\n", id="bash"),
        pytest.param("tcsh", ["server", ""], "", id="unknown-shell"),
    ],
)
def test_run_prints_candidates_only(monkeypatch, capsys, shell, words, expected):
    monkeypatch.setenv("_PIOU_COMPLETE", shell)
    monkeypatch.setattr(sys, "argv", ["sctl", *words])
    # tui=True must not start the TUI while completing
    with pytest.raises(SystemExit) as e:
        _make_cli().run()
    assert e.value.code == 0
    assert capsys.readouterr().out == expected


@pytest.mark.parametrize(
    "args, expected",
    [
        pytest.param(("--completions", "zsh"), nullcontext("compdef _sctl sctl"), id="zsh"),
        pytest.param(("--completions", "bash"), nullcontext("complete -o default -F _sctl sctl"), id="bash"),
        pytest.param(("--completions", "fish"), nullcontext("complete -c sctl"), id="fish"),
        pytest.param(("--completions", "tcsh"), pytest.raises(SystemExit, match="1"), id="unknown-shell"),
        pytest.param(("--completions",), pytest.raises(SystemExit, match="1"), id="missing-shell"),
        pytest.param(
            ("--completions", "zsh", "my-alias"), nullcontext("compdef _my_alias my-alias"), id="explicit-prog"
        ),
    ],
)
def test_completions_flag(monkeypatch, capsys, args, expected):
    monkeypatch.setattr(sys, "argv", ["/usr/bin/sctl", *args])
    # tui=True must not start the TUI when emitting the script
    with expected as e:
        _make_cli().run()
    if isinstance(e, str):
        assert e in capsys.readouterr().out


@pytest.mark.parametrize(
    "prog, expected",
    [
        pytest.param("my-cli.py", nullcontext(), id="valid"),
        pytest.param("x; rm -rf ~", pytest.raises(ValueError, match="Invalid program name"), id="injection"),
    ],
)
def test_completion_script_prog(prog, expected):
    with expected:
        completion_script("bash", prog)


@pytest.mark.parametrize(
    "shell, check",
    [
        pytest.param("zsh", ["zsh", "-n"], id="zsh"),
        pytest.param("bash", ["bash", "-n"], id="bash"),
        pytest.param("fish", ["fish", "--no-execute"], id="fish"),
    ],
)
def test_script_syntax(tmp_path, shell, check):
    if shutil.which(check[0]) is None:
        pytest.skip(f"{shell} not installed")
    script = tmp_path / f"completion.{shell}"
    script.write_text(_make_cli().completion_script(shell, prog="sctl"))
    subprocess.run([*check, str(script)], check=True)


async def _async_zones() -> list[str]:
    return ["az1", "az2"]


def _broken_choices() -> list[str]:
    raise RuntimeError("db down")


def _noisy_choices() -> list[str]:
    print("noise")
    return ["n1"]


@pytest.mark.parametrize(
    "cli_kwargs, env, flag, expected",
    [
        pytest.param({}, None, "--region", "", id="off-by-default"),
        pytest.param({}, "1", "--region", "eu\nus\n", id="env-var"),
        pytest.param({"complete_dynamic_choices": True}, None, "--region", "eu\nus\n", id="cli-field"),
        pytest.param({"complete_dynamic_choices": False}, "1", "--region", "", id="cli-field-wins-over-env"),
        pytest.param({"complete_dynamic_choices": True}, None, "--zone", "az1\naz2\n", id="async-choices"),
        pytest.param({"complete_dynamic_choices": True}, None, "--broken", "", id="raising-choices"),
        pytest.param({"complete_dynamic_choices": True}, None, "--noisy", "n1\n", id="printing-choices"),
    ],
)
def test_dynamic_choices(monkeypatch, capsys, cli_kwargs, env, flag, expected):
    if env is None:
        monkeypatch.delenv("PIOU_COMPLETE_DYNAMIC", raising=False)
    else:
        monkeypatch.setenv("PIOU_COMPLETE_DYNAMIC", env)
    cli = Cli(**cli_kwargs)

    @cli.command(cmd="run")
    def run(
        region: str = Option("eu", "--region", choices=lambda: ["eu", "us"]),
        zone: str = Option("az1", "--zone", choices=_async_zones),
        broken: str = Option("", "--broken", choices=_broken_choices),
        noisy: str = Option("", "--noisy", choices=_noisy_choices),
    ):
        pass

    monkeypatch.setenv("_PIOU_COMPLETE", "bash")
    monkeypatch.setattr(sys, "argv", ["prog", "run", flag, ""])
    with pytest.raises(SystemExit, match="0"):
        cli.run()
    assert capsys.readouterr().out == expected
