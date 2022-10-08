from typing import Literal, Union
from pathlib import Path

from piou import Cli, Option
from piou.formatter import RichFormatter

cli = Cli(description="A Cli tool",
          formatter=RichFormatter(show_default=True))


@cli.processor()
def processor(quiet: bool = Option(False, '-q', '--quiet', help='Do not output any message'),
              verbose: bool = Option(False, '--verbose', help='Increase verbosity')
              ):
    print(f'Processing {quiet=} and {verbose=}')


LongLiteral = Literal['foo1', 'foo2', 'foo3', 'foo4']
UnionLiteral = Union[Literal['foo1'], Literal['foo2']]


@cli.command(cmd='foo',
             help='Run foo command')
def foo_main(
        foo1: int = Option(..., help='Foo argument'),
        foo2: str = Option(..., '-f', '--foo2', help='Foo2 argument'),
        foo3: str = Option(None, '-g', '--foo3', help='Foo3 argument'),
        foo4: Literal['foo', 'bar'] = Option(None, '--foo4', help='Foo4 argument',
                                             case_sensitive=False),
        foo5: list[int] = Option(None, '--foo5', help='Foo5 arguments'),
        foo6: LongLiteral = Option('foo1', '--foo6', help='Foo6 argument'),
        foo7: LongLiteral = Option(None, '--foo7', help='Foo7 argument'),
        foo8: UnionLiteral = Option(None, '--foo8', help='Foo8 argument'),
        foo9: str = Option(None, '--foo9', help='Foo9 argument',
                           choices=[f'item{i}' for i in range(4)]),
):
    """
    A test command
    """
    print('Running foo')
    for name, value in [('foo1', foo1),
                        ('foo2', foo2),
                        ('foo3', foo3),
                        ('foo4', foo4),
                        ('foo5', foo5),
                        ('foo6', foo6),
                        ('foo7', foo7),
                        ('foo8', foo8),
                        ('foo9', foo9)
                        ]:
        print(f'{name} = {value} ({type(value)})')


@cli.command(cmd='bar', help='Run bar command')
def bar_main(**kwargs):
    pass


sub_cmd = cli.add_sub_parser(cmd='sub', help='A sub command')
sub_cmd.add_option('--test', help='Test mode')


@sub_cmd.command(cmd='bar', help='Run bar command')
def sub_bar_main(
        foo: Path = Option(Path('/tmp'), '--foo', help='Foo argument'),
        **kwargs):
    print('Running sub-bar command')
    print(f'foo ({type(foo)})')


@sub_cmd.command(cmd='foo', help='Run foo command')
def sub_foo_main(
        test: bool,
        foo1: int = Option(..., help='Foo argument'),
        foo2: str = Option(..., '-f', '--foo2', help='Foo2 argument'),
        foo3: str = Option(None, '--foo3', help='Foo3 argument'),
):
    for name, value in [('test', test),
                        ('foo1', foo1),
                        ('foo2', foo2),
                        ('foo3', foo3)]:
        print(f'{name} = {value} ({type(value)})')


if __name__ == '__main__':
    cli.run()
