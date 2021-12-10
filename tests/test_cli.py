import pytest


def test_raises_error_on_duplicate_args():
    from cli.command import Command
    from cli.utils import CommandArgs, Parameter

    with pytest.raises(ValueError,
                       match='Duplicate optional arg found "--foo"') as e:
        Command(name='', help='', fn=lambda x: x,
                optional_params={
                    'foo': Parameter(int, CommandArgs(None, ['-f', '--foo'])),
                    'bar': Parameter(int, CommandArgs(None, ['--foo']))
                })
