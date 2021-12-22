import pytest


def get_simple_cli():
    from piou import Cli, Option

    cli = Cli(description='A CLI tool')

    @cli.command(cmd='foo',
                 help='Run foo command')
    def foo_main(
            foo1: int = Option(..., help='Foo arguments'),
            foo2: str = Option(..., '-f', '--foo2', help='Foo2 arguments'),
            foo3: str = Option(None, '-g', '--foo3', help='Foo3 arguments'),
    ):
        pass

    return cli


def get_simple_cli_with_global_opt():
    from piou import Cli, Option

    cli = Cli(description='A CLI tool')
    cli.add_option(None, '-q', '--quiet', help='Do not output any message')
    cli.add_option(None, '--verbose', help='Increase verbosity')

    @cli.command(cmd='foo',
                 help='Run foo command')
    def foo_main(
            foo1: int = Option(..., help='Foo arguments'),
            foo2: str = Option(..., '-f', '--foo2', help='Foo2 arguments'),
            foo3: str = Option(None, '-g', '--foo3', help='Foo3 arguments'),
    ):
        pass

    return cli


def get_cmd_group_cli_with_global_opt():
    from piou import Cli, Option

    cli = Cli(description='A CLI tool')
    cli.add_option(None, '-q', '--quiet', help='Do not output any message')
    cli.add_option(None, '--verbose', help='Increase verbosity')

    sub_cmd = cli.add_sub_parser('sub-cmd', description='A sub command')

    sub_cmd.add_option(None, '-t', '--test', help='Test mode')

    @sub_cmd.command(cmd='foo',
                     help='Run foo command')
    def foo_main(
            foo1: int = Option(..., help='Foo arguments'),
            foo2: str = Option(..., '-f', '--foo2', help='Foo2 arguments'),
            foo3: str = Option(None, '-g', '--foo3', help='Foo3 arguments'),
    ):
        pass

    @sub_cmd.command(cmd='bar',
                     help='Run bar command')
    def bar_main(**kwargs):
        pass

    return cli


def get_cli_full():
    from piou import Cli, Option

    cli = Cli(description='A CLI tool')

    cli.add_option(None, '-q', '--quiet', help='Do not output any message')
    cli.add_option(None, '--verbose', help='Increase verbosity')

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
    baz_cmd.add_option(None, '--test', help='Test mode')

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
    -f (--foo2)                 Foo2 arguments    
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

_RICH_PARAMS = [
    ('Simple CLI', get_simple_cli, [], _SIMPLE_CLI_OUTPUT_RICH),
    ('Simple CLI cmd', get_simple_cli, ['foo', '-h'], _SIMPLE_CLI_COMMAND_RICH),
    ('Simple CLI with opts', get_simple_cli_with_global_opt, [], _SIMPLE_CLI_WITH_OPTS_OUTPUT_RICH),
    ('Simple CLI with opts cmd', get_simple_cli_with_global_opt, ['foo', '-h'], _SIMPLE_CLI_WITH_OPTS_CMD_OUTPUT_RICH),
    ('Simple CLI sub cmd', get_cmd_group_cli_with_global_opt, [], _SIMPLE_CLI_SUB_CMD_RICH),
    ('Simple CLI sub cmd help', get_cmd_group_cli_with_global_opt, ['sub-cmd', '-h'], _SIMPLE_CLI_SUB_CMD_HELP_RICH),
    ('Simple CLI sub cmd cmd cmd', get_cmd_group_cli_with_global_opt, ['sub-cmd', 'foo', '-h'],
     _SIMPLE_CLI_SUB_CMD_CMD_RICH)
]


@pytest.mark.parametrize('name, cli_fn, args, expected', _RICH_PARAMS, ids=[x[0] for x in _RICH_PARAMS])
def test_rich_formatting(name, cli_fn, args, expected, capsys):
    cli = cli_fn()
    cli.run_with_args(*args)
    output = capsys.readouterr().out.strip()
    assert output == expected.strip(), print(output)
