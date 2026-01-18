import pytest
import asyncio
from unittest.mock import MagicMock

@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for each test case."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest.fixture
def mock_db():
    return MagicMock()

@pytest.fixture
def mock_ai():
    return MagicMock()
