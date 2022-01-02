import pytest


def get_simple_cli(formatter):
    from piou import Cli, Option

    cli = Cli(description='A CLI tool', formatter=formatter)

    @cli.command(cmd='foo',
                 help='Run foo command')
    def foo_main(
            foo1: int = Option(..., help='Foo arguments'),
            foo2: str = Option(..., '-f', '--foo2', help='Foo2 arguments'),
            foo3: str = Option('a-value', '-g', '--foo3', help='Foo3 arguments'),
    ):
        pass

    return cli


def get_simple_cli_with_global_opt(formatter):
    from piou import Cli, Option

    cli = Cli(description='A CLI tool', formatter=formatter)
    cli.add_option('-q', '--quiet', help='Do not output any message')
    cli.add_option('--verbose', help='Increase verbosity')

    @cli.command(cmd='foo',
                 help='Run foo command')
    def foo_main(
            foo1: int = Option(..., help='Foo arguments'),
            foo2: str = Option(..., '-f', '--foo2', help='Foo2 arguments'),
            foo3: str = Option(None, '-g', '--foo3', help='Foo3 arguments'),
    ):
        pass

    return cli


def get_cmd_group_cli_with_global_opt(formatter):
    from piou import Cli, Option

    cli = Cli(description='A CLI tool', formatter=formatter)
    cli.add_option('-q', '--quiet', help='Do not output any message')
    cli.add_option('--verbose', help='Increase verbosity')

    sub_cmd = cli.add_sub_parser('sub-cmd', description='A sub command')

    sub_cmd.add_option('-t', '--test', help='Test mode')

    @sub_cmd.command(cmd='foo',
                     help='Run foo command')
    def foo_main(
            foo1: int = Option(..., help='Foo arguments'),
            foo2: str = Option(..., '-f', '--foo2', help='Foo2 arguments'),
            foo3: str = Option('a sub value', '-g', '--foo3', help='Foo3 arguments'),
    ):
        pass

    @sub_cmd.command(cmd='bar',
                     help='Run bar command')
    def bar_main(**kwargs):
        pass

    return cli


def get_cli_full(formatter):
    from piou import Cli, Option

    cli = Cli(description='A CLI tool', formatter=formatter)

    cli.add_option('-q', '--quiet', help='Do not output any message')
    cli.add_option('--verbose', help='Increase verbosity')

    @cli.command(cmd='foo',
                 help='Run foo command')
    def foo_main(
            quiet: bool,
            verbose: bool,
            foo1: int = Option(..., help='Foo arguments'),
            foo2: str = Option(..., '-f', '--foo2', help='Foo2 arguments'),
            foo3: str = Option(None, '-g', '--foo3', help='Foo3 arguments'),
    ):
        pass

    @cli.command(cmd='bar', help='Run bar command')
    def bar_main():
        pass

    baz_cmd = cli.add_sub_parser(cmd='baz', description='A sub command')
    baz_cmd.add_option('--test', help='Test mode')

    @baz_cmd.command(cmd='bar', help='Run baz command')
    def baz_bar_main(
            **kwargs
    ):
        pass

    @baz_cmd.command(cmd='toto', help='Run toto command')
    def toto_main(
            test: bool,
            quiet: bool,
            verbose: bool,
            foo1: int = Option(..., help='Foo arguments'),
            foo2: str = Option(..., '-f', '--foo2', help='Foo2 arguments'),
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
 pytest foo <foo1> [-f] [-g] 

ARGUMENTS
    <foo1>                      Foo arguments    

OPTIONS
    -f (--foo2)                 Foo2 arguments    
    -g (--foo3)                 Foo3 arguments    

DESCRIPTION
 Run foo command
"""

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
"""

_SIMPLE_CLI_WITH_OPTS_CMD_OUTPUT_RICH = """
USAGE 
 pytest [-q] [--verbose] foo <foo1> [-f] [-g] 

ARGUMENTS
    <foo1>                      Foo arguments    

OPTIONS
    -f (--foo2)                 Foo2 arguments    
    -g (--foo3)                 Foo3 arguments    

GLOBAL OPTIONS
    -q (--quiet)                Do not output any message    
    --verbose                   Increase verbosity           

DESCRIPTION
 Run foo command
"""

_SIMPLE_CLI_SUB_CMD_RICH = """
USAGE 
 pytest [-q] [--verbose] <command> 

GLOBAL OPTIONS
    -q (--quiet)                Do not output any message    
    --verbose                   Increase verbosity           

AVAILABLE COMMANDS
     sub-cmd                    A sub command    

DESCRIPTION
 A CLI tool
"""

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
"""

_SIMPLE_CLI_SUB_CMD_CMD_RICH = """
USAGE 
 pytest sub-cmd [-t] foo <foo1> [-f] [-g] 

ARGUMENTS
    <foo1>                      Foo arguments    

OPTIONS
    -f (--foo2)                 Foo2 arguments    
    -g (--foo3)                 Foo3 arguments    

GLOBAL OPTIONS
    -t (--test)                 Test mode                    
    -q (--quiet)                Do not output any message    
    --verbose                   Increase verbosity           

DESCRIPTION
 Run foo command
"""

_PARAMS = [
    ('Simple CLI', get_simple_cli, [], _SIMPLE_CLI_OUTPUT_RICH),
    ('Simple CLI cmd', get_simple_cli, ['foo', '-h'], _SIMPLE_CLI_COMMAND_RICH),
    ('Simple CLI with opts', get_simple_cli_with_global_opt, [], _SIMPLE_CLI_WITH_OPTS_OUTPUT_RICH),
    ('Simple CLI with opts cmd', get_simple_cli_with_global_opt, ['foo', '-h'],
     _SIMPLE_CLI_WITH_OPTS_CMD_OUTPUT_RICH),
    ('Simple CLI sub cmd', get_cmd_group_cli_with_global_opt, [], _SIMPLE_CLI_SUB_CMD_RICH),
    ('Simple CLI sub cmd help', get_cmd_group_cli_with_global_opt, ['sub-cmd', '-h'], _SIMPLE_CLI_SUB_CMD_HELP_RICH),
    ('Simple CLI sub cmd cmd cmd', get_cmd_group_cli_with_global_opt, ['sub-cmd', 'foo', '-h'],
     _SIMPLE_CLI_SUB_CMD_CMD_RICH),
    # Errors
    ('Simple CLI keyword error', get_simple_cli, ['foo', '-vvv'],
     "Could not find keyword parameter '-vvv' for command 'foo'"),
    ('Simple CLI keyword error', get_simple_cli, ['foo'],
     "Expected 1 positional arguments but got 0 for command foo"),
]


def _compare_str(output, expected):
    output_lines, expected_lines = output.split('\n'), expected.split('\n')
    assert len(output_lines) == len(expected_lines)
    for output_line, expected_line in zip(output_lines, expected_lines):
        assert output_line.strip() == expected_line.strip()


@pytest.mark.parametrize('name, cli_fn, args, expected', _PARAMS, ids=[x[0] for x in _PARAMS])
def test_rich_formatting(name, cli_fn, args, expected, capsys):
    from piou.formatter import RichFormatter
    cli = cli_fn(RichFormatter(show_default=False))
    cli.run_with_args(*args)
    output = capsys.readouterr().out
    _compare_str(output.strip(), expected.strip())


_SIMPLE_CLI_COMMAND_RICH_DEFAULT = """
USAGE 
 pytest foo <foo1> [-f] [-g] 

ARGUMENTS
    <foo1>                      Foo arguments    

OPTIONS
    -f (--foo2)                 Foo2 arguments    
    -g (--foo3)                 Foo3 arguments (default: a-value)    

DESCRIPTION
 Run foo command
"""

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
"""

_SIMPLE_CLI_SUB_CMD_CMD_DEFAULT = """
USAGE 
 pytest sub-cmd [-t] foo <foo1> [-f] [-g] 

ARGUMENTS
    <foo1>                      Foo arguments    

OPTIONS
    -f (--foo2)                 Foo2 arguments    
    -g (--foo3)                 Foo3 arguments (default: a sub value) 

GLOBAL OPTIONS
    -t (--test)                 Test mode (default: False)                    
    -q (--quiet)                Do not output any message (default: False)
    --verbose                   Increase verbosity (default: False)    

DESCRIPTION
 Run foo command
"""

_PARAMS_WITH_DEFAULTS = [
    ('Simple CLI cmd', get_simple_cli, ['foo', '-h'], _SIMPLE_CLI_COMMAND_RICH_DEFAULT),
    ('Simple CLI sub-cmd help', get_cmd_group_cli_with_global_opt, ['sub-cmd', '-h'], _SIMPLE_CLI_SUB_CMD_HELP_DEFAULT),
    ('Simple CLI sub-cmd cmd', get_cmd_group_cli_with_global_opt, ['sub-cmd', 'foo', '-h'],
     _SIMPLE_CLI_SUB_CMD_CMD_DEFAULT)
]


@pytest.mark.parametrize('name, cli_fn, args, expected', _PARAMS_WITH_DEFAULTS,
                         ids=[x[0] for x in _PARAMS_WITH_DEFAULTS])
def test_rich_formatting_default(name, cli_fn, args, expected, capsys):
    from piou.formatter import RichFormatter
    cli = cli_fn(RichFormatter(show_default=True))
    cli.run_with_args(*args)
    output = capsys.readouterr().out
    _compare_str(output.strip(), expected.strip())
