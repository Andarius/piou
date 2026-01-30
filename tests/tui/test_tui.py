"""Tests for the TUI module."""

from __future__ import annotations

import tempfile
from pathlib import Path
from typing import TYPE_CHECKING, cast
from unittest.mock import MagicMock

import pytest

from piou import Cli, Option
from piou.command import Command, CommandGroup
from piou.tui import (
    TuiContext,
    TuiOption,
    get_tui_context,
    TuiApp,
    TuiState,
    SeverityLevel,
    set_tui_context,
    History,
    CssClass,
)
from piou.tui.runner import CommandRunner
from piou.tui.suggester import (
    CommandSuggester,
    get_command_for_path,
    get_command_suggestions,
    get_subcommand_suggestions,
)
from piou.tui.utils import get_command_help

# Check if textual is available
pytest.importorskip("textual")

if TYPE_CHECKING:
    from textual.widget import Widget


@pytest.fixture
def temp_history_file():
    """Create a temporary path for history testing (file doesn't exist initially)."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".history", delete=False) as f:
        path = Path(f.name)
    # Delete the file so tests start with non-existent file
    path.unlink(missing_ok=True)
    yield path
    path.unlink(missing_ok=True)


@pytest.fixture
def sample_cli():
    """Create a sample CLI for testing."""
    cli = Cli(description="Test CLI")

    @cli.command(cmd="hello", help="Say hello")
    def hello(name: str = Option(..., help="Name to greet")):
        print(f"Hello, {name}!")

    @cli.command(cmd="add", help="Add numbers")
    def add(
        a: int = Option(..., help="First number"),
        b: int = Option(..., help="Second number"),
    ):
        print(f"{a + b}")

    @cli.command(cmd="greet", help="Greet someone")
    def greet(
        name: str = Option(..., help="Name"),
        loud: bool = Option(False, "-l", "--loud", help="Shout"),
    ):
        msg = f"Hi, {name}!"
        print(msg.upper() if loud else msg)

    return cli


@pytest.fixture
def tui_state(sample_cli, temp_history_file):
    """Create a TuiState for testing."""
    commands = list(sample_cli.commands.values())
    return TuiState(
        cli_name="test-cli",
        description=sample_cli.description,
        group=sample_cli.group,
        commands=commands,
        commands_map={f"/{cmd.name}": cmd for cmd in commands},
        history=History(file=temp_history_file),
        runner=CommandRunner(
            group=sample_cli.group,
            formatter=sample_cli.formatter,
            hide_internal_errors=True,
        ),
        on_ready=None,
    )


@pytest.fixture
def cli_with_subcommands():
    """Create a CLI with nested subcommands for testing."""
    cli = Cli(description="Test CLI")

    @cli.command(cmd="hello", help="Say hello")
    def hello(name: str = Option(..., help="Name to greet")):
        print(f"Hello, {name}!")

    @cli.command(cmd="noargs", help="Command with no args")
    def noargs():
        print("No args!")

    @cli.command(cmd="greet", help="Greet someone")
    def greet(
        name: str = Option(..., help="Name"),
        loud: bool = Option(False, "-l", "--loud", help="Shout"),
    ):
        msg = f"Hi, {name}!"
        print(msg.upper() if loud else msg)

    stats = cli.add_sub_parser(cmd="stats", help="Statistics commands")

    @stats.command(cmd="uploads", help="Show upload stats")
    def uploads():
        print("Uploads stats")

    @stats.command(cmd="downloads", help="Show download stats")
    def downloads(path: str = Option(..., help="Path to check")):
        print(f"Downloads for {path}")

    return cli


@pytest.fixture
def mock_app(cli_with_subcommands):
    """Create a mock TuiApp with the test CLI state."""
    app = MagicMock()
    app.state = MagicMock()
    app.state.group = cli_with_subcommands.group
    app.current_suggestions = []
    return app


class TestHistory:
    def test_empty_history(self, temp_history_file):
        """Test history with no existing file."""
        history = History(file=temp_history_file)
        assert history.entries == []
        assert history.index == -1

    def test_load_existing_history(self, temp_history_file):
        """Test loading history from existing file (newest first)."""
        temp_history_file.write_text("cmd1\ncmd2\ncmd3")
        history = History(file=temp_history_file)
        assert history.entries == ["cmd3", "cmd2", "cmd1"]

    def test_append_entry(self, temp_history_file):
        """Test appending entries to history."""
        history = History(file=temp_history_file)
        history.append("new_command")
        assert history.entries[0] == "new_command"
        # Verify it was written to file
        assert "new_command" in temp_history_file.read_text()

    @pytest.mark.parametrize(
        "direction,start_index,expected_sequence",
        [
            pytest.param("up", -1, [("cmd1", 0), ("cmd2", 1), ("cmd3", 2), ("cmd3", 2)], id="up"),
            pytest.param("down", 2, [("cmd2", 1), ("cmd1", 0), (None, -1)], id="down"),
        ],
    )
    def test_navigate(self, temp_history_file, direction, start_index, expected_sequence):
        """Test navigating through history in both directions."""
        history = History(file=temp_history_file)
        history.entries = ["cmd1", "cmd2", "cmd3"]
        history.index = start_index

        for expected_entry, expected_index in expected_sequence:
            assert history.navigate(direction) == expected_entry
            assert history.index == expected_index

    @pytest.mark.parametrize("direction", [pytest.param("up", id="up"), pytest.param("down", id="down")])
    def test_navigate_empty_history(self, temp_history_file, direction):
        """Test navigation with empty history returns None."""
        history = History(file=temp_history_file)
        assert history.navigate(direction) is None

    def test_reset_index(self, temp_history_file):
        """Test resetting navigation index."""
        history = History(file=temp_history_file)
        history.entries = ["cmd1", "cmd2"]
        history.navigate("up")
        history.navigate("up")
        assert history.index == 1

        history.reset_index()
        assert history.index == -1

    def test_save_truncates(self, temp_history_file):
        """Test that save truncates history to max entries."""
        history = History(file=temp_history_file)
        history.entries = [f"cmd{i}" for i in range(100)]
        history.save(max_entries=10)

        saved = temp_history_file.read_text().strip().split("\n")
        assert len(saved) == 10


class TestTuiApp:
    async def test_app_compose(self, tui_state):
        """Test that the app composes correctly."""
        app = TuiApp(state=tui_state)
        async with app.run_test():
            # Check basic structure
            assert app.query_one("#name")
            assert app.query_one("#description")
            assert app.query_one("#messages")
            assert app.query_one("#suggestions")
            assert app.query_one("#input-row")

    async def test_on_tui_ready_called(self):
        """Test that tui_on_ready callback is called when app is ready."""
        cli = Cli(description="Test CLI")
        callback_called = False

        @cli.tui_on_ready
        def on_ready():
            nonlocal callback_called
            callback_called = True

        async with cli.tui_app().run_test():
            assert callback_called

    async def test_command_suggestions_appear(self, tui_state):
        """Test that typing / shows command suggestions."""
        app = TuiApp(state=tui_state)
        async with app.run_test() as pilot:
            await pilot.press("/")
            await pilot.pause()

            suggestions = app.query(f".{CssClass.SUGGESTION}")
            # Should have /help plus the 3 commands
            assert len(suggestions) >= 4

    async def test_command_filter(self, tui_state):
        """Test that suggestions are filtered by input."""
        app = TuiApp(state=tui_state)
        async with app.run_test() as pilot:
            await pilot.press("/", "h")
            await pilot.pause()

            suggestions = app.query(f".{CssClass.SUGGESTION}")
            # Should match /help and /hello
            assert len(suggestions) == 2

    async def test_suggestion_navigation(self, tui_state):
        """Test navigating through suggestions with arrow keys."""
        app = TuiApp(state=tui_state)
        async with app.run_test() as pilot:
            await pilot.press("/")
            await pilot.pause()

            # First suggestion should be selected by default
            selected = app.query(f".{CssClass.SELECTED}")
            assert len(selected) == 1

            # Press down to select next
            await pilot.press("down")
            await pilot.pause()

            # Check that selection moved
            assert app.suggestion_index == 1

    async def test_tab_completes_command(self, tui_state):
        """Test that Tab completes the selected command."""
        app = TuiApp(state=tui_state)
        async with app.run_test() as pilot:
            from textual.widgets import Input

            await pilot.press("/", "a", "d")  # Type /ad to match /add
            await pilot.pause()

            await pilot.press("tab")
            await pilot.pause()

            inp = app.query_one(Input)
            # Should complete to /add with first arg placeholder
            assert "/add" in inp.value

    async def test_execute_command(self, tui_state):
        """Test executing a command."""
        app = TuiApp(state=tui_state)
        async with app.run_test() as pilot:
            from textual.widgets import Input

            # Type and submit a command
            inp = app.query_one(Input)
            inp.value = "/add 2 3"
            await pilot.press("enter")
            await pilot.pause()

            # Check that output was displayed
            outputs = app.query(f".{CssClass.OUTPUT}")
            assert len(outputs) >= 1
            # The output should contain "5" (2 + 3)
            output_text = str(outputs[-1].render())
            assert "5" in output_text

    async def test_help_command(self, tui_state):
        """Test the /help command."""
        app = TuiApp(state=tui_state)
        async with app.run_test() as pilot:
            from textual.widgets import Input

            inp = app.query_one(Input)
            inp.value = "/help"
            await pilot.press("enter")
            await pilot.pause()

            outputs = app.query(f".{CssClass.OUTPUT}")
            assert len(outputs) >= 1

    @pytest.mark.parametrize(
        "initial_value,expect_cleared,expect_exit_hint",
        [
            pytest.param("/hello world", True, False, id="with-input"),
            pytest.param("", False, True, id="empty-input"),
        ],
    )
    async def test_ctrl_c(self, tui_state, initial_value, expect_cleared, expect_exit_hint):
        """Test Ctrl+C clears input when present, shows exit hint when empty."""
        from textual.widgets import Input, Static

        app = TuiApp(state=tui_state)
        async with app.run_test() as pilot:
            inp = app.query_one(Input)
            inp.value = initial_value

            await pilot.press("ctrl+c")
            await pilot.pause()

            if expect_cleared:
                assert inp.value == ""
            if expect_exit_hint:
                hint = app.query_one("#hint", Static)
                assert hint.display is True
                assert app.exit_pending is True

    async def test_history_navigation(self, tui_state):
        """Test history navigation with up/down arrows."""
        # Pre-populate history
        tui_state.history.append("/hello world")
        tui_state.history.append("/add 1 2")

        app = TuiApp(state=tui_state)
        async with app.run_test() as pilot:
            from textual.widgets import Input

            await pilot.press("up")
            await pilot.pause()

            inp = app.query_one(Input)
            # Most recent entry first
            assert inp.value == "/add 1 2"

            await pilot.press("up")
            await pilot.pause()
            # Then older entries
            assert inp.value == "/hello world"

    async def test_command_added_to_history(self, tui_state):
        """Test that executed commands are added to history."""
        app = TuiApp(state=tui_state)
        async with app.run_test() as pilot:
            from textual.widgets import Input

            inp = app.query_one(Input)
            inp.value = "/add 5 5"
            await pilot.press("enter")
            await pilot.pause()

            assert app.history.entries[0] == "/add 5 5"

    async def test_message_displayed_on_submit(self, tui_state):
        """Test that submitted input is shown in messages."""
        app = TuiApp(state=tui_state)
        async with app.run_test() as pilot:
            from textual.widgets import Input

            inp = app.query_one(Input)
            inp.value = "/hello test"
            await pilot.press("enter")
            await pilot.pause()

            messages = app.query(f".{CssClass.MESSAGE}")
            assert len(messages) >= 1

    async def test_error_output(self, tui_state):
        """Test that errors are displayed with error class."""
        app = TuiApp(state=tui_state)
        async with app.run_test() as pilot:
            from textual.widgets import Input

            # Try to execute add without proper arguments
            inp = app.query_one(Input)
            inp.value = "/add notanumber 3"
            await pilot.press("enter")
            await pilot.pause()

            errors = app.query(f".{CssClass.ERROR}")
            assert len(errors) >= 1

    async def test_initial_input(self, tui_state):
        """Test that initial_input pre-fills the input field."""
        app = TuiApp(state=tui_state, initial_input="/hello world")
        async with app.run_test():
            from textual.widgets import Input

            inp = app.query_one(Input)
            assert inp.value == "/hello world"

    @pytest.mark.parametrize(
        "method,rule_id",
        [
            pytest.param("set_rule_above", "rule-above", id="above"),
            pytest.param("set_rule_below", "rule-below", id="below"),
        ],
    )
    async def test_set_rule(self, tui_state, method, rule_id):
        """Test set_rule_* add_class, remove_class, and line_style."""
        from textual.widgets import Rule

        app = TuiApp(state=tui_state)
        async with app.run_test():
            rule = app.query_one(f"#{rule_id}", Rule)
            set_rule = getattr(app, method)

            # add_class preserves existing
            rule.add_class("original-class")
            set_rule(add_class="new-class")
            assert "original-class" in rule.classes
            assert "new-class" in rule.classes

            # remove_class removes
            set_rule(remove_class="new-class")
            assert "new-class" not in rule.classes

            # line_style changes
            set_rule(line_style="double")
            assert rule.line_style == "double"

    async def test_custom_css_injection(self, tui_state):
        """Test that custom CSS is applied to the app."""
        custom_css = "Rule.custom-test { color: red; }"
        app = TuiApp(state=tui_state, css=custom_css)
        async with app.run_test():
            from textual.widgets import Rule

            rule = app.query_one("#rule-above", Rule)
            rule.set_classes("custom-test")
            # The CSS should be loaded and applied
            assert "custom-test" in rule.classes

    @pytest.mark.parametrize(
        "get_app",
        [
            pytest.param(lambda cli, css: cli.tui_app(css=css), id="tui_app"),
            pytest.param(lambda cli, css: cli.tui_cli().get_app(css=css), id="tui_cli.get_app"),
        ],
    )
    async def test_custom_css_via_cli(self, cli_with_subcommands, get_app):
        """Test that custom CSS can be passed through Cli methods."""
        custom_css = "Rule.custom { color: blue; }"
        app = get_app(cli_with_subcommands, custom_css)
        async with app.run_test():
            from textual.widgets import Rule

            rule = app.query_one("#rule-above", Rule)
            rule.set_classes("custom")
            assert "custom" in rule.classes

    @pytest.mark.parametrize(
        "content,expected_display",
        [
            pytest.param("tokens: 100", True, id="string-shows"),
            pytest.param(None, False, id="none-hides"),
        ],
    )
    async def test_set_status_above(self, tui_state, content, expected_display):
        """Test set_status_above shows/hides the status area based on content."""
        from textual.widgets import Static

        app = TuiApp(state=tui_state)
        async with app.run_test() as pilot:
            app.set_status_above(content)
            await pilot.pause()

            status = app.query_one("#status-above", Static)
            assert status.display is expected_display


@pytest.fixture
def reset_context():
    """Reset context before and after each test."""
    set_tui_context(TuiContext())
    yield
    set_tui_context(TuiContext())


class TestTuiContext:
    """Tests for the TuiContext class."""

    @pytest.mark.parametrize(
        "with_tui,expected_is_tui",
        [
            pytest.param(False, False, id="no-tui"),
            pytest.param(True, True, id="with-tui"),
        ],
    )
    def test_is_tui(self, with_tui: bool, expected_is_tui: bool):
        """Test is_tui property reflects whether TUI is attached."""
        ctx = TuiContext()
        if with_tui:
            ctx.tui = MagicMock(spec=TuiApp)
        assert ctx.is_tui is expected_is_tui

    @pytest.mark.parametrize(
        "with_tui,severity",
        [
            pytest.param(False, "information", id="no-tui-information"),
            pytest.param(False, "warning", id="no-tui-warning"),
            pytest.param(False, "error", id="no-tui-error"),
            pytest.param(True, "information", id="with-tui-information"),
            pytest.param(True, "warning", id="with-tui-warning"),
            pytest.param(True, "error", id="with-tui-error"),
        ],
    )
    def test_notify(self, with_tui: bool, severity: SeverityLevel):
        """Test notify() is a no-op without TUI, calls TUI.notify with TUI."""
        ctx = TuiContext()
        tui = MagicMock(spec=TuiApp) if with_tui else None
        ctx.tui = tui
        ctx.notify("Hello", title="Alert", severity=severity)
        if with_tui:
            assert tui is not None
            tui.notify.assert_called_once_with("Hello", title="Alert", severity=severity)

    @pytest.mark.parametrize(
        "with_tui",
        [
            pytest.param(False, id="no-tui"),
            pytest.param(True, id="with-tui"),
        ],
    )
    def test_mount_widget(self, with_tui: bool):
        """Test mount_widget() is a no-op without TUI, calls TUI.mount_widget with TUI."""
        ctx = TuiContext()
        tui = MagicMock(spec=TuiApp) if with_tui else None
        ctx.tui = tui
        widget = cast("Widget", object())
        ctx.mount_widget(widget)
        if with_tui:
            assert tui is not None
            tui.mount_widget.assert_called_once_with(widget)

    @pytest.mark.parametrize(
        "with_tui,content",
        [
            pytest.param(False, "status text", id="no-tui-string"),
            pytest.param(False, None, id="no-tui-none"),
            pytest.param(True, "status text", id="with-tui-string"),
            pytest.param(True, None, id="with-tui-none"),
        ],
    )
    def test_set_status_above(self, with_tui: bool, content: str | None):
        """Test set_status_above() is a no-op without TUI, delegates to TUI with TUI."""
        ctx = TuiContext()
        tui = MagicMock(spec=TuiApp) if with_tui else None
        ctx.tui = tui
        ctx.set_status_above(content)
        if with_tui:
            assert tui is not None
            tui.set_status_above.assert_called_once_with(content)

    def test_get_tui_context_default(self, reset_context):
        """get_tui_context() should return a default context."""
        ctx = get_tui_context()
        assert isinstance(ctx, TuiContext)
        assert ctx.is_tui is False

    def test_set_and_get_tui_context(self, reset_context):
        """set_tui_context() should update the current context."""
        custom_ctx = TuiContext()
        custom_ctx.tui = MagicMock(spec=TuiApp)
        set_tui_context(custom_ctx)

        ctx = get_tui_context()
        assert ctx is custom_ctx
        assert ctx.is_tui is True


class TestTuiOption:
    """Tests for TuiOption derived option."""

    @pytest.mark.parametrize(
        "with_tui,expected_is_tui",
        [
            pytest.param(False, False, id="cli-mode"),
            pytest.param(True, True, id="tui-mode"),
        ],
    )
    def test_tui_option_injection(self, reset_context, with_tui: bool, expected_is_tui: bool):
        """TuiOption injects the current context based on TUI mode."""
        cli = Cli(description="Test")
        captured_ctx = None

        @cli.command(cmd="test")
        def test_cmd(ctx: TuiContext = TuiOption()):
            nonlocal captured_ctx
            captured_ctx = ctx

        if with_tui:
            tui_ctx = TuiContext()
            tui_ctx.tui = MagicMock(spec=TuiApp)
            set_tui_context(tui_ctx)

        cli._group.run_with_args("test")

        assert captured_ctx is not None
        assert isinstance(captured_ctx, TuiContext)
        assert captured_ctx.is_tui is expected_is_tui

    def test_tui_option_with_other_args(self, reset_context):
        """TuiOption works alongside other arguments."""
        cli = Cli(description="Test")
        captured: dict[str, object] = {}

        @cli.command(cmd="greet")
        def greet(
            name: str = Option(..., help="Name"),
            ctx: TuiContext = TuiOption(),
        ):
            captured["name"] = name
            captured["ctx"] = ctx

        cli._group.run_with_args("greet", "Alice")

        assert captured["name"] == "Alice"
        assert isinstance(captured["ctx"], TuiContext)

    def test_get_tui_context_inside_command(self, reset_context):
        """get_tui_context() works inside command functions."""
        cli = Cli(description="Test")
        captured_ctx = None

        @cli.command(cmd="test")
        def test_cmd():
            nonlocal captured_ctx
            captured_ctx = get_tui_context()

        cli._group.run_with_args("test")

        assert captured_ctx is not None
        assert isinstance(captured_ctx, TuiContext)


class TestGetCommandForPath:
    @pytest.mark.parametrize(
        "path,expected_type,expected_name",
        [
            pytest.param("hello", Command, "hello", id="simple-command"),
            pytest.param("HELLO", Command, "hello", id="case-insensitive"),
            pytest.param("/hello", Command, "hello", id="with-leading-slash"),
            pytest.param("stats", CommandGroup, "stats", id="command-group"),
            pytest.param("stats:uploads", Command, "uploads", id="nested-command"),
            pytest.param("stats:UPLOADS", Command, "uploads", id="nested-case-insensitive"),
            pytest.param("nonexistent", type(None), None, id="nonexistent"),
            pytest.param("stats:nonexistent", type(None), None, id="nested-nonexistent"),
        ],
    )
    def test_get_command_for_path(self, cli_with_subcommands, path, expected_type, expected_name):
        """Test that get_command_for_path resolves command paths correctly."""
        result = get_command_for_path(cli_with_subcommands.group, path)
        assert isinstance(result, expected_type)
        if expected_name is not None:
            assert result is not None
            assert result.name == expected_name


class TestCommandSuggester:
    @pytest.mark.parametrize(
        "query,expected_paths",
        [
            pytest.param("", ["/help", "/greet", "/hello", "/noargs", "/stats"], id="cmd-empty"),
            pytest.param("hel", ["/help", "/hello"], id="cmd-partial"),
            pytest.param("hello", ["/hello"], id="cmd-exact"),
            pytest.param("stats", ["/stats"], id="cmd-group"),
            pytest.param("xyz", [], id="cmd-no-match"),
            pytest.param("stats:", {"/stats:downloads", "/stats:uploads"}, id="sub-all"),
            pytest.param("stats:up", {"/stats:uploads"}, id="sub-partial"),
            pytest.param("stats:downloads", {"/stats:downloads"}, id="sub-exact"),
            pytest.param("stats:xyz", set(), id="sub-no-match"),
            pytest.param("hello:", set(), id="sub-not-a-group"),
        ],
    )
    def test_get_suggestions(self, cli_with_subcommands, query, expected_paths):
        """Test that suggestion functions return matching commands/subcommands."""
        if ":" in query:
            suggestions = get_subcommand_suggestions(cli_with_subcommands.group, query)
            paths = {s[0] for s in suggestions}
        else:
            commands = list(cli_with_subcommands.group.commands.values())
            suggestions = get_command_suggestions(commands, query)
            paths = [s[0] for s in suggestions]
        assert paths == expected_paths

    @pytest.mark.parametrize(
        "value,current_suggestions,expected",
        [
            pytest.param("hello", [], None, id="no-slash-prefix"),
            pytest.param("/", [], None, id="slash-only"),
            pytest.param("/  ", [], None, id="slash-with-spaces"),
            pytest.param("/hello", ["/hello", "/help"], None, id="multiple-suggestions"),
            pytest.param("/noargs", [], None, id="command-without-args"),
            pytest.param("/stats ", [], None, id="group-with-space"),
            pytest.param("/nonexistent", [], None, id="nonexistent-command"),
            pytest.param("/nonexistent:", [], None, id="invalid-colon-path"),
            pytest.param("/stats", [], "/stats:downloads", id="group-first-subcommand"),
            pytest.param("/stats:", [], "/stats:downloads", id="colon-first-subcommand"),
            pytest.param("/hello", [], "/hello <name>", id="command-positional-arg"),
            pytest.param("/hello ", [], "/hello <name>", id="command-space-positional-arg"),
            pytest.param("/stats:downloads", [], "/stats:downloads <path>", id="nested-positional-arg"),
            pytest.param("/stats:downloads ", [], "/stats:downloads <path>", id="nested-space-positional-arg"),
        ],
    )
    @pytest.mark.asyncio
    async def test_get_suggestion(self, mock_app, value, current_suggestions, expected):
        """Test get_suggestion returns the expected completion or None."""
        mock_app.current_suggestions = current_suggestions
        suggester = CommandSuggester(mock_app)
        result = await suggester.get_suggestion(value)
        assert result == expected


class TestGetCommandHelp:
    @pytest.mark.parametrize(
        "cmd_name,expected_fragments",
        [
            pytest.param("hello", ["Usage: /hello <name>", "Arguments:", "<name> (str)"], id="positional-arg"),
            pytest.param("noargs", ["Usage: /noargs"], id="no-args"),
            pytest.param("greet", ["Usage: /greet <name>", "Options:", "--loud, -l"], id="keyword-arg"),
        ],
    )
    def test_command_help(self, cli_with_subcommands, cmd_name, expected_fragments):
        """Test get_command_help output for various command types."""
        cmd = cli_with_subcommands.group.commands[cmd_name]
        result = str(get_command_help(cmd))
        for fragment in expected_fragments:
            assert fragment in result

    def test_command_group_help(self, cli_with_subcommands):
        """Test get_command_help output for CommandGroup."""
        group = cli_with_subcommands.group.commands["stats"]
        result = str(get_command_help(group))
        assert "Usage: /stats:<subcommand>" in result
        assert "Subcommands:" in result
        assert "uploads" in result
        assert "downloads" in result

    def test_required_keyword_arg(self):
        """Test get_command_help displays required keyword args correctly."""
        cli = Cli(description="Test")

        @cli.command(cmd="test")
        def test_cmd(name: str = Option(..., "-n", "--name", help="Required name")):
            pass

        cmd = cli.group.commands["test"]
        result = str(get_command_help(cmd))
        assert "-n <value>" in result
        assert "*required" in result

    @pytest.mark.parametrize(
        "annotation,expected_type",
        [
            pytest.param("str | int", "str | int", id="union"),
            pytest.param("str | None", "str", id="optional"),
        ],
    )
    def test_union_type_formatting(self, annotation, expected_type):
        """Test get_command_help formats union types correctly."""
        cli = Cli(description="Test")
        # Use exec to dynamically create command with different type annotations
        exec(
            f"""
@cli.command(cmd="test")
def test_cmd(value: {annotation} = Option(..., help="A value")):
    pass
""",
            {"cli": cli, "Option": Option},
        )
        cmd = cli.group.commands["test"]
        result = str(get_command_help(cmd))
        assert f"({expected_type})" in result


class TestTuiSnapshots:
    """Visual regression tests using pytest-textual-snapshot."""

    @pytest.mark.parametrize(
        "press",
        [
            pytest.param([], id="initial"),
            pytest.param(["/"], id="suggestions"),
            pytest.param(["/", "h"], id="filtered"),
            pytest.param(["/", "down"], id="selection"),
            pytest.param(["ctrl+c"], id="exit-hint"),
        ],
    )
    def test_snapshot(self, snap_compare, press):
        """Snapshot tests for various UI states."""
        assert snap_compare("tui_app.py", press=press, terminal_size=(80, 24))

    @pytest.mark.parametrize(
        "command",
        [
            pytest.param("/add 2 3", id="command"),
            pytest.param("/help", id="help"),
        ],
    )
    def test_snapshot_after_command(self, snap_compare, command):
        """Snapshot tests after executing commands."""

        async def run_before(pilot):
            from textual.widgets import Input

            inp = pilot.app.query_one(Input)
            inp.value = command
            await pilot.press("enter")
            await pilot.pause()

        assert snap_compare("tui_app.py", run_before=run_before, terminal_size=(80, 24))
