import pytest


def test_raises_error_on_duplicate_args():
    from pioupiou.command import Command
    from pioupiou.utils import CommandArgs, CmdArg

    with pytest.raises(ValueError,
                       match='Duplicate keyword args found "--foo"'):
        Command(name='', help='', fn=lambda x: x,
                keyword_params=[
                    CommandArgs(int, keyword_args=['-f', '--foo']),
                    CommandArgs(int, keyword_args=['--foo'])
                ])
