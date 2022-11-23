import pytest
import asyncio


@pytest.fixture(scope='function')
def sys_exit_counter(monkeypatch):
    import sys
    exit_counter = 0

    def mock_exit(*args, **kwargs):
        nonlocal exit_counter
        exit_counter += 1

    def get_count():
        return exit_counter

    monkeypatch.setattr(sys, 'exit', mock_exit)
    return get_count


@pytest.fixture(scope='session')
def monkeysession():
    from _pytest.monkeypatch import MonkeyPatch
    mpatch = MonkeyPatch()
    yield mpatch
    mpatch.undo()


@pytest.fixture(scope='session', autouse=True)
def loop(monkeysession):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    monkeysession.setattr('piou.utils.asyncio.get_event_loop', lambda: loop)
    yield
    loop.stop()
