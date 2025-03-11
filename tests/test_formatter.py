from typing import Literal

import pytest

from piou.utils import Password


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
    "default, data_type,show_default,expected",
    [
        pytest.param("hello", Password, True, "(default: ******)", id="Password"),
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
