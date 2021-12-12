# import pytest

# from pioupiou import CmdArg, Parameter
# from pioupiou.utils import


# @pytest.mark.parametrize('parameters, cmd_args, expected_output', [
#     ({'arg1': Parameter(str, CmdArg(...))},
#      'baz',
#      {
#          'arg1': 'baz'
#      }),
#     # ([
#     #          ([...], {}),
#     #         (['--foo'], {}),
#     #         (['--bar'], {}),
#     #
#     #  ], 'baz --foo buz --bar 1 2 3',
#     #
#     # )
#
# ])
# def test_validate_arguments(parameters, cmd_args, expected_output):
#     from cli.utils import parse_args
#     output = parse_args(cmd_args.split(' '), parameters)
#     # assert output == expected_output
