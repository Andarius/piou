import pytest


@pytest.fixture(scope="function")
def sys_exit_counter(monkeypatch):
    import sys

    exit_counter = 0

    def mock_exit(*args, **kwargs):
        nonlocal exit_counter
        exit_counter += 1

    def get_count():
        return exit_counter

    monkeypatch.setattr(sys, "exit", mock_exit)
    return get_count


@pytest.fixture(scope="session")
def monkeysession():
    from _pytest.monkeypatch import MonkeyPatch

    mpatch = MonkeyPatch()
    yield mpatch
    mpatch.undo()
