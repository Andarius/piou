import asyncio
import datetime as dt
import re
import sys
from contextlib import contextmanager, nullcontext
from enum import Enum
from functools import partial
from pathlib import Path
from typing import Annotated, Literal, Optional
from uuid import UUID

import pytest
from typing_extensions import LiteralString

from piou.exceptions import InvalidChoiceError

_IS_GE_PY310 = f"{sys.version_info.major}.{sys.version_info.minor:02}" >= "3.10"


async def _async_foo_bar():
    return ["foo", "bar"]


class MyEnum(Enum):
    foo = "bar"
    baz = "foo"


@pytest.mark.parametrize("arg, expected", [("-q", "q"), ("--quiet", "quiet"), ("--quiet-v2", "quiet_v2")])
def test_keyword_arg_to_name(arg, expected):
    from piou.utils import keyword_arg_to_name

    assert keyword_arg_to_name(arg) == expected


@pytest.mark.parametrize(
    "cmd, is_required, is_positional",
    [([...], True, True), ([None, "--foo"], False, True)],
)
def test_command_option(cmd, is_required, is_positional):
    from piou.utils import CommandOption

    cmd = CommandOption(*cmd)
    assert cmd.is_required == is_required
    assert cmd.is_positional_arg == is_positional


@pytest.mark.parametrize(
    "data_type, expected",
    [
        (str, str),
        (Optional[str], str),
        (list, list),
        (list[str], list[str]),
        (Optional[list[int]], list[int]),
    ],
)
def test_extract_optional_type(data_type, expected):
    from piou.utils import extract_optional_type

    assert extract_optional_type(data_type) == expected


def test_get_type_hints_derived():
    from piou.utils import get_type_hints_derived, Derived

    def _derived() -> str:
        return "hello"

    def foo(a: int, bar=Derived(_derived)): ...

    hints = get_type_hints_derived(foo)
    assert hints == {"a": int, "bar": str}


def _get_cmd_opt(default, help, keyword_args, name: str, data_type, arg_name: str | None = None):
    from piou.utils import CommandOption

    opt = CommandOption(default=default, help=help, keyword_args=keyword_args, arg_name=arg_name)
    opt.name = name
    opt.data_type = data_type
    return opt


def test_extract_function_info():
    from piou.utils import Derived, Option, extract_function_info

    def processor(a: int = Option(1, "-a"), b: int = Option(2, "-b")) -> int:
        return a + b

    def test(value=Derived(processor), value2: str = Option("foo", "--value2")): ...

    expected_options = [
        _get_cmd_opt(default=1, help=None, keyword_args=("-a",), name="a", data_type=int, arg_name="__processor.a"),
        _get_cmd_opt(default=2, help=None, keyword_args=("-b",), name="b", data_type=int, arg_name="__processor.b"),
        _get_cmd_opt(
            default="foo",
            help=None,
            keyword_args=("--value2",),
            name="value2",
            data_type=str,
        ),
    ]
    _options, _ = extract_function_info(test)
    assert expected_options == _options


@pytest.mark.parametrize(
    "data_type, value, expected, options",
    [
        (str, "123", "123", None),
        (str, "foo bar", "foo bar", None),
        (int, "123", 123, None),
        (int, "123", 123, None),
        (float, "123", 123, None),
        (float, "0.123", 0.123, None),
        # (bytes, 'foo'.encode('utf-8'), b'foo'),
        (Path, str(Path(__file__).parent / "conftest.py"), Path(__file__).parent / "conftest.py", None),
        (
            Path,
            str(Path(__file__).parent / "foobarbaz.py"),
            Path(__file__).parent / "foobarbaz.py",
            {"raise_path_does_not_exist": False},
        ),
        (list, "1 2 3", ["1", "2", "3"], None),
        (list[str], "1 2 3", ["1", "2", "3"], None),
        (list[int], "1 2 3", [1, 2, 3], None),
        (dict, '{"a": 1, "b": "foo", "c": {"foo": "bar"}}', {"a": 1, "b": "foo", "c": {"foo": "bar"}}, None),
        (dt.date, "2019-01-01", dt.date(2019, 1, 1), None),
        (dt.datetime, "2019-01-01T01:01:01", dt.datetime(2019, 1, 1, 1, 1, 1), None),
        (Literal["foo", "bar"], "bar", "bar", None),
        (UUID, "00000000-0000-0000-0000-000000000000", UUID("00000000-0000-0000-0000-000000000000"), None),
        (MyEnum, "foo", "bar", None),
        (LiteralString, "foo", "foo", None),
    ],
)
def test_validate_value(data_type, value, expected, options):
    from piou.utils import validate_value

    _options = options or {}

    assert validate_value(data_type, value, **_options) == expected
    assert validate_value(Optional[data_type], value, **_options) == expected
    if _IS_GE_PY310:
        assert validate_value(data_type | None, value, **_options) == expected


class TestSecretType:
    """Tests for Secret type with configurable masking."""

    from piou import Secret

    def test_command_option_is_secret_property(self):
        """Test is_secret property on CommandOption."""
        from piou.utils import CommandOption, Secret, Password

        opt_secret = CommandOption("value")
        opt_secret.data_type = Secret
        assert opt_secret.is_secret is True

        opt_password = CommandOption("value")
        opt_password.data_type = Password
        assert opt_password.is_secret is True  # Password is also a secret type

        opt_str = CommandOption("value")
        opt_str.data_type = str
        assert opt_str.is_secret is False

    @pytest.mark.parametrize(
        "secret_type, value",
        [
            pytest.param(Secret(), "abc123", id="full_mask"),
            pytest.param(Secret(show_first=3), "sk-12345678", id="show_first"),
            pytest.param(Secret(show_last=4), "4111111111111234", id="show_last"),
        ],
    )
    def test_validate_value_with_secret(self, secret_type, value):
        """Test validate_value handles Secret types."""
        from piou.utils import validate_value

        result = validate_value(secret_type, value)
        assert result == value
        assert isinstance(result, str)


class TestMaybePath:
    """Tests for MaybePath type that skips existence checking."""

    @pytest.mark.parametrize(
        "path_type, expectation",
        [
            pytest.param("MaybePath", nullcontext(), id="maybe_path_skips_existence_check"),
            pytest.param(
                "Path", pytest.raises(FileNotFoundError, match="File not found"), id="path_raises_for_missing_file"
            ),
        ],
    )
    def test_validate_value_path_existence(self, path_type, expectation):
        """Test validate_value behavior for Path vs MaybePath with missing files."""
        from piou.utils import MaybePath, validate_value

        dtype = MaybePath if path_type == "MaybePath" else Path
        with expectation:
            result = validate_value(dtype, "/nonexistent/path/file.txt")
            assert result == Path("/nonexistent/path/file.txt")

    @pytest.mark.parametrize(
        "path_type, expected",
        [
            pytest.param("MaybePath", True, id="maybe_path_is_optional"),
            pytest.param("Path", False, id="path_is_not_optional"),
        ],
    )
    def test_command_option_is_optional_path(self, path_type, expected):
        """Test is_optional_path property on CommandOption."""
        from piou.utils import CommandOption, MaybePath

        opt = CommandOption("value")
        opt.data_type = MaybePath if path_type == "MaybePath" else Path  # type: ignore[assignment]
        assert opt.is_optional_path is expected

    def test_cli_with_optional_path(self):
        """Test MaybePath works in a CLI command."""
        from piou import Cli, Option, MaybePath

        cli = Cli(description="Test CLI")
        result = {}

        @cli.command()
        def test(config: MaybePath = Option(..., "--config")):
            result["config"] = config

        cli.run_with_args("test", "--config", "/some/nonexistent/config.yaml")
        assert result["config"] == Path("/some/nonexistent/config.yaml")


class TestChoices:
    @pytest.mark.parametrize(
        "input_type, value, options, expectation",
        [
            pytest.param(
                str,
                "FOO",
                {"case_sensitive": False, "choices": ["foo", "bar"]},
                nullcontext("FOO"),
                id="case_insensitive_upper",
            ),
            pytest.param(
                str,
                "foo",
                {"case_sensitive": False, "choices": ["foo", "bar"]},
                nullcontext("foo"),
                id="case_insensitive_lower",
            ),
            pytest.param(
                str,
                "fOo",
                {"case_sensitive": False, "choices": ["foo", "bar"]},
                nullcontext("fOo"),
                id="case_insensitive_mixed",
            ),
            pytest.param(
                str,
                "fOo",
                {"case_sensitive": True, "choices": ["foo", "bar"]},
                pytest.raises(InvalidChoiceError),
                id="case_sensitive_rejects",
            ),
            pytest.param(
                Literal["fOo"],
                "fOo",
                {"case_sensitive": False, "choices": ["foo", "bar"]},
                nullcontext("fOo"),
                id="literal_case_insensitive",
            ),
        ],
    )
    def test_choices_case_sensitivity(self, input_type, value, options, expectation):
        from piou.utils import validate_value

        with expectation as expected:
            assert validate_value(input_type, value, **options) == expected

    @pytest.mark.parametrize(
        "value, choices, case_sensitive, expected_valid",
        [
            # Regex pattern matching
            pytest.param("dev-123", [re.compile(r"dev-\d+")], True, True, id="regex_match"),
            pytest.param("dev-abc", [re.compile(r"dev-\d+")], True, False, id="regex_no_match"),
            pytest.param("prod", [re.compile(r"dev-\d+")], True, False, id="regex_literal_no_match"),
            # Mixed literal and regex
            pytest.param("prod", ["prod", re.compile(r"dev-\d+")], True, True, id="mixed_literal_match"),
            pytest.param("dev-456", ["prod", re.compile(r"dev-\d+")], True, True, id="mixed_regex_match"),
            pytest.param("staging", ["prod", re.compile(r"dev-\d+")], True, False, id="mixed_no_match"),
            # Multiple regex patterns
            pytest.param(
                "test-123.db", [re.compile(r"test-\d+\.db"), re.compile(r"dev-\d+")], True, True, id="multi_regex_first"
            ),
            pytest.param(
                "dev-999", [re.compile(r"test-\d+\.db"), re.compile(r"dev-\d+")], True, True, id="multi_regex_second"
            ),
            pytest.param(
                "invalid", [re.compile(r"test-\d+\.db"), re.compile(r"dev-\d+")], True, False, id="multi_regex_no_match"
            ),
            # Regex with fullmatch (must match entire string)
            pytest.param("dev-123-extra", [re.compile(r"dev-\d+")], True, False, id="fullmatch_suffix"),
            pytest.param("prefix-dev-123", [re.compile(r"dev-\d+")], True, False, id="fullmatch_prefix"),
            # case_sensitive only affects literals, not regex
            pytest.param("DEV-123", [re.compile(r"DEV-\d+")], False, True, id="regex_case_insensitive_flag_ignored"),
            pytest.param("dev-123", [re.compile(r"DEV-\d+")], False, False, id="regex_case_mismatch"),
            # Use re.IGNORECASE for case-insensitive regex
            pytest.param("DEV-123", [re.compile(r"dev-\d+", re.IGNORECASE)], True, True, id="regex_ignorecase_upper"),
            pytest.param("dev-123", [re.compile(r"dev-\d+", re.IGNORECASE)], True, True, id="regex_ignorecase_lower"),
            # Mixed: literal with case_sensitive=False, regex with IGNORECASE
            pytest.param("PROD", ["prod", re.compile(r"dev-\d+")], False, True, id="mixed_literal_case_insensitive"),
            pytest.param(
                "DEV-999", ["prod", re.compile(r"dev-\d+", re.IGNORECASE)], False, True, id="mixed_regex_ignorecase"
            ),
        ],
    )
    def test_regex_choices(self, value, choices, case_sensitive, expected_valid):
        from piou.utils import validate_value
        from piou.exceptions import InvalidChoiceError

        if expected_valid:
            result = validate_value(str, value, case_sensitive=case_sensitive, choices=choices)
            assert result == value
        else:
            with pytest.raises(InvalidChoiceError) as e:
                validate_value(str, value, case_sensitive=case_sensitive, choices=choices)
            assert e.value.value == value
            assert e.value.choices == choices

    @staticmethod
    async def _test_invalid():
        return [1, 2, 3]

    @pytest.mark.parametrize(
        "choices",
        [[1, 2, 3], lambda: [1, 2, 3], _test_invalid],
    )
    def test_invalid_command_options_choices(self, choices):
        from piou.command import CommandOption

        opt = CommandOption(None, choices=choices)
        with pytest.raises(ValueError, match="Pick either a Literal type or choices"):
            opt.data_type = Literal["foo"]  # type: ignore[assignment]

    def test_choices(self):
        """Test that choices can be an async function."""
        from piou.command import CommandOption

        async def get_choices() -> list[str]:
            return ["foo", "bar", "baz"]

        opt = CommandOption("", choices=get_choices)
        # get_choices should work with async functions
        assert opt.get_choices() == ["foo", "bar", "baz"]
        # validate should work with async choices
        assert opt.validate("foo") == "foo"


def test_regex_helper():
    """Test the Regex helper function creates proper patterns."""
    from piou.utils import Regex

    pattern = Regex(r"dev-\d+")
    assert isinstance(pattern, re.Pattern)
    assert pattern.fullmatch("dev-123")
    assert not pattern.fullmatch("dev-abc")

    # With flags
    pattern_i = Regex(r"dev-\d+", re.IGNORECASE)
    assert pattern_i.fullmatch("DEV-123")


def test_invalid_choice_error_attributes():
    """Test that InvalidChoiceError correctly separates literal and regex choices."""
    from piou.exceptions import InvalidChoiceError

    choices = ["prod", "staging", re.compile(r"dev-\d+"), re.compile(r"test-\d+\.db")]
    err = InvalidChoiceError("invalid", choices)

    assert err.value == "invalid"
    assert err.literal_choices == ["prod", "staging"]
    assert err.regex_patterns == [r"dev-\d+", r"test-\d+\.db"]


@pytest.mark.parametrize(
    "data_type, value, expected, expected_str",
    [(Path, "a-file.py", FileNotFoundError, 'File not found: "a-file.py"')],
)
def test_invalid_validate_value(data_type, value, expected, expected_str):
    from piou.utils import validate_value

    with pytest.raises(expected, match=re.escape(expected_str)):
        validate_value(data_type, value)


@pytest.mark.parametrize(
    "input_str, types, expected_pos_args, expected_key_args",
    [
        ("--foo buz", {"foo": str}, [], {"--foo": "buz"}),
        ('--foo "buz biz"', {"foo": str}, [], {"--foo": "buz biz"}),
        ("--foo buz -b baz", {"foo": str, "b": str}, [], {"--foo": "buz", "-b": "baz"}),
        ("--foo -b", {"foo": bool, "b": True}, [], {"--foo": True, "-b": True}),
        ("foo buz -b baz", {"b": str}, ["foo", "buz"], {"-b": "baz"}),
        ('"buz baz"', {}, ["buz baz"], {}),
        ("foo", {}, ["foo"], {}),
        (
            "--foo 1 2 3 --bar",
            {"foo": list[int], "bar": str},
            [],
            {"--foo": "1 2 3", "--bar": True},
        ),
        (
            "foo bar --foo1 1 2 3 --foo2 --foo3 test",
            {"foo1": list[int], "foo2": bool, "foo3": str},
            ["foo", "bar"],
            {"--foo1": "1 2 3", "--foo2": True, "--foo3": "test"},
        ),
        ("--foo /tmp", {"foo": Path}, [], {"--foo": "/tmp"}),
        ("--foo-bar /tmp", {"foo_bar": Path}, [], {"--foo-bar": "/tmp"}),
    ],
)
def test_get_cmd_args(input_str, types, expected_pos_args, expected_key_args):
    from piou.utils import get_cmd_args

    pos_args, key_args = get_cmd_args(input_str, types)
    assert pos_args == expected_pos_args
    assert key_args == expected_key_args


@pytest.mark.parametrize(
    "input_str, args, expected",
    [
        (
            "baz --foo buz",
            [
                {"default": ..., "name": "baz"},
                {"default": ..., "keyword_args": ["--foo"], "name": "foo"},
            ],
            {"baz": "baz", "foo": "buz"},
        ),
        (
            "--foo buz",
            [{"default": ..., "keyword_args": ["--foo", "-f"], "name": "foo"}],
            {"foo": "buz"},
        ),
        (
            "'baz buz'",
            [
                {"default": ..., "name": "baz"},
            ],
            {"baz": "baz buz"},
        ),
    ],
)
def test_validate_arguments(input_str, args, expected):
    from piou.utils import Option, convert_args_to_dict

    cmd_args = []
    for _arg in args:
        arg = Option(_arg["default"], *_arg.get("keyword_args", []))
        arg.name = _arg["name"]
        cmd_args.append(arg)
    output = convert_args_to_dict(input_str.split(" "), options=cmd_args)
    assert output == expected


def test_command():
    from piou.command import Command

    called = False

    def test_fn(foo, *, bar=None):
        nonlocal called

        assert foo == 1
        assert bar == "baz"

        called = True

    cmd = Command(name="", help=None, fn=test_fn)
    cmd.run(1, bar="baz")
    assert called


def test_command_options():
    from piou.command import Command, CommandOption

    # Required Pos at the end
    opt1 = CommandOption(...)
    opt1.name = "z"
    # Required Keyword
    opt2 = CommandOption(..., keyword_args=("-a",))
    opt2.name = "a"
    # Optional Keyword
    opt3 = CommandOption(False, keyword_args=("-b",))
    opt3.name = "b"
    opt4 = CommandOption(False, keyword_args=("-c",))
    opt4.name = "c"
    opt5 = CommandOption(False, keyword_args=("-d",))
    opt5.name = "d"

    def fn(*args, **kwargs):
        pass

    cmd = Command(name="", fn=fn, options=[opt4, opt5, opt3, opt2, opt1])
    assert [x.name for x in cmd.options_sorted] == ["z", "a", "b", "c", "d"]


def test_command_async():
    from piou.command import Command

    called = False

    async def test_fn(foo, *, bar=None):
        nonlocal called

        assert foo == 1
        assert bar == "baz"

        called = True

    cmd = Command(name="", fn=test_fn, help=None)
    cmd.run(1, bar="baz")
    assert called


def test_command_raises_error_on_duplicate_args():
    from piou.command import Command
    from piou.utils import CommandOption

    with pytest.raises(ValueError, match='Duplicate keyword args found "--foo"'):
        Command(
            name="",
            help=None,
            fn=lambda x: x,
            options=[
                CommandOption(1, keyword_args=("-f", "--foo")),
                CommandOption(1, keyword_args=("--foo",)),
            ],
        )
    with pytest.raises(ValueError, match='Duplicate keyword args found "--foo"'):
        Command(
            name="",
            help=None,
            fn=lambda x: x,
            options=[CommandOption(1, keyword_args=("-f", "--foo", "--foo"))],
        )


def test_command_wrapper_help():
    from piou import Cli

    cli = Cli(description="A CLI tool")

    @cli.command(cmd="foo")
    def foo_main():
        """
        A doc about the function
        """
        pass

    @cli.command(cmd="foo2", help="A first doc")
    def foo_2_main():
        """
        A doc about the function
        """
        pass

    @cli.command(cmd="foo3")
    def foo_3_main():
        pass

    assert cli.commands["foo"].help is None
    assert cli.commands["foo"].description == "A doc about the function"
    assert cli.commands["foo2"].help == "A first doc"
    assert cli.commands["foo2"].description == "A doc about the function"
    assert cli.commands["foo3"].help is None
    assert cli.commands["foo3"].description is None


@contextmanager
def raises_exit(code: int = 1):
    with pytest.raises(SystemExit) as exit_error:
        fn = yield
        print(fn)
    assert isinstance(exit_error.type, SystemExit)
    assert exit_error.value.code == code


def test_run_command():
    from piou import Cli, Option
    from piou.exceptions import (
        PosParamsCountError,
        KeywordParamNotFoundError,
        KeywordParamMissingError,
        CommandNotFoundError,
    )

    called, processor_called = False, False

    cli = Cli(description="A CLI tool")

    cli.add_option("-q", "--quiet", help="Do not output any message")
    cli.add_option("--verbose", help="Increase verbosity")

    def processor(quiet: bool, verbose: bool):
        nonlocal processor_called
        processor_called = True
        assert quiet is True
        assert verbose is False

    cli.set_options_processor(processor)

    @cli.command(cmd="foo", help="Run foo command")
    def foo_main(
        foo1: int = Option(..., help="Foo arguments"),
        foo2: str = Option(..., "-f", "--foo2", help="Foo2 arguments"),
        foo3: str = Option(None, "-g", "--foo3", help="Foo3 arguments"),
        foo4: list[int] = Option(None, "--foo4", help="Foo4 arguments"),
    ):
        nonlocal called
        called = True
        assert foo1 == 1
        assert foo2 == "toto"
        assert foo3 is None
        assert foo4 == [1, 2, 3]

    with pytest.raises(CommandNotFoundError, match="Unknown command given. Possible commands are 'foo'"):
        cli._group.run_with_args("toto")

    with pytest.raises(PosParamsCountError, match="Expected 1 positional values but got 0"):
        cli._group.run_with_args("foo")

    assert not called
    assert not processor_called

    with pytest.raises(KeywordParamNotFoundError, match="Could not find parameter '-vvv'"):
        cli._group.run_with_args("foo", "1", "-vvv")

    assert not called
    assert not processor_called

    with pytest.raises(
        KeywordParamMissingError,
        match="Missing value for required keyword parameter 'foo2'",
    ):
        cli._group.run_with_args("-q", "foo", "1", "--foo4", "1 2 3")
    assert not called
    assert not processor_called

    cli._group.run_with_args("-q", "foo", "1", "-f", "toto", "--foo4", "1 2 3")
    assert called
    assert processor_called


def test_run_async_cmd():
    from piou import Cli

    called = False

    cli = Cli(description="A CLI tool")

    @cli.command("foo")
    async def foo():
        nonlocal called
        called = True

    cli.run_with_args("foo")
    assert called
    # Can run again
    cli.run_with_args("foo")


def test_reuse_option():
    from piou import Cli, Option

    called = False

    cli = Cli(description="A CLI tool", propagate_options=True)

    Test = Option(1, "--test")

    @cli.command()
    def foo(test1: int = Test):
        nonlocal called
        assert isinstance(test1, int)
        called = True

    @cli.command()
    def bar(test2: int = Test):
        assert isinstance(test2, int)

    cli._group.run_with_args("foo")
    assert called


def test_run_command_pass_global_args():
    from piou import Cli, Option

    called, processor_called = False, False

    cli = Cli(description="A CLI tool", propagate_options=True)

    cli.add_option("-q", "--quiet", help="Do not output any message")
    cli.add_option("--verbose", help="Increase verbosity")

    def processor(quiet: bool, verbose: bool):
        nonlocal processor_called
        processor_called = True
        assert quiet is True
        assert verbose is False

    cli.set_options_processor(processor)

    @cli.command(cmd="foo", help="Run foo command")
    def foo_main(
        quiet: bool,
        verbose: bool,
        foo1: int = Option(..., help="Foo arguments"),
    ):
        nonlocal called
        called = True
        assert foo1 == 1, "Foo1 should be 1"
        assert quiet is True, "Quiet should be True"
        assert verbose is False, "Verbose should be False"

    #
    cli._group.run_with_args("-q", "foo", "1")
    assert called
    assert processor_called

    called, processor_called = False, False
    # Also works when passing the global option to the command
    cli._group.run_with_args("foo", "1", "-q")
    assert called
    assert processor_called


def test_run_group_command():
    called = False

    from piou import Cli, Option, CommandGroup

    cli = Cli(description="A CLI tool")

    cli.add_option("-q", "--quiet", help="Do not output any message")
    cli.add_option("--verbose", help="Increase verbosity")

    processor_called = False

    def processor(quiet: bool, verbose: bool):
        nonlocal processor_called
        processor_called = True

        assert quiet is True
        assert verbose is False

    cli.set_options_processor(processor)

    foo_sub_cmd = cli.add_sub_parser(cmd="foo", description="A sub command")
    foo_sub_cmd.add_option("--test", help="Test mode")

    sub_processor_called = False

    def sub_processor(test: bool):
        nonlocal sub_processor_called
        sub_processor_called = True
        assert test is True

    foo_sub_cmd.set_options_processor(sub_processor)

    @foo_sub_cmd.command(cmd="bar", help="Run baz command")
    def bar_main(**kwargs):
        pass

    @foo_sub_cmd.command(cmd="baz", help="Run toto command")
    def baz_main(
        # test: bool = False,
        # quiet: bool = False,
        # verbose: bool = False,
        foo1: int = Option(..., help="Foo arguments"),
        foo2: str = Option(..., "-f", "--foo2", help="Foo2 arguments"),
        foo3: LiteralString = Option("a value", "--foo3", help="Foo3 arguments"),
    ):
        nonlocal called
        called = True
        # assert test is True
        # assert quiet is True
        # assert verbose is False
        assert foo1 == 1
        assert foo2 == "toto"
        assert foo3 == "a value"

    cli._group.run_with_args("-q", "foo", "--test", "baz", "1", "-f", "toto")
    assert called
    assert processor_called
    assert sub_processor_called

    group2 = CommandGroup(name="foo2")
    cli.add_command_group(group2)

    group2_called = False

    @group2.command("baz")
    def baz_2_main(
        # quiet: bool = False,
        # verbose: bool = False,
    ):
        nonlocal group2_called
        group2_called = True
        # assert quiet is True
        # assert verbose is False

    cli._group.run_with_args("-q", "foo2", "baz")
    assert group2_called


def test_run_group_command_pass_global_args():
    called = False

    from piou import Cli, Option

    cli = Cli(description="A CLI tool", propagate_options=True)

    cli.add_option("-q", "--quiet", help="Do not output any message")
    cli.add_option("--verbose", help="Increase verbosity")

    processor_called = False

    def processor(quiet: bool, verbose: bool):
        nonlocal processor_called
        processor_called = True

        assert quiet is True
        assert verbose is False

    cli.set_options_processor(processor)

    foo_sub_cmd = cli.add_sub_parser(cmd="foo", description="A sub command", propagate_options=True)
    foo_sub_cmd.add_option("--test", help="Test mode")

    sub_processor_called = False

    def sub_processor(test: bool):
        nonlocal sub_processor_called
        sub_processor_called = True
        assert test is True

    foo_sub_cmd.set_options_processor(sub_processor)

    @foo_sub_cmd.command(cmd="baz", help="Run toto command")
    def baz_main(
        test: bool = False,
        quiet: bool = False,
        verbose: bool = False,
        foo1: int = Option(..., help="Foo arguments"),
    ):
        nonlocal called
        called = True
        assert test is True
        assert quiet is True
        assert verbose is False
        assert foo1 == 1

    cli._group.run_with_args("-q", "foo", "--test", "baz", "1")
    assert called
    assert processor_called
    assert sub_processor_called


def test_option_processor():
    from piou import Cli, Option

    cli = Cli(description="A CLI tool", propagate_options=True)

    processor_called = False
    test_called = False

    @cli.processor()
    def processor(
        quiet: bool = Option(False, "-q", "--quiet", help="Do not output any message"),
        verbose: bool = Option(False, "--verbose", help="Increase verbosity"),
    ):
        nonlocal processor_called
        processor_called = True

        assert quiet is True
        assert verbose is False

    @cli.command()
    def test(**kwargs):
        nonlocal test_called
        assert kwargs["quiet"]
        test_called = True

    cli._group.run_with_args("--quiet", "test")
    assert processor_called
    assert test_called


def test_derived():
    from piou import Cli, Option, Derived

    cli = Cli(description="A CLI tool")

    def processor(a: int = Option(1, "--first-val"), b: int = Option(2, "--second-val")):
        return a + b

    def processor2(a: int = Option(1, "--first-val"), b: int = Option(2, "--second-val")) -> int:
        return a + b

    def processor3(a: int = Option(3, "--third-val"), b: int = Option(4, "--fourth-val")) -> int:
        return a + b

    called = False

    @cli.command()
    def test(value: int = Derived(processor)):
        nonlocal called
        called = True
        assert value == 5

    @cli.command()
    def test2(value=Derived(processor2)):
        nonlocal called
        called = True
        assert value == 5

    @cli.command()
    def test3(value1: int = Derived(processor), value2=Derived(processor3)):
        nonlocal called
        called = True
        assert value1 == 5
        assert value2 == 2

    cli.run_with_args("test", "--first-val", "3", "--second-val", "2")
    assert called
    called = False

    cli.run_with_args("test2", "--first-val", "3", "--second-val", "2")
    assert called
    called = False

    cli.run_with_args("test3", "--first-val", "3", "--second-val", "2", "--third-val", "1", "--fourth-val", "1")
    assert called


def test_chained_derived():
    from piou import Cli, Option, Derived

    cli = Cli(description="A CLI tool")

    def processor_1(a: int = Option(1, "-a"), b: int = Option(2, "-b")):
        return a + b

    def processor_2(c: int = Derived(processor_1)):
        return c + 2

    def processor_3(d: int = Derived(processor_2)):
        return d * 2

    called = False

    @cli.command()
    def test(value: int = Derived(processor_3)):
        nonlocal called
        called = True
        assert value == 10

    cli.run_with_args("test")  # , '-a', '3', '-b', '2')
    assert called


def test_async_derived():
    from piou import Cli, Option, Derived

    cli = Cli(description="A CLI tool")

    async def processor(a: int = Option(1, "-a"), b: int = Option(2, "-b")) -> int:
        await asyncio.sleep(0.01)
        return a + b

    called = False

    @cli.command()
    def test(value=Derived(processor), value2: str = Option("foo", "--value")):
        nonlocal called
        called = True
        assert value == 5
        assert isinstance(value, int)
        assert value2 == "foo"

    #
    # @cli.command()
    # def test2(value=Derived(processor)):
    #     nonlocal called
    #     called = True
    #     assert value == 5
    #     assert isinstance(value, int)

    cli.run_with_args("test", "-a", "3", "-b", "2")
    assert called
    called = False
    # cli.run_with_args('test2', '-a', '3', '-b', '2')
    # assert called


def test_dynamic_derived():
    from piou import Cli, Option, Derived

    cli = Cli(description="A CLI tool")

    def processor(arg_name: str):
        def _processor(v: int = Option(1, f"--{arg_name}", arg_name=arg_name)):
            return v

        return _processor

    def processor2(arg_name: str):
        def _processor(v: int = Option(1, arg_name=arg_name)):
            return v

        return _processor

    called = False

    @cli.command()
    def test(
        foo: int = Derived(processor("foo")),
        bar: int = Derived(processor("bar")),
        baz: int = Derived(processor2("baz")),
    ):
        nonlocal called
        called = True
        assert foo + bar + baz == 6

    cli.run_with_args("test", "1", "--foo", "3", "--bar", "2")
    assert called


def test_on_cmd_run():
    from piou import Cli, Option, CommandMeta, Derived

    cmd_run_called = False
    is_sub_command = False

    def on_cmd_run(meta: CommandMeta):
        nonlocal cmd_run_called
        cmd_run_called = True
        if not is_sub_command:
            assert meta == CommandMeta(
                cmd_name="test",
                fn_args={"bar": "bar", "value": 5},
                cmd_args={"__processor.a": 3, "__processor.b": 2, "bar": "bar"},
            )
        else:
            assert meta == CommandMeta(cmd_name="sub.test", fn_args={"baz": "baz"}, cmd_args={"baz": "baz"})

    cli = Cli(description="A CLI tool", on_cmd_run=on_cmd_run)

    def processor(a: int = Option(1, "-a"), b: int = Option(2, "-b")):
        return a + b

    @cli.command()
    def test(value: int = Derived(processor), bar: str = Option(None, "--bar")):
        pass

    sub_cmd = cli.add_sub_parser("sub")

    @sub_cmd.processor()
    def sub_processor(verbose: bool = Option(False, "--verbose")):
        pass

    @sub_cmd.command("test")
    def test_sub(baz: str = Option(None, "--baz")):
        pass

    cli._group.run_with_args("test", "-a", "3", "-b", "2", "--bar", "bar")
    assert cmd_run_called

    # Testing sub command
    cmd_run_called = False
    is_sub_command = True
    cli._group.run_with_args("sub", "--verbose", "test", "--baz", "baz")
    assert cmd_run_called


@pytest.mark.parametrize(
    "arg_type, arg_value, expected",
    [
        (int, "5", 5),
        (dict, '{"foo": 1, "bar": "baz"}', {"foo": 1, "bar": "baz"}),
    ],
)
def test_cmd_args(arg_type, arg_value, expected):
    from piou import Cli, Option

    cli = Cli(description="A CLI tool")

    called = False

    @cli.command(cmd="foo", help="Run foo command")
    def foo_main(bar: arg_type = Option(...)):  # type: ignore[valid-type]
        nonlocal called
        called = True
        assert bar == expected

    cli._group.run_with_args("foo", arg_value)
    assert called


@pytest.mark.parametrize("decorator", ["command", "main"])
def test_main_command(decorator):
    from piou import Cli, Option
    from piou.exceptions import DuplicatedCommandError, CommandException

    cli = Cli(description="A CLI tool")

    called = False

    with pytest.raises(ValueError, match="Main command should not have a command name"):

        @cli.command(cmd="bar", is_main=True)
        def bar():
            pass

    _decorator = partial(cli.command, is_main=True) if decorator == "command" else cli.main

    @_decorator()
    def foo_main(bar: int = Option(...)):
        nonlocal called
        called = True
        assert bar == 1

    with pytest.raises(CommandException, match="Command 'bar' cannot be added with main command"):

        @cli.command("bar")
        def _bar():
            pass

    with pytest.raises(DuplicatedCommandError):

        @cli.command(is_main=True)
        def _bar():
            pass

    cli.run_with_args("1")
    assert called


class TestAnnotated:
    @staticmethod
    def _make_annotated_option(
        type_hint: str,
    ) -> tuple[object, type, type | None, tuple[str, ...] | None]:
        """Helper to create Annotated types for parametrized tests."""
        from piou.utils import Option, Derived, CommandOption, CommandDerivedOption

        def processor() -> int:
            return 42

        if type_hint == "regular":
            return int, int, None, None
        elif type_hint == "with_option":
            return Annotated[int, Option(..., "-f", "--foo")], int, CommandOption, ("-f", "--foo")
        elif type_hint == "with_derived":
            return Annotated[int, Derived(processor)], int, CommandDerivedOption, None
        else:  # "no_option"
            return Annotated[str, "some metadata"], str, None, None

    @pytest.mark.parametrize(
        "type_hint_key",
        [
            pytest.param("regular", id="regular_type"),
            pytest.param("with_option", id="annotated_with_option"),
            pytest.param("with_derived", id="annotated_with_derived"),
            pytest.param("no_option", id="annotated_without_option"),
        ],
    )
    def test_extract_annotated_option(self, type_hint_key):
        """Test the helper function that extracts Option from Annotated types."""
        from piou.utils import extract_annotated_option, CommandOption

        type_hint, expected_base, expected_option_type, expected_keyword_args = self._make_annotated_option(
            type_hint_key
        )
        base_type, option = extract_annotated_option(type_hint)

        assert base_type is expected_base
        if expected_option_type is None:
            assert option is None
        else:
            assert isinstance(option, expected_option_type)
            if expected_keyword_args is not None and isinstance(option, CommandOption):
                assert option.keyword_args == expected_keyword_args

    @pytest.mark.parametrize(
        "args, expected",
        [
            pytest.param(["42"], {"bar": 42}, id="positional_arg"),
            pytest.param(["-b", "hello", "--count", "5"], {"bar": "hello", "count": 5}, id="keyword_args"),
            pytest.param([], {"name": "default_name", "count": 10}, id="optional_defaults"),
            pytest.param(["--items", "1 2 3"], {"items": [1, 2, 3]}, id="list_type"),
            pytest.param(["--mode", "release"], {"mode": "release"}, id="literal_type"),
        ],
    )
    def test_annotated_command(self, args, expected):
        """Test Annotated syntax with various argument types."""
        from piou import Cli, Option

        cli = Cli(description="A CLI tool")
        result = {}

        # Define command based on what we're testing
        if "bar" in expected and isinstance(expected["bar"], int):

            @cli.command(cmd="foo")
            def foo_positional(bar: Annotated[int, Option(..., help="Bar value")]):
                result["bar"] = bar

        elif "bar" in expected and isinstance(expected["bar"], str):

            @cli.command(cmd="foo")
            def foo_keyword(
                bar: Annotated[str, Option(..., "-b", "--bar")],
                count: Annotated[int, Option(1, "-c", "--count")],
            ):
                result["bar"] = bar
                result["count"] = count

        elif "name" in expected:

            @cli.command(cmd="foo")
            def foo_optional(
                name: Annotated[str, Option("default_name", "--name")],
                count: Annotated[int, Option(10, "--count")],
            ):
                result["name"] = name
                result["count"] = count

        elif "items" in expected:

            @cli.command(cmd="foo")
            def foo_list(items: Annotated[list[int], Option(..., "--items")]):
                result["items"] = items

        elif "mode" in expected:

            @cli.command(cmd="foo")
            def foo_literal(mode: Annotated[Literal["debug", "release"], Option("debug", "--mode")]):
                result["mode"] = mode

        cli.run_with_args("foo", *args)
        assert result == expected

    def test_annotated_mixed_syntax(self):
        """Test mixing Annotated syntax with default value syntax."""
        from piou import Cli, Option

        cli = Cli(description="A CLI tool")
        result: dict[str, object] = {}

        @cli.command()
        def foo(
            bar: Annotated[int, Option(..., help="Bar value")],
            baz: str = Option(..., "-b", "--baz"),
            count: Annotated[int, Option(1, "-c", "--count")] = 1,
        ):
            result.update(bar=bar, baz=baz, count=count)

        cli.run_with_args("foo", "42", "-b", "hello", "-c", "5")
        assert result == {"bar": 42, "baz": "hello", "count": 5}

    def test_annotated_with_derived(self):
        """Test Annotated syntax with Derived options."""
        from piou import Cli, Option, Derived

        cli = Cli(description="A CLI tool")
        result = {}

        def processor(a: int = Option(1, "-a"), b: int = Option(2, "-b")) -> int:
            return a + b

        @cli.command()
        def foo(value: Annotated[int, Derived(processor)]):
            result["value"] = value

        cli.run_with_args("foo", "-a", "3", "-b", "2")
        assert result == {"value": 5}

    def test_annotated_extract_function_info(self):
        """Test that extract_function_info correctly handles Annotated types."""
        from piou.utils import extract_function_info, Option, Derived

        def processor(a: int = Option(1, "-a"), b: int = Option(2, "-b")) -> int:
            return a + b

        def test_fn(
            pos_arg: Annotated[int, Option(...)],
            keyword_arg: Annotated[str, Option(..., "-k", "--keyword")],
            derived_arg: Annotated[int, Derived(processor)],
        ):
            pass

        options, derived = extract_function_info(test_fn)

        assert len(options) == 4
        assert options[0].name == "pos_arg"
        assert options[0].data_type is int
        assert options[0].is_positional_arg
        assert options[1].name == "keyword_arg"
        assert options[1].data_type is str
        assert options[1].keyword_args == ("-k", "--keyword")
        assert len(derived) == 1
        assert derived[0].param_name == "derived_arg"

    @pytest.mark.parametrize(
        "cmd, args, expected",
        [
            pytest.param("foo", ["--test", "5"], 5, id="with_value"),
            pytest.param("bar", [], 1, id="default_value"),
        ],
    )
    def test_annotated_reuse_option(self, cmd, args, expected):
        """Test reusing the same Option definition with Annotated syntax."""
        from piou import Cli, Option

        cli = Cli(description="A CLI tool")
        result = {}

        TestOption = Option(1, "--test")

        @cli.command()
        def foo(test: Annotated[int, TestOption]):
            result["test"] = test

        @cli.command()
        def bar(test: Annotated[int, TestOption]):
            result["test"] = test

        cli.run_with_args(cmd, *args)
        assert result["test"] == expected


class TestNestedCommandGroup:
    """Tests for nested CommandGroup added via add_group()."""

    def test_nested_command_group_help_display(self, capsys):
        """Test that nested CommandGroup help displays correctly with formatter."""
        from piou import Cli, CommandGroup
        from piou.formatter import RichFormatter

        cli = Cli(description="Test CLI", formatter=RichFormatter())

        parent = CommandGroup(name="parent", help="Parent group")
        child = CommandGroup(name="child", help="Child group")

        @child.command("action", help="Run action")
        def action():
            pass

        parent.add_group(child)
        cli.add_command_group(parent)

        # Trigger help display for the nested group - this was crashing before the fix
        cli.run_with_args("parent", "child", "-h")

        output = capsys.readouterr().out
        assert "USAGE" in output
        assert "COMMANDS" in output
        assert "action" in output
        assert "Run action" in output

    def test_nested_command_group_with_options(self, capsys):
        """Test nested CommandGroup with options displays help correctly."""
        from piou import Cli, CommandGroup, Option
        from piou.formatter import RichFormatter

        cli = Cli(description="Test CLI", formatter=RichFormatter())

        parent = CommandGroup(name="scw", help="Scaleway commands")
        child = CommandGroup(name="baremetal", help="Baremetal commands")

        @child.command("offers", help="List offers")
        def offers(zone: str = Option("fr-par-2", "-z", "--zone", help="Zone")):
            pass

        parent.add_group(child)
        cli.add_command_group(parent)

        # Test parent group help
        cli.run_with_args("scw", "-h")
        output = capsys.readouterr().out
        assert "baremetal" in output
        assert "Baremetal commands" in output

        # Test child group help - exercises print_cmd_group_help
        cli.run_with_args("scw", "baremetal", "-h")
        output = capsys.readouterr().out
        assert "COMMANDS" in output
        assert "offers" in output
        assert "List offers" in output

    def test_command_group_options_sorted_property(self):
        """Test that CommandGroup has options_sorted for interface consistency with Command."""
        from piou import CommandGroup

        group = CommandGroup(name="test", help="Test group")
        group.add_option("-a", "--alpha", help="Alpha option")
        group.add_option("-b", "--beta", help="Beta option")

        # options_sorted should exist and return same as options
        assert hasattr(group, "options_sorted")
        assert group.options_sorted == group.options
