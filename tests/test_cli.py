import datetime as dt
from pathlib import Path

import pytest


@pytest.mark.parametrize('arg, expected', [
    ('-q', 'q'),
    ('--quiet', 'quiet'),
    ('--quiet-v2', 'quiet_v2')
])
def test_keyword_arg_to_name(arg, expected):
    from piou.utils import keyword_arg_to_name
    assert keyword_arg_to_name(arg) == expected


@pytest.mark.parametrize('cmd, is_required, is_positional', [
    ([...], True, True),
    ([None, '--foo'], False, True)
])
def test_command_option(cmd, is_required, is_positional):
    from piou.utils import CommandOption
    cmd = CommandOption(*cmd)
    assert cmd.is_required == is_required
    assert cmd.is_positional_arg == is_positional


@pytest.mark.parametrize('data_type, value, expected', [
    (str, '123', '123'),
    (int, '123', 123),
    (float, '123', 123),
    (float, '0.123', 0.123),
    # (bytes, 'foo'.encode('utf-8'), b'foo'),
    (Path, str(Path(__file__).parent / 'conftest.py'), Path(__file__).parent / 'conftest.py'),
    (list, '1 2 3', ['1', '2', '3']),
    (list[str], '1 2 3', ['1', '2', '3']),
    (list[int], '1 2 3', [1, 2, 3]),
    (dict, '{"a": 1, "b": "foo", "c": {"foo": "bar"}}', {"a": 1, "b": "foo", "c": {"foo": "bar"}}),
    (dt.date, '2019-01-01', dt.date(2019, 1, 1)),
    (dt.datetime, '2019-01-01T01:01:01', dt.datetime(2019, 1, 1, 1, 1, 1))
])
def test_validate_type(data_type, value, expected):
    from piou.utils import validate_type
    assert validate_type(data_type, value) == expected


@pytest.mark.parametrize('input_str, expected_pos_args, expected_key_args', [
    ('--foo buz', [], {'--foo': 'buz'}),
    ('--foo buz -b baz', [], {'--foo': 'buz', '-b': 'baz'}),
    ('--foo', [], {'--foo': True}),
    ('foo buz -b baz', ['foo', 'buz'], {'-b': 'baz'}),
    ('foo', ['foo'], {})
])
def test_get_cmd_args(input_str, expected_pos_args, expected_key_args):
    from piou.utils import get_cmd_args

    pos_args, key_args = get_cmd_args(input_str)
    assert pos_args == expected_pos_args
    assert key_args == expected_key_args


@pytest.mark.parametrize('input_str, args, expected', [
    (
            'baz --foo buz',
            [
                {'default': ..., 'name': 'baz'},
                {'default': ..., 'keyword_args': ['--foo'], 'name': 'foo'}
            ],
            {'baz': 'baz', 'foo': 'buz'}
    ),
    (
            '--foo buz',
            [
                {'default': ..., 'keyword_args': ['--foo', '-f'], 'name': 'foo'}
            ],
            {'foo': 'buz'}
    )

])
def test_validate_arguments(input_str, args, expected):
    from piou.utils import convert_args_to_dict, Option
    cmd_args = []
    for _arg in args:
        arg = Option(_arg['default'], *_arg.get('keyword_args', []))
        arg.name = _arg['name']
        cmd_args.append(arg)
    output = convert_args_to_dict(input_str.split(' '),
                                  options=cmd_args)
    assert output == expected


def test_command():
    from piou.command import Command
    called = False

    def test_fn(foo, *, bar=None):
        nonlocal called

        assert foo == 1
        assert bar == 'baz'

        called = True

    cmd = Command(name='', help=None, fn=test_fn)
    cmd.run(1, bar='baz')
    assert called


def test_command_raises_error_on_duplicate_args():
    from piou.command import Command
    from piou.utils import CommandOption

    with pytest.raises(ValueError,
                       match='Duplicate keyword args found "--foo"'):
        Command(name='', help=None, fn=lambda x: x,
                options=[
                    CommandOption(None, keyword_args=('-f', '--foo')),
                    CommandOption(None, keyword_args=('--foo',))
                ])
    with pytest.raises(ValueError,
                       match='Duplicate keyword args found "--foo"'):
        Command(name='', help=None, fn=lambda x: x,
                options=[
                    CommandOption(None, keyword_args=('-f', '--foo', '--foo'))
                ])


def test_cli_help(capsys):
    from piou import Cli, Option
    from piou.formatter import RichFormatter

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

    cli.run_with_args('-h')
    assert capsys.readouterr().out.strip() == """
USAGE
 pytest [-q] [--verbose] <command>  

GLOBAL OPTIONS
                                               
  -q (--quiet)      Do not output any message  
  --verbose         Increase verbosity         
                                               
AVAILABLE COMMANDS
                                     
  bar               Run bar command  
  baz               A sub command    
  foo               Run foo command  
                                     
DESCRIPTION
 A CLI tool
""".strip()


def test_run_command(capsys):
    from piou import Cli, Option

    called = False

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
        nonlocal called
        called = True
        assert foo1 == 1
        assert foo2 == 'toto'
        assert foo3 is None
        assert quiet is True
        assert verbose is None

    cli.run_with_args('foo')
    assert not called
    assert capsys.readouterr().out.strip() == 'Expected 1 positional arguments but got 0'

    cli.run_with_args('-q', 'foo', '1', '-f', 'toto')

    cli.run_with_args('-h')
    assert capsys.readouterr().out.strip() == """
USAGE
 pytest [-q] [--verbose] <command>  

GLOBAL OPTIONS
                                               
  -q (--quiet)      Do not output any message  
  --verbose         Increase verbosity         
                                               
AVAILABLE COMMANDS
                                     
  foo               Run foo command  
                                     
DESCRIPTION
 A CLI tool
""".strip()
