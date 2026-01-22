from typing import Literal

import pytest

from piou.utils import Password, Secret


@pytest.mark.parametrize(
    "options, input, expected",
    [
        ({"use_markdown": True}, "**test**", "\nDESCRIPTION\n test"),
        (
            {"use_markdown": True},
            "[bold]test[/bold]",
            "\nDESCRIPTION\n [bold]test[/bold]",
        ),
        ({"use_markdown": False}, "**test**", "\nDESCRIPTION\n **test**"),
        ({"use_markdown": False}, "[bold]test[/bold]", "\nDESCRIPTION\n test"),
    ],
)
def test_rich_formatting_options(options, input, expected, capsys):
    from piou.formatter import RichFormatter
    from piou.command import Command

    formatter = RichFormatter(**options)
    formatter._print_description(Command("", lambda x: ..., description=input))
    assert capsys.readouterr().out.rstrip() == expected


@pytest.mark.parametrize(
    "value, show_first, show_last, expected",
    [
        pytest.param("", 0, 0, "******", id="empty_string"),
        pytest.param("abc123", 0, 0, "******", id="full_mask"),
        pytest.param("sk-12345678", 3, 0, "sk-******", id="show_first_3"),
        pytest.param("4111111111111234", 0, 4, "******1234", id="show_last_4"),
        pytest.param("abc123xyz", 3, 3, "abc***xyz", id="show_both"),
        pytest.param("short", 3, 3, "short", id="too_short_to_mask"),
        pytest.param("abcdef", 3, 3, "abcdef", id="exact_length_no_mask"),
        pytest.param("a]", 0, 0, "**", id="short_value"),
    ],
)
def test_mask_secret(value, show_first, show_last, expected):
    from piou.formatter.utils import mask_secret

    assert mask_secret(value, show_first, show_last) == expected


@pytest.mark.parametrize(
    "default, data_type,show_default,expected",
    [
        pytest.param("hello", Password, True, "(default: *****)", id="Password"),
        pytest.param("sk-12345678", Secret(show_first=3), True, "(default: sk-******)", id="Secret_show_first"),
        pytest.param("4111111111111234", Secret(show_last=4), True, "(default: ******1234)", id="Secret_show_last"),
        pytest.param("abc123xyz", Secret(show_first=3, show_last=3), True, "(default: abc***xyz)", id="Secret_both"),
        pytest.param("token123", Secret(), True, "(default: ******)", id="Secret_full_mask"),
        pytest.param(
            None,
            Literal["foo", "bar"],
            True,
            "(choices are: foo, bar)",
            id="Small Literal",
        ),
        pytest.param(
            None,
            Literal["foo", "bar", "baz", "others"],
            True,
            "\nPossible choices are: \n - foo \n - bar \n - baz \n - others",
            id="Large Literal",
        ),
    ],
)
def test_fmt_help(default, data_type, show_default, expected):
    from piou.formatter.rich_formatter import fmt_help
    from piou.utils import CommandOption

    option = CommandOption(default)
    option.data_type = data_type
    output = fmt_help(option, show_default, markdown_open=None, markdown_close=None)
    assert output == expected


def get_simple_cli(formatter):
    from piou import Cli, Option, Password

    cli = Cli(description="A CLI tool", formatter=formatter)

    @cli.command(cmd="foo", help="Run foo command")
    def foo_main(
        foo1: int = Option(..., help="Foo arguments"),
        foo2: str = Option(..., "-f", "--foo2", help="Foo2 arguments"),
        foo3: str = Option("a-value", "-g", "--foo3", help="Foo3 arguments"),
        pwd: Password = Option("a-password", "-p", help="Password"),
    ):
        pass

    return cli


def get_simple_cli_with_global_opt(formatter):
    from piou import Cli, Option

    cli = Cli(description="A CLI tool", formatter=formatter)
    cli.add_option("-q", "--quiet", help="Do not output any message")
    cli.add_option("--verbose", help="Increase verbosity")

    @cli.command(cmd="foo", help="Run foo command")
    def foo_main(
        foo1: int = Option(..., help="Foo arguments"),
        foo2: str = Option(..., "-f", "--foo2", help="Foo2 arguments"),
        foo3: str = Option(None, "-g", "--foo3", help="Foo3 arguments"),
    ):
        pass

    return cli


def get_cmd_group_cli_with_global_opt(formatter):
    from piou import Cli, Option

    cli = Cli(description="A CLI tool", formatter=formatter)
    cli.add_option("-q", "--quiet", help="Do not output any message")
    cli.add_option("--verbose", help="Increase verbosity")

    sub_cmd = cli.add_sub_parser("sub-cmd", help="A sub command")

    sub_cmd.add_option("-t", "--test", help="Test mode")

    @sub_cmd.command(cmd="foo", help="Run foo command")
    def foo_main(
        foo3: str = Option("a sub value", "-g", "--foo3", help="Foo3 arguments"),
        foo2: str = Option(..., "-f", "--foo2", help="Foo2 arguments"),
        foo1: int = Option(..., help="Foo arguments"),
    ):
        pass

    @sub_cmd.command(cmd="bar", help="Run bar command")
    def bar_main(**kwargs):
        pass

    sub_cmd2 = cli.add_sub_parser("sub-cmd2", help="Another sub command")

    @sub_cmd2.command(cmd="bar", help="Run bar command")
    def another_bar_main(**kwargs):
        pass

    return cli


def get_cli_full(formatter):
    from piou import Cli, Option

    cli = Cli(description="A CLI tool", formatter=formatter)

    cli.add_option("-q", "--quiet", help="Do not output any message")
    cli.add_option("--verbose", help="Increase verbosity")

    @cli.command(cmd="foo", help="Run foo command")
    def foo_main(
        quiet: bool,
        verbose: bool,
        foo1: int = Option(..., help="Foo arguments"),
        foo2: str = Option(..., "-f", "--foo2", help="Foo2 arguments"),
        foo3: str = Option(None, "-g", "--foo3", help="Foo3 arguments"),
    ):
        pass

    @cli.command(cmd="bar", help="Run bar command")
    def bar_main():
        pass

    baz_cmd = cli.add_sub_parser(cmd="baz", help="A sub command")
    baz_cmd.add_option("--test", help="Test mode")

    @baz_cmd.command(cmd="bar", help="Run baz command")
    def baz_bar_main(**kwargs):
        pass

    @baz_cmd.command(cmd="toto", help="Run toto command")
    def toto_main(
        test: bool,
        quiet: bool,
        verbose: bool,
        foo1: int = Option(..., help="Foo arguments"),
        foo2: str = Option(..., "-f", "--foo2", help="Foo2 arguments"),
    ):
        pass

    return cli


_SIMPLE_CLI_OUTPUT_RICH = """
USAGE 
 pytest <command> 

AVAILABLE COMMANDS
     foo                        Run foo command    

DESCRIPTION
 A CLI tool
"""

_SIMPLE_CLI_COMMAND_RICH = """
USAGE 
 pytest foo <foo1> [-f] [-g] [-p]                                                                                                    

ARGUMENTS
    <foo1>                      Foo arguments    

OPTIONS
    -f (--foo2)*                Foo2 arguments    
    -g (--foo3)                 Foo3 arguments    
    -p                          Password            

DESCRIPTION
 Run foo command
"""  # noqa

_SIMPLE_CLI_WITH_OPTS_OUTPUT_RICH = """
USAGE 
 pytest [-q] [--verbose] <command> 

GLOBAL OPTIONS
    -q (--quiet)                Do not output any message    
    --verbose                   Increase verbosity           

AVAILABLE COMMANDS
     foo                        Run foo command    

DESCRIPTION
 A CLI tool
"""  # noqa

_SIMPLE_CLI_WITH_OPTS_CMD_OUTPUT_RICH = """
USAGE 
 pytest [-q] [--verbose] foo <foo1> [-f] [-g]                                                                                        

ARGUMENTS
    <foo1>                      Foo arguments    

OPTIONS
    -f (--foo2)*                Foo2 arguments    
    -g (--foo3)                 Foo3 arguments    

GLOBAL OPTIONS
    -q (--quiet)                Do not output any message    
    --verbose                   Increase verbosity           

DESCRIPTION
 Run foo command
"""  # noqa

_SIMPLE_CLI_SUB_CMD_RICH = """
USAGE 
 pytest [-q] [--verbose] <command> 

GLOBAL OPTIONS
    -q (--quiet)                Do not output any message    
    --verbose                   Increase verbosity           

AVAILABLE COMMANDS
     sub-cmd                    A sub command    
     sub-cmd2                   Another sub command

DESCRIPTION
 A CLI tool
"""  # noqa

_SIMPLE_CLI_SUB_CMD_HELP_RICH = """
USAGE
     pytest sub-cmd [-t] bar 
 or: pytest sub-cmd [-t] foo <foo1> [-f] [-g]

COMMANDS
  bar                                                                                                                                      
    Run bar command                                                                                                                        

  foo                                                                                                                                      
    Run foo command                                                                                                                        

    <foo1>                      Foo arguments     
    -f (--foo2)*                Foo2 arguments    
    -g (--foo3)                 Foo3 arguments    

OPTIONS
    -t (--test)                 Test mode    

GLOBAL OPTIONS
    -q (--quiet)                Do not output any message    
    --verbose                   Increase verbosity           

DESCRIPTION
 A sub command
"""  # noqa

_SIMPLE_CLI_SUB_CMD2_HELP = """
USAGE
     pytest sub-cmd2 bar 

COMMANDS
  bar                                                                                                                                                                                                                                       
    Run bar command                                                                                                                                                                                                                         

GLOBAL OPTIONS
    -q (--quiet)                Do not output any message    
    --verbose                   Increase verbosity           

DESCRIPTION
 Another sub command
"""  # noqa

_SIMPLE_CLI_SUB_CMD_CMD_RICH = """
USAGE 
 pytest sub-cmd [-t] foo <foo1> [-f] [-g] 

ARGUMENTS
    <foo1>                      Foo arguments    

OPTIONS
    -f (--foo2)*                Foo2 arguments    
    -g (--foo3)                 Foo3 arguments    

GLOBAL OPTIONS
    -t (--test)                 Test mode                    
    -q (--quiet)                Do not output any message    
    --verbose                   Increase verbosity           

DESCRIPTION
 Run foo command
"""  # noqa

_PARAMS = [
    pytest.param(get_simple_cli, ["-h"], _SIMPLE_CLI_OUTPUT_RICH, id="Simple CLI"),
    pytest.param(get_simple_cli, ["foo", "-h"], _SIMPLE_CLI_COMMAND_RICH, id="Simple CLI cmd"),
    pytest.param(
        get_simple_cli_with_global_opt,
        ["-h"],
        _SIMPLE_CLI_WITH_OPTS_OUTPUT_RICH,
        id="Simple CLI with opts",
    ),
    pytest.param(
        get_simple_cli_with_global_opt,
        ["foo", "-h"],
        _SIMPLE_CLI_WITH_OPTS_CMD_OUTPUT_RICH,
        id="Simple CLI with opts cmd",
    ),
    pytest.param(
        get_cmd_group_cli_with_global_opt,
        ["-h"],
        _SIMPLE_CLI_SUB_CMD_RICH,
        id="Simple CLI sub-cmd",
    ),
    pytest.param(
        get_cmd_group_cli_with_global_opt,
        ["sub-cmd", "-h"],
        _SIMPLE_CLI_SUB_CMD_HELP_RICH,
        id="Simple CLI sub-cmd help",
    ),
    pytest.param(
        get_cmd_group_cli_with_global_opt,
        ["sub-cmd2", "-h"],
        _SIMPLE_CLI_SUB_CMD2_HELP,
        id="Simple CLI sub-cmd 2 help",
    ),
    pytest.param(
        get_cmd_group_cli_with_global_opt,
        ["sub-cmd", "foo", "-h"],
        _SIMPLE_CLI_SUB_CMD_CMD_RICH,
        id="Simple CLI sub-cmd cmd",
    ),
    # # Errors
    pytest.param(
        get_simple_cli,
        ["foo", "-vvv"],
        "Could not find keyword parameter '-vvv' for command 'foo'",
        id="Simple CLI keyword error",
    ),
    pytest.param(
        get_simple_cli,
        ["foo"],
        "Expected 1 positional arguments but got 0 for command foo",
        id="Simple CLI keyword error",
    ),
]


def _compare_str(output, expected):
    output_lines, expected_lines = output.split("\n"), expected.split("\n")
    assert len(output_lines) == len(expected_lines), print(output)

    for output_line, expected_line in zip(output_lines, expected_lines):
        assert output_line.rstrip() == expected_line.rstrip(), print(output)


@pytest.mark.parametrize("cli_fn, args, expected", _PARAMS)
def test_rich_formatting(cli_fn, args, expected, capsys, sys_exit_counter, request):
    from piou.formatter import RichFormatter

    cli = cli_fn(RichFormatter(show_default=False))

    cli.run_with_args(*args)

    output = capsys.readouterr().out
    _compare_str(output.strip(), expected.strip())
    assert sys_exit_counter() == (1 if "error" in request.node.callspec.id else 0)


_SIMPLE_CLI_COMMAND_RICH_DEFAULT = """
USAGE 
 pytest foo <foo1> [-f] [-g] [-p]                                                                                                    

ARGUMENTS
    <foo1>                      Foo arguments    

OPTIONS
    -f (--foo2)*                Foo2 arguments                       
    -g (--foo3)                 Foo3 arguments (default: a-value)    
    -p                          Password (default: ******)  

DESCRIPTION
 Run foo command
"""  # noqa

_SIMPLE_CLI_SUB_CMD_HELP_DEFAULT = """
USAGE
     pytest sub-cmd [-t] bar 
 or: pytest sub-cmd [-t] foo <foo1> [-f] [-g]

COMMANDS
  bar                                                                                                                                      
    Run bar command                                                                                                                        

  foo                                                                                                                                      
    Run foo command                                                                                                                        

    <foo1>                      Foo arguments     
    -f (--foo2)*                Foo2 arguments    
    -g (--foo3)                 Foo3 arguments (default: a sub value)

OPTIONS
    -t (--test)                 Test mode (default: False)

GLOBAL OPTIONS
    -q (--quiet)                Do not output any message (default: False)
    --verbose                   Increase verbosity (default: False)       

DESCRIPTION
 A sub command
"""  # noqa

_SIMPLE_CLI_SUB_CMD_CMD_DEFAULT = """
USAGE 
 pytest sub-cmd [-t] foo <foo1> [-f] [-g] 

ARGUMENTS
    <foo1>                      Foo arguments    

OPTIONS
    -f (--foo2)*                Foo2 arguments    
    -g (--foo3)                 Foo3 arguments (default: a sub value) 

GLOBAL OPTIONS
    -t (--test)                 Test mode (default: False)                    
    -q (--quiet)                Do not output any message (default: False)
    --verbose                   Increase verbosity (default: False)    

DESCRIPTION
 Run foo command
"""  # noqa

_PARAMS_WITH_DEFAULTS = [
    ("Simple CLI cmd", get_simple_cli, ["foo", "-h"], _SIMPLE_CLI_COMMAND_RICH_DEFAULT),
    (
        "Simple CLI sub-cmd help",
        get_cmd_group_cli_with_global_opt,
        ["sub-cmd", "-h"],
        _SIMPLE_CLI_SUB_CMD_HELP_DEFAULT,
    ),
    (
        "Simple CLI sub-cmd cmd",
        get_cmd_group_cli_with_global_opt,
        ["sub-cmd", "foo", "-h"],
        _SIMPLE_CLI_SUB_CMD_CMD_DEFAULT,
    ),
]


@pytest.mark.parametrize(
    "name, cli_fn, args, expected",
    _PARAMS_WITH_DEFAULTS,
    ids=[x[0] for x in _PARAMS_WITH_DEFAULTS],
)
def test_rich_formatting_default(name, cli_fn, args, expected, capsys):
    from piou.formatter import RichFormatter

    cli = cli_fn(RichFormatter(show_default=True))
    cli.run_with_args(*args)
    output = capsys.readouterr().out
    _compare_str(output.strip(), expected.strip())


class TestClosestMatch:
    """Tests for the closest match suggestion feature."""

    @pytest.mark.parametrize(
        "commands, input_cmd, expected_suggestion, should_suggest",
        [
            pytest.param(
                ["deploy", "status"],
                "depoly",
                "deploy",
                True,
                id="typo-suggests-deploy",
            ),
            pytest.param(
                ["deploy"],
                "xyz",
                None,
                False,
                id="no-match-no-suggestion",
            ),
            pytest.param(
                ["start", "stop", "status"],
                "stat",
                None,  # Will match one of them
                True,
                id="multiple-similar-commands",
            ),
            pytest.param(
                ["install", "uninstall"],
                "instal",
                "install",
                True,
                id="missing-letter",
            ),
            pytest.param(
                ["build", "rebuild"],
                "buld",
                "build",
                True,
                id="missing-letter-short",
            ),
        ],
    )
    def test_close_match_cli(self, commands, input_cmd, expected_suggestion, should_suggest, capsys, sys_exit_counter):
        """Test close match suggestions with various typos."""
        from piou import Cli
        from piou.formatter import RichFormatter

        cli = Cli(formatter=RichFormatter())

        for cmd in commands:
            cli.add_command(cmd, lambda: None)

        cli.run_with_args(input_cmd)

        output = capsys.readouterr().out
        if should_suggest:
            assert "Did you mean" in output
            if expected_suggestion:
                assert f"Did you mean '{expected_suggestion}'?" in output
        else:
            assert "Did you mean" not in output
            assert f"Unknown command '{input_cmd}'" in output
        assert sys_exit_counter() == 1

    @pytest.mark.parametrize(
        "available, input_cmd, expected_in_output, not_expected_in_output",
        [
            pytest.param(
                ["deploy", "status", "start"],
                "depoly",
                ["Did you mean 'deploy'?"],
                [],
                id="base-formatter-suggests",
            ),
            pytest.param(
                ["deploy", "status"],
                None,
                ["Unknown command"],
                ["Did you mean"],
                id="base-formatter-no-input",
            ),
        ],
    )
    def test_close_match_base_formatter(self, available, input_cmd, expected_in_output, not_expected_in_output, capsys):
        """Test close match with base formatter."""
        from piou.formatter.base import Formatter
        from piou.command import CommandGroup

        class SimpleFormatter(Formatter):
            def print_cli_help(self, group: CommandGroup) -> None:
                pass

            def print_cmd_group_help(self, group: CommandGroup, parent_args) -> None:
                pass

            def print_cmd_help(self, command, options, parent_args=None) -> None:
                pass

        formatter = SimpleFormatter()
        formatter.print_invalid_command(available, input_cmd)

        output = capsys.readouterr().out
        for expected in expected_in_output:
            assert expected in output
        for not_expected in not_expected_in_output:
            assert not_expected not in output

    @pytest.mark.parametrize(
        "valid_commands, input_command, expected_valid, expected_input",
        [
            pytest.param(
                ["foo", "bar"],
                "baz",
                ["bar", "foo"],
                "baz",
                id="stores-input-and-sorts",
            ),
            pytest.param(
                ["z", "a", "m"],
                "x",
                ["a", "m", "z"],
                "x",
                id="sorts-alphabetically",
            ),
        ],
    )
    def test_exception_stores_input_command(self, valid_commands, input_command, expected_valid, expected_input):
        """Test that CommandNotFoundError stores the input command correctly."""
        from piou.exceptions import CommandNotFoundError

        error = CommandNotFoundError(valid_commands, input_command=input_command)
        assert error.input_command == expected_input
        assert error.valid_commands == expected_valid

    def test_subcommand_close_match(self, capsys, sys_exit_counter):
        """Test close match works within subcommand groups."""
        from piou import Cli
        from piou.formatter import RichFormatter

        cli = Cli(formatter=RichFormatter())

        sub = cli.add_sub_parser("db", help="Database commands")

        @sub.command(cmd="migrate")
        def migrate_cmd():
            pass

        @sub.command(cmd="rollback")
        def rollback_cmd():
            pass

        cli.run_with_args("db", "migrat")  # Typo in subcommand

        output = capsys.readouterr().out
        assert "Did you mean 'migrate'?" in output
        assert sys_exit_counter() == 1


@pytest.mark.parametrize("formatter_cls", ["Formatter", "RichFormatter"])
class TestFormatterOutput:
    """Tests for both Formatter and RichFormatter output."""

    def test_cli_help(self, formatter_cls, capsys):
        from piou import Cli, Option
        from piou.formatter import Formatter, RichFormatter

        formatter = Formatter() if formatter_cls == "Formatter" else RichFormatter()
        cli = Cli(description="A CLI tool", formatter=formatter)

        @cli.command(cmd="foo", help="Run foo command")
        def foo_main(
            foo1: int = Option(..., help="Foo argument"),
        ):
            pass

        cli.run_with_args("-h")
        output = capsys.readouterr().out

        assert "USAGE" in output
        assert "AVAILABLE COMMANDS" in output
        assert "foo" in output
        assert "Run foo command" in output

    def test_command_help(self, formatter_cls, capsys):
        from piou import Cli, Option
        from piou.formatter import Formatter, RichFormatter

        formatter = Formatter() if formatter_cls == "Formatter" else RichFormatter()
        cli = Cli(formatter=formatter)

        @cli.command(cmd="foo", help="Run foo command")
        def foo_main(
            foo1: int = Option(..., help="Foo argument"),
            foo2: str = Option("default", "-f", "--foo2", help="Foo2 argument"),
        ):
            pass

        cli.run_with_args("foo", "-h")
        output = capsys.readouterr().out

        assert "USAGE" in output
        assert "ARGUMENTS" in output
        assert "<foo1>" in output
        assert "OPTIONS" in output
        assert "--foo2" in output

    def test_error_output(self, formatter_cls, capsys, sys_exit_counter):
        from piou import Cli
        from piou.formatter import Formatter, RichFormatter

        formatter = Formatter() if formatter_cls == "Formatter" else RichFormatter()
        cli = Cli(formatter=formatter)

        @cli.command(cmd="foo")
        def foo_main():
            pass

        cli.run_with_args("bar")
        output = capsys.readouterr().out

        assert "Unknown command" in output
        assert "bar" in output
        assert sys_exit_counter() == 1

    def test_close_match_suggestion(self, formatter_cls, capsys, sys_exit_counter):
        from piou import Cli
        from piou.formatter import Formatter, RichFormatter

        formatter = Formatter() if formatter_cls == "Formatter" else RichFormatter()
        cli = Cli(formatter=formatter)

        @cli.command(cmd="migrate")
        def migrate_cmd():
            pass

        cli.run_with_args("migrat")
        output = capsys.readouterr().out

        assert "Did you mean 'migrate'?" in output
        assert sys_exit_counter() == 1


class TestFormatterEnvVar:
    """Tests for PIOU_FORMATTER environment variable."""

    @pytest.mark.parametrize(
        "env_value,expected_cls_name",
        [
            ("raw", "Formatter"),
            ("rich", "RichFormatter"),
        ],
    )
    def test_env_var_formatter(self, monkeypatch, env_value, expected_cls_name):
        monkeypatch.setenv("PIOU_FORMATTER", env_value)

        from piou.formatter import get_formatter, Formatter, RichFormatter

        formatter = get_formatter()
        expected_cls = Formatter if expected_cls_name == "Formatter" else RichFormatter
        assert type(formatter) is expected_cls

    @pytest.mark.parametrize(
        "formatter_type,expected_cls_name",
        [
            ("raw", "Formatter"),
            ("rich", "RichFormatter"),
        ],
    )
    def test_get_formatter(self, formatter_type, expected_cls_name):
        from piou.formatter import get_formatter, Formatter, RichFormatter

        formatter = get_formatter(formatter_type)
        expected_cls = Formatter if expected_cls_name == "Formatter" else RichFormatter
        assert type(formatter) is expected_cls

    @pytest.mark.parametrize(
        "env_value,expected_cls_name",
        [
            ("raw", "Formatter"),
            ("rich", "RichFormatter"),
        ],
    )
    def test_cli_uses_env_var(self, monkeypatch, env_value, expected_cls_name):
        monkeypatch.setenv("PIOU_FORMATTER", env_value)

        from piou import Cli
        from piou.formatter import Formatter, RichFormatter

        cli = Cli()
        expected_cls = Formatter if expected_cls_name == "Formatter" else RichFormatter
        assert type(cli.formatter) is expected_cls
