import asyncio
import sys
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest
import pytest_socket

pytest_plugins = "pytest_homeassistant_custom_component"

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


@pytest.fixture
def event_loop_policy():
    pytest_socket.enable_socket()
    if hasattr(asyncio, "WindowsSelectorEventLoopPolicy"):
        policy = asyncio.WindowsSelectorEventLoopPolicy()
        asyncio.set_event_loop_policy(policy)
        return policy
    return asyncio.get_event_loop_policy()


@pytest.fixture(autouse=True)
def _mock_ws_start(request):
    if request.node.get_closest_marker("real_ws_start"):
        yield
        return
    with patch(
        "custom_components.signalk_ha.coordinator.SignalKCoordinator.async_start",
        new=AsyncMock(),
    ):
        yield
