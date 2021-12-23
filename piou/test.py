from piou import Cli, Option

cli = Cli(description='A CLI tool')

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
def bar_main(**kwargs):
    pass


sub_cmd = cli.add_sub_parser(cmd='sub', description='A sub command')
sub_cmd.add_option('--test', help='Test mode')


@sub_cmd.command(cmd='bar', help='Run baz command')
def baz_bar_main(
        **kwargs
):
    pass


@sub_cmd.command(cmd='toto', help='Run toto command')
def toto_main(
        test: bool,
        quiet: bool,
        verbose: bool,
        foo1: int = Option(..., help='Foo arguments'),
        foo2: str = Option(..., '-f', '--foo2', help='Foo2 arguments'),
):
    pass


if __name__ == '__main__':
    cli.run()
