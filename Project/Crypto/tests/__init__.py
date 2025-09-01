"""Test Package for Crypto Trading System."""

import pytest
import asyncio
from typing import Generator

@pytest.fixture
def event_loop() -> Generator:
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()