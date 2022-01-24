import asyncio
import datetime as dt
import re
from enum import Enum
from pathlib import Path
from typing import Literal
from uuid import UUID

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


def testing_case_sensitivity():
    from piou.utils import convert_to_type
    _type = Literal['foo', 'bar']
    assert convert_to_type(_type, 'FOO', case_sensitive=False) == 'FOO'
    assert convert_to_type(_type, 'foo', case_sensitive=False) == 'foo'
    with pytest.raises(ValueError,
                       match=re.escape('"toto" is not a valid value for Literal[foo, bar]')):
        convert_to_type(_type, 'toto', case_sensitive=False)


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
    ),
    ('--foo /tmp', {'foo': Path}, [], {'--foo': '/tmp'})
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


def test_command_options():
    from piou.command import Command, CommandOption

    # Required Pos at the end
    opt1 = CommandOption(...)
    opt1.name = 'z'
    # Required Keyword
    opt2 = CommandOption(..., keyword_args=('-a',))
    opt2.name = 'a'
    # Optional Keyword
    opt3 = CommandOption(False, keyword_args=('-b',))
    opt3.name = 'b'
    opt4 = CommandOption(False, keyword_args=('-c',))
    opt4.name = 'c'
    opt5 = CommandOption(False, keyword_args=('-d',))
    opt5.name = 'd'

    def fn(*args, **kwargs): pass

    cmd = Command(name='', fn=fn, options=[opt4, opt5, opt3, opt2, opt1])
    assert [x.name for x in cmd.options_sorted] == ['z', 'a', 'b', 'c', 'd']


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
                    CommandOption(1, keyword_args=('-f', '--foo')),
                    CommandOption(1, keyword_args=('--foo',))
                ])
    with pytest.raises(ValueError,
                       match='Duplicate keyword args found "--foo"'):
        Command(name='', help=None, fn=lambda x: x,
                options=[
                    CommandOption(1, keyword_args=('-f', '--foo', '--foo'))
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

    assert cli.commands['foo'].help is None
    assert cli.commands['foo'].description == 'A doc about the function'
    assert cli.commands['foo2'].help == 'A first doc'
    assert cli.commands['foo2'].description == 'A doc about the function'
    assert cli.commands['foo3'].help is None
    assert cli.commands['foo3'].description is None


def test_run_command():
    from piou import Cli, Option
    from piou.exceptions import (
        PosParamsCountError, KeywordParamNotFoundError,
        KeywordParamMissingError, CommandNotFoundError
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
        assert foo4 == [1, 2, 3]

    with pytest.raises(CommandNotFoundError,
                       match="Unknown command given. Possible commands are 'foo'") as e:
        cli.run_with_args('toto')
    assert e.value.input_args == ('toto',)

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


def test_reuse_option():
    from piou import Cli, Option

    called = False

    cli = Cli(description='A CLI tool',
              propagate_options=True)

    Test = Option(1, '--test')

    @cli.command()
    def foo(test1: int = Test):
        nonlocal called
        assert isinstance(test1, int)
        called = True

    @cli.command()
    def bar(test2: int = Test):
        assert isinstance(test2, int)

    cli._group.run_with_args('foo')
    assert called


def test_run_command_pass_global_args():
    from piou import Cli, Option

    called, processor_called = False, False

    cli = Cli(description='A CLI tool',
              propagate_options=True)

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
    ):
        nonlocal called
        called = True
        assert foo1 == 1
        assert quiet is True
        assert verbose is False

    cli._group.run_with_args('-q', 'foo', '1')
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
            # test: bool = False,
            # quiet: bool = False,
            # verbose: bool = False,
            foo1: int = Option(..., help='Foo arguments'),
            foo2: str = Option(..., '-f', '--foo2', help='Foo2 arguments'),
            foo3: str = Option('a value', '--foo3', help='Foo3 arguments'),
    ):
        nonlocal called
        called = True
        # assert test is True
        # assert quiet is True
        # assert verbose is False
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
            # quiet: bool = False,
            # verbose: bool = False,
    ):
        nonlocal group2_called
        group2_called = True
        # assert quiet is True
        # assert verbose is False

    cli._group.run_with_args('-q', 'foo2', 'baz')
    assert group2_called


def test_run_group_command_pass_global_args():
    called = False

    from piou import Cli, Option

    cli = Cli(description='A CLI tool',
              propagate_options=True)

    cli.add_option('-q', '--quiet', help='Do not output any message')
    cli.add_option('--verbose', help='Increase verbosity')

    processor_called = False

    def processor(quiet: bool, verbose: bool):
        nonlocal processor_called
        processor_called = True

        assert quiet is True
        assert verbose is False

    cli.set_options_processor(processor)

    foo_sub_cmd = cli.add_sub_parser(cmd='foo', description='A sub command',
                                     propagate_options=True)
    foo_sub_cmd.add_option('--test', help='Test mode')

    sub_processor_called = False

    def sub_processor(test: bool):
        nonlocal sub_processor_called
        sub_processor_called = True
        assert test is True

    foo_sub_cmd.set_options_processor(sub_processor)

    @foo_sub_cmd.command(cmd='baz', help='Run toto command')
    def baz_main(
            test: bool = False,
            quiet: bool = False,
            verbose: bool = False,
            foo1: int = Option(..., help='Foo arguments')
    ):
        nonlocal called
        called = True
        assert test is True
        assert quiet is True
        assert verbose is False
        assert foo1 == 1

    cli._group.run_with_args('-q', 'foo', '--test', 'baz', '1')
    assert called
    assert processor_called
    assert sub_processor_called


def test_option_processor():
    from piou import Cli, Option

    cli = Cli(description='A CLI tool',
              propagate_options=True)

    processor_called = False

    @cli.processor()
    def processor(
            quiet: bool = Option(False, '-q', '--quiet', help='Do not output any message'),
            verbose: bool = Option(False, '--verbose', help='Increase verbosity')
    ):
        nonlocal processor_called
        processor_called = True

        assert quiet is True
        assert verbose is False

    @cli.command()
    def test(**kwargs):
        assert kwargs['quiet']

    cli._group.run_with_args('--quiet', 'test')
    assert processor_called


def test_derived():
    from piou import Cli, Option, Derived

    cli = Cli(description='A CLI tool')

    def processor(a: int = Option(1, '--first-val'),
                  b: int = Option(2, '--second-val')):
        return a + b

    called = False

    @cli.command()
    def test(value: int = Derived(processor)):
        nonlocal called
        called = True
        assert value == 5

    cli._group.run_with_args('test', '--first-val', '3', '--second-val', '2')
    assert called


def test_async_derived():
    from piou import Cli, Option, Derived

    cli = Cli(description='A CLI tool')

    async def processor(a: int = Option(1, '-a'),
                        b: int = Option(2, '-b')):
        await asyncio.sleep(0.01)
        return a + b

    called = False

    @cli.command()
    def test(value: int = Derived(processor)):
        nonlocal called
        called = True
        assert value == 5

    cli._group.run_with_args('test', '-a', '3', '-b', '2')
    assert called


def test_on_cmd_run():
    from piou import Cli, Option, CommandMeta, Derived

    cmd_run_called = False
    is_sub_command = False

    def on_cmd_run(meta: CommandMeta):
        nonlocal cmd_run_called
        cmd_run_called = True
        if not is_sub_command:
            assert meta == CommandMeta(cmd_name='test',
                                       fn_args={'bar': 'bar', 'value': 5},
                                       cmd_args={'a': 3, 'b': 2, 'bar': 'bar'})
        else:
            assert meta == CommandMeta(
                cmd_name='sub.test',
                fn_args={'baz': 'baz'},
                cmd_args={'baz': 'baz'}
            )

    cli = Cli(description='A CLI tool',
              on_cmd_run=on_cmd_run)

    def processor(a: int = Option(1, '-a'),
                  b: int = Option(2, '-b')):
        return a + b

    @cli.command()
    def test(
            value: int = Derived(processor),
            bar: str = Option(None, '--bar')
    ):
        pass

    sub_cmd = cli.add_sub_parser('sub')

    @sub_cmd.processor()
    def sub_processor(verbose: bool = Option(False, '--verbose')):
        pass

    @sub_cmd.command('test')
    def test_sub(
            baz: str = Option(None, '--baz')
    ):
        pass

    cli._group.run_with_args('test', '-a', '3', '-b', '2', '--bar', 'bar')
    assert cmd_run_called

    # Testing sub command
    cmd_run_called = False
    is_sub_command = True
    cli._group.run_with_args('sub', '--verbose', 'test', '--baz', 'baz')
    assert cmd_run_called
