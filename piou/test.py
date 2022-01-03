from typing import Literal

from piou import Cli, Option
from piou.formatter import RichFormatter

cli = Cli(description='A CLI tool',
          formatter=RichFormatter(show_default=True))

cli.add_option('-q', '--quiet', help='Do not output any message')
cli.add_option('--verbose', help='Increase verbosity')


def processor(quiet: bool, verbose: bool):
    print(f'Processing {quiet=} and {verbose=}')


cli.set_options_processor(processor)


@cli.command(cmd='foo',
             help='Run foo command')
def foo_main(
        quiet: bool,
        verbose: bool,
        foo1: int = Option(..., help='Foo argument'),
        foo2: str = Option(..., '-f', '--foo2', help='Foo2 argument'),
        foo3: str = Option(None, '-g', '--foo3', help='Foo3 argument'),
        foo4: Literal['foo', 'bar'] = Option(None, '--foo4', help='Foo4 argument'),
        foo5: list[int] = Option(None, '--foo5', help='Foo5 arguments'),
):
    for name, value in [('quiet', quiet),
                        ('verbose', verbose),
                        ('foo1', foo1),
                        ('foo2', foo2),
                        ('foo3', foo3),
                        ('foo4', foo4),
                        ('foo5', foo5)
                        ]:
        print(f'{name} = {value} ({type(value)})')


@cli.command(cmd='bar', help='Run bar command')
def bar_main(**kwargs):
    pass


sub_cmd = cli.add_sub_parser(cmd='sub', description='A sub command')
sub_cmd.add_option('--test', help='Test mode')


@sub_cmd.command(cmd='bar', help='Run bar command')
def sub_bar_main(**kwargs):
    print('Running sub-bar command')


@sub_cmd.command(cmd='foo', help='Run foo command')
def sub_foo_main(
        test: bool,
        quiet: bool,
        verbose: bool,
        foo1: int = Option(..., help='Foo argument'),
        foo2: str = Option(..., '-f', '--foo2', help='Foo2 argument'),
        foo3: str = Option(None, '--foo3', help='Foo3 argument'),
):
    for name, value in [('test', test),
                        ('quiet', quiet),
                        ('verbose', verbose),
                        ('foo1', foo1),
                        ('foo2', foo2),
                        ('foo3', foo3)]:
        print(f'{name} = {value} ({type(value)})')


if __name__ == '__main__':
    cli.run()
