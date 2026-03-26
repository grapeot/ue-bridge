"""
Integration tests — require a running Unreal Editor with UEBridgeEditor plugin.

Run with: python3 -m pytest tests/test_integration.py -v -m integration
Skip if UE is not running (tests will be skipped, not failed).
"""
from __future__ import annotations

import pytest

from ue_bridge import UEBridge
from ue_bridge.errors import UECommandError, UEConnectionError


def ue_available() -> bool:
    try:
        ue = UEBridge(timeout=3.0)
        result = ue.ping()
        ue.close()
        return result
    except (UEConnectionError, Exception):
        return False


skip_no_ue = pytest.mark.skipif(
    not ue_available(),
    reason="Unreal Editor not running or plugin not loaded"
)

pytestmark = [pytest.mark.integration, skip_no_ue]


@pytest.fixture
def ue():
    bridge = UEBridge(timeout=10.0)
    yield bridge
    bridge.close()


class TestConnection:
    def test_ping(self, ue):
        assert ue.ping() is True

    def test_get_context(self, ue):
        ctx = ue.get_context()
        assert "current_blueprint" in ctx or "current_graph" in ctx


class TestAssets:
    def test_list_assets(self, ue):
        assets = ue.list_assets("/Game/")
        assert isinstance(assets, list)
        assert len(assets) > 0

    def test_get_actors(self, ue):
        actors = ue.get_actors()
        assert isinstance(actors, list)
        assert len(actors) > 0


class TestBlueprint:
    def test_get_summary(self, ue):
        summary = ue.get_blueprint_summary("BP_PlatformingCharacter")
        assert "parent_class" in summary
        assert summary["parent_class"] == "Character"

    def test_compile(self, ue):
        result = ue.compile("BP_PlatformingCharacter")
        assert "status" in result or "compiled" in result


class TestInputSystem:
    """Test creating and cleaning up an input action."""

    def test_create_and_verify_input_action(self, ue):
        name = "IA_IntegrationTest"
        # Create
        result = ue.create_input_action(name, value_type="Digital")
        assert "path" in result or "name" in result

        # Verify it exists in assets
        assets = ue.list_assets("/Game/Input/Actions/")
        asset_names = [a.get("asset_name", "") for a in assets]
        assert name in asset_names


class TestNodes:
    """Test node creation and connection in a blueprint."""

    def test_add_function_node_and_get_pins(self, ue):
        node_id = ue.add_function_node(
            "BP_PlatformingCharacter", "Crouch", target="self"
        )
        assert isinstance(node_id, str)
        assert len(node_id) > 0

        pins = ue.get_pins("BP_PlatformingCharacter", node_id)
        assert isinstance(pins, list)
        pin_names = [p["name"] for p in pins]
        assert "execute" in pin_names

        # Clean up
        ue.delete_node("BP_PlatformingCharacter", node_id)
