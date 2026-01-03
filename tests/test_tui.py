"""Tests for the TUI module."""

import tempfile
from pathlib import Path

import pytest

from piou import Cli, Option

# Check if textual is available
pytest.importorskip("textual")

from piou.tui import TuiApp
from piou.tui.cli import History, CssClass


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


# ============================================================================
# History class tests
# ============================================================================


class TestHistory:
    def test_empty_history(self, temp_history_file):
        """Test history with no existing file."""
        history = History(file=temp_history_file)
        assert history.entries == []
        assert history.index == -1

    def test_load_existing_history(self, temp_history_file):
        """Test loading history from existing file."""
        temp_history_file.write_text("cmd1\ncmd2\ncmd3")
        history = History(file=temp_history_file)
        assert history.entries == ["cmd1", "cmd2", "cmd3"]

    def test_append_entry(self, temp_history_file):
        """Test appending entries to history."""
        history = History(file=temp_history_file)
        history.append("new_command")
        assert history.entries[0] == "new_command"
        # Verify it was written to file
        assert "new_command" in temp_history_file.read_text()

    def test_navigate_up(self, temp_history_file):
        """Test navigating up through history."""
        history = History(file=temp_history_file)
        history.entries = ["cmd1", "cmd2", "cmd3"]

        assert history.navigate("up") == "cmd1"
        assert history.index == 0
        assert history.navigate("up") == "cmd2"
        assert history.index == 1
        assert history.navigate("up") == "cmd3"
        assert history.index == 2
        # Should stay at last entry
        assert history.navigate("up") == "cmd3"
        assert history.index == 2

    def test_navigate_down(self, temp_history_file):
        """Test navigating down through history."""
        history = History(file=temp_history_file)
        history.entries = ["cmd1", "cmd2", "cmd3"]
        history.index = 2  # Start at the end

        assert history.navigate("down") == "cmd2"
        assert history.index == 1
        assert history.navigate("down") == "cmd1"
        assert history.index == 0
        assert history.navigate("down") is None
        assert history.index == -1

    def test_navigate_empty_history(self, temp_history_file):
        """Test navigation with empty history."""
        history = History(file=temp_history_file)
        assert history.navigate("up") is None
        assert history.navigate("down") is None

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


# ============================================================================
# TuiApp tests
# ============================================================================


class TestTuiApp:
    async def test_app_compose(self, sample_cli, temp_history_file):
        """Test that the app composes correctly."""
        app = TuiApp(sample_cli, history_file=temp_history_file)
        async with app.run_test():
            # Check basic structure
            assert app.query_one("#name")
            assert app.query_one("#description")
            assert app.query_one("#messages")
            assert app.query_one("#suggestions")
            assert app.query_one("#input-row")

    async def test_command_suggestions_appear(self, sample_cli, temp_history_file):
        """Test that typing / shows command suggestions."""
        app = TuiApp(sample_cli, history_file=temp_history_file)
        async with app.run_test() as pilot:
            await pilot.press("/")
            await pilot.pause()

            suggestions = app.query(f".{CssClass.SUGGESTION}")
            # Should have /help plus the 3 commands
            assert len(suggestions) >= 4

    async def test_command_filter(self, sample_cli, temp_history_file):
        """Test that suggestions are filtered by input."""
        app = TuiApp(sample_cli, history_file=temp_history_file)
        async with app.run_test() as pilot:
            await pilot.press("/", "h")
            await pilot.pause()

            suggestions = app.query(f".{CssClass.SUGGESTION}")
            # Should match /help and /hello
            assert len(suggestions) == 2

    async def test_suggestion_navigation(self, sample_cli, temp_history_file):
        """Test navigating through suggestions with arrow keys."""
        app = TuiApp(sample_cli, history_file=temp_history_file)
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

    async def test_tab_completes_command(self, sample_cli, temp_history_file):
        """Test that Tab completes the selected command."""
        app = TuiApp(sample_cli, history_file=temp_history_file)
        async with app.run_test() as pilot:
            from textual.widgets import Input

            await pilot.press("/", "a", "d")  # Type /ad to match /add
            await pilot.pause()

            await pilot.press("tab")
            await pilot.pause()

            inp = app.query_one(Input)
            # Should complete to /add with first arg placeholder
            assert "/add" in inp.value

    async def test_execute_command(self, sample_cli, temp_history_file):
        """Test executing a command."""
        app = TuiApp(sample_cli, history_file=temp_history_file)
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

    async def test_help_command(self, sample_cli, temp_history_file):
        """Test the /help command."""
        app = TuiApp(sample_cli, history_file=temp_history_file)
        async with app.run_test() as pilot:
            from textual.widgets import Input

            inp = app.query_one(Input)
            inp.value = "/help"
            await pilot.press("enter")
            await pilot.pause()

            outputs = app.query(f".{CssClass.OUTPUT}")
            assert len(outputs) >= 1

    async def test_ctrl_c_clears_input(self, sample_cli, temp_history_file):
        """Test that Ctrl+C clears input when there's text."""
        app = TuiApp(sample_cli, history_file=temp_history_file)
        async with app.run_test() as pilot:
            from textual.widgets import Input

            inp = app.query_one(Input)
            inp.value = "/hello world"

            await pilot.press("ctrl+c")
            await pilot.pause()

            assert inp.value == ""

    async def test_ctrl_c_shows_exit_hint(self, sample_cli, temp_history_file):
        """Test that Ctrl+C shows exit hint when input is empty."""
        app = TuiApp(sample_cli, history_file=temp_history_file)
        async with app.run_test() as pilot:
            from textual.widgets import Static

            await pilot.press("ctrl+c")
            await pilot.pause()

            exit_hint = app.query_one("#exit-hint", Static)
            assert exit_hint.display is True
            assert app.exit_pending is True

    async def test_history_navigation(self, sample_cli, temp_history_file):
        """Test history navigation with up/down arrows."""
        # Pre-populate history
        temp_history_file.write_text("/hello world\n/add 1 2\n")

        app = TuiApp(sample_cli, history_file=temp_history_file)
        async with app.run_test() as pilot:
            from textual.widgets import Input

            await pilot.press("up")
            await pilot.pause()

            inp = app.query_one(Input)
            assert inp.value == "/hello world"

            await pilot.press("up")
            await pilot.pause()
            assert inp.value == "/add 1 2"

    async def test_command_added_to_history(self, sample_cli, temp_history_file):
        """Test that executed commands are added to history."""
        app = TuiApp(sample_cli, history_file=temp_history_file)
        async with app.run_test() as pilot:
            from textual.widgets import Input

            inp = app.query_one(Input)
            inp.value = "/add 5 5"
            await pilot.press("enter")
            await pilot.pause()

            assert app.history.entries[0] == "/add 5 5"

    async def test_message_displayed_on_submit(self, sample_cli, temp_history_file):
        """Test that submitted input is shown in messages."""
        app = TuiApp(sample_cli, history_file=temp_history_file)
        async with app.run_test() as pilot:
            from textual.widgets import Input

            inp = app.query_one(Input)
            inp.value = "/hello test"
            await pilot.press("enter")
            await pilot.pause()

            messages = app.query(f".{CssClass.MESSAGE}")
            assert len(messages) >= 1

    async def test_error_output(self, sample_cli, temp_history_file):
        """Test that errors are displayed with error class."""
        app = TuiApp(sample_cli, history_file=temp_history_file)
        async with app.run_test() as pilot:
            from textual.widgets import Input

            # Try to execute add without proper arguments
            inp = app.query_one(Input)
            inp.value = "/add notanumber 3"
            await pilot.press("enter")
            await pilot.pause()

            errors = app.query(f".{CssClass.ERROR}")
            assert len(errors) >= 1


# ============================================================================
# Snapshot tests
# ============================================================================


class TestTuiSnapshots:
    """Visual regression tests using pytest-textual-snapshot."""

    def test_snapshot_initial_state(self, snap_compare):
        """Snapshot of the app in its initial state."""
        assert snap_compare("snapshot_app.py", terminal_size=(80, 24))

    def test_snapshot_with_suggestions(self, snap_compare):
        """Snapshot showing command suggestions."""
        assert snap_compare("snapshot_app.py", press=["/"], terminal_size=(80, 24))

    def test_snapshot_filtered_suggestions(self, snap_compare):
        """Snapshot with filtered suggestions (typing /h)."""
        assert snap_compare("snapshot_app.py", press=["/", "h"], terminal_size=(80, 24))

    def test_snapshot_after_command(self, snap_compare):
        """Snapshot after executing a command."""

        async def run_before(pilot):
            from textual.widgets import Input

            inp = pilot.app.query_one(Input)
            inp.value = "/add 2 3"
            await pilot.press("enter")
            await pilot.pause()

        assert snap_compare("snapshot_app.py", run_before=run_before, terminal_size=(80, 24))

    def test_snapshot_help_output(self, snap_compare):
        """Snapshot showing help output."""

        async def run_before(pilot):
            from textual.widgets import Input

            inp = pilot.app.query_one(Input)
            inp.value = "/help"
            await pilot.press("enter")
            await pilot.pause()

        assert snap_compare("snapshot_app.py", run_before=run_before, terminal_size=(80, 24))

    def test_snapshot_exit_hint(self, snap_compare):
        """Snapshot showing the exit hint after Ctrl+C."""
        assert snap_compare("snapshot_app.py", press=["ctrl+c"], terminal_size=(80, 24))

    def test_snapshot_suggestion_selection(self, snap_compare):
        """Snapshot with second suggestion selected."""
        assert snap_compare("snapshot_app.py", press=["/", "down"], terminal_size=(80, 24))
