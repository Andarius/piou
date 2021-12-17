from pathlib import Path
import datetime as dt

import pytest


@pytest.mark.parametrize('cmd, is_required, is_positional', [
    ([...], True, True),
    ([None, '--foo'], False, True)
])
def test_command_arg(cmd, is_required, is_positional):
    from piou.utils import CommandArg
    cmd = CommandArg(*cmd)
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
    from piou.utils import parse_args, CmdArg
    cmd_args = []
    for _arg in args:
        arg = CmdArg(_arg['default'], *_arg.get('keyword_args', []))
        arg.name = _arg['name']
        cmd_args.append(arg)
    output = parse_args(input_str.split(' '),
                        command_args=cmd_args)
    assert output == expected
    # assert output == expected_output


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
    from piou.utils import CommandArg

    with pytest.raises(ValueError,
                       match='Duplicate keyword args found "--foo"'):
        Command(name='', help=None, fn=lambda x: x,
                command_args=[
                    CommandArg(None, keyword_args=('-f', '--foo')),
                    CommandArg(None, keyword_args=('--foo',))
                ])
    with pytest.raises(ValueError,
                       match='Duplicate keyword args found "--foo"'):
        Command(name='', help=None, fn=lambda x: x,
                command_args=[
                    CommandArg(None, keyword_args=('-f', '--foo', '--foo'))
                ])


# def test_cli_no_command(capfd):
#     from piou import Cli
#
#     cli = Cli(description='A CLI tool')
#     cli.run()
#     out, _ = capfd.readouterr()
#     print(out)
#     assert out.startswith('Unknown command "')


def test_cli():
    from piou import Cli
    cli = Cli(description='A CLI tool')
    cli.add_argument('-h', '--help', help='Display this help message')
    cli.add_argument('-q', '--quiet', help='Do not output any message')
    cli.add_argument('--verbose', help='Increase verbosity')

    cli.run()
