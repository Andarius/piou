import datetime as dt
import re
from pathlib import Path
from typing import Literal
from uuid import UUID
from enum import Enum

import pytest


class MyEnum(Enum):
    foo = 'bar'
    baz = 'foo'


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
    (dt.datetime, '2019-01-01T01:01:01', dt.datetime(2019, 1, 1, 1, 1, 1)),
    (Literal['foo', 'bar'], 'bar', 'bar'),
    (UUID, '00000000-0000-0000-0000-000000000000', UUID('00000000-0000-0000-0000-000000000000')),
    (MyEnum, 'foo', 'bar')
])
def test_convert_to_type(data_type, value, expected):
    from piou.utils import convert_to_type
    assert convert_to_type(data_type, value) == expected


@pytest.mark.parametrize('data_type, value, expected, expected_str', [
    (Path, 'a-file.py', FileNotFoundError, f'File not found: "a-file.py"'),
    (Literal['foo', 'bar'], 'baz', ValueError, '"baz" is not a valid value for Literal[foo, bar]')
])
def test_convert_to_type_invalid_data(data_type, value, expected,
                                    expected_str):
    from piou.utils import convert_to_type
    with pytest.raises(expected, match=re.escape(expected_str)):
        convert_to_type(data_type, value)


@pytest.mark.parametrize('input_str, types, expected_pos_args, expected_key_args', [
    ('--foo buz', {'foo': str}, [], {'--foo': 'buz'}),
    ('--foo buz -b baz', {'foo': str, 'b': str}, [], {'--foo': 'buz', '-b': 'baz'}),
    ('--foo -b', {'foo': bool, 'b': True}, [], {'--foo': True, '-b': True}),
    ('foo buz -b baz', {'b': str}, ['foo', 'buz'], {'-b': 'baz'}),
    ('foo', {}, ['foo'], {}),
    ('--foo 1 2 3 --bar', {'foo': list[int], 'bar': str}, [], {'--foo': '1 2 3', '--bar': True}),
    (
            'foo bar --foo1 1 2 3 --foo2 --foo3 test',
            {'foo1': list[int], 'foo2': bool, 'foo3': str},
            ['foo', 'bar'],
            {'--foo1': '1 2 3', '--foo2': True, '--foo3': 'test'}
    )
])
def test_get_cmd_args(input_str, types, expected_pos_args, expected_key_args):
    from piou.utils import get_cmd_args

    pos_args, key_args = get_cmd_args(input_str, types)
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
    from piou.utils import Option, convert_args_to_dict
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


def test_command_async():
    from piou.command import Command
    called = False

    async def test_fn(foo, *, bar=None):
        nonlocal called

        assert foo == 1
        assert bar == 'baz'

        called = True

    cmd = Command(name='', fn=test_fn, help=None)
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


def test_command_wrapper_help():
    from piou import Cli

    cli = Cli(description='A CLI tool')

    @cli.command(cmd='foo')
    def foo_main():
        """
        A doc about the function
        """
        pass

    @cli.command(cmd='foo2', help='A first doc')
    def foo_2_main():
        """
        A doc about the function
        """
        pass

    @cli.command(cmd='foo3')
    def foo_3_main():
        pass

    assert cli.commands['foo'].help == 'A doc about the function'
    assert cli.commands['foo2'].help == 'A first doc'
    assert cli.commands['foo3'].help is None


def test_run_command():
    from piou import Cli, Option
    from piou.exceptions import (
        PosParamsCountError, KeywordParamNotFoundError,
        KeywordParamMissingError
    )

    called, processor_called = False, False

    cli = Cli(description='A CLI tool')

    cli.add_option('-q', '--quiet', help='Do not output any message')
    cli.add_option('--verbose', help='Increase verbosity')

    def processor(quiet: bool, verbose: bool):
        nonlocal processor_called
        processor_called = True
        assert quiet is True
        assert verbose is False

    cli.set_options_processor(processor)

    @cli.command(cmd='foo',
                 help='Run foo command')
    def foo_main(
            quiet: bool,
            verbose: bool,
            foo1: int = Option(..., help='Foo arguments'),
            foo2: str = Option(..., '-f', '--foo2', help='Foo2 arguments'),
            foo3: str = Option(None, '-g', '--foo3', help='Foo3 arguments'),
            foo4: list[int] = Option(None, '--foo4', help='Foo4 arguments'),
    ):
        nonlocal called
        called = True
        assert foo1 == 1
        assert foo2 == 'toto'
        assert foo3 is None
        assert quiet is True
        assert verbose is False
        assert foo4 == [1, 2, 3]

    with pytest.raises(PosParamsCountError,
                       match='Expected 1 positional values but got 0'):
        cli._group.run_with_args('foo')
    assert not called
    assert not processor_called

    with pytest.raises(KeywordParamNotFoundError,
                       match="Could not find parameter '-vvv'"):
        cli._group.run_with_args('foo', '1', '-vvv')

    assert not called
    assert not processor_called

    with pytest.raises(KeywordParamMissingError,
                       match="Missing value for required keyword parameter 'foo2'"):
        cli._group.run_with_args('-q', 'foo', '1', '--foo4', '1 2 3')
    assert not called
    assert not processor_called

    cli._group.run_with_args('-q', 'foo', '1', '-f', 'toto', '--foo4', '1 2 3')
    assert called
    assert processor_called


def test_run_group_command():
    called = False

    from piou import Cli, Option, CommandGroup

    cli = Cli(description='A CLI tool')

    cli.add_option('-q', '--quiet', help='Do not output any message')
    cli.add_option('--verbose', help='Increase verbosity')

    processor_called = False

    def processor(quiet: bool, verbose: bool):
        nonlocal processor_called
        processor_called = True

        assert quiet is True
        assert verbose is False

    cli.set_options_processor(processor)

    foo_sub_cmd = cli.add_sub_parser(cmd='foo', description='A sub command')
    foo_sub_cmd.add_option('--test', help='Test mode')

    sub_processor_called = False

    def sub_processor(test: bool):
        nonlocal sub_processor_called
        sub_processor_called = True
        assert test is True

    foo_sub_cmd.set_options_processor(sub_processor)

    @foo_sub_cmd.command(cmd='bar', help='Run baz command')
    def bar_main(**kwargs):
        pass

    @foo_sub_cmd.command(cmd='baz', help='Run toto command')
    def baz_main(
            test: bool = False,
            quiet: bool = False,
            verbose: bool = False,
            foo1: int = Option(..., help='Foo arguments'),
            foo2: str = Option(..., '-f', '--foo2', help='Foo2 arguments'),
            foo3: str = Option('a value', '--foo3', help='Foo3 arguments'),
    ):
        nonlocal called
        called = True
        assert test is True
        assert quiet is True
        assert verbose is False
        assert foo1 == 1
        assert foo2 == 'toto'
        assert foo3 == 'a value'

    cli._group.run_with_args('-q', 'foo', '--test', 'baz', '1', '-f', 'toto')
    assert called
    assert processor_called
    assert sub_processor_called

    group2 = CommandGroup(name='foo2')
    cli.add_command_group(group2)

    group2_called = False

    @group2.command('baz')
    def baz_2_main(
            quiet: bool = False,
            verbose: bool = False,
    ):
        nonlocal group2_called
        group2_called = True
        assert quiet is True
        assert verbose is False

    cli._group.run_with_args('-q', 'foo2', 'baz')
    assert group2_called
