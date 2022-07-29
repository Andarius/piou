import pytest
from typing import Iterator
import asyncio


@pytest.fixture(scope='function')
def loop() -> Iterator[asyncio.AbstractEventLoop]:
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()
