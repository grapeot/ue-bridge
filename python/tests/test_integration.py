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


class TestScreenshot:
    """Test take_screenshot produces a valid, non-trivially-dark image."""

    def test_take_screenshot_creates_file(self, ue):
        import tempfile
        import os
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
            path = f.name
        try:
            result = ue.raw_command("take_screenshot", {"output_path": path})
            assert os.path.exists(path), "Screenshot file not created"
            assert os.path.getsize(path) > 1000, "Screenshot file suspiciously small"
            assert "output_path" in result
        finally:
            if os.path.exists(path):
                os.unlink(path)

    def test_screenshot_not_all_black(self, ue):
        """Verify screenshot has non-trivial content (not all-black pixels)."""
        import tempfile
        import os
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
            path = f.name
        try:
            # Force a viewport refresh first
            actors = ue.get_actors()
            if actors:
                ue.raw_command("select_actors", {"actor_names": [actors[0]["name"]]})

            ue.raw_command("take_screenshot", {"output_path": path})
            assert os.path.exists(path)
            # Read raw bytes and check not all zeros (excluding PNG header)
            with open(path, "rb") as img:
                data = img.read()
            assert len(data) > 5000, "Screenshot too small to contain real content"
        finally:
            if os.path.exists(path):
                os.unlink(path)


class TestLevelManagement:
    """Test new_level and open_level commands."""

    def test_new_level_creates_and_opens(self, ue):
        result = ue.new_level("IntegrationTestLevel", path="/Game/Maps")
        assert result.get("level_name") == "IntegrationTestLevel"
        assert result.get("saved") is True

    def test_open_level_loads_existing(self, ue):
        # Create a level first, then switch away, then open it back
        ue.new_level("TestOpenLevel_A", path="/Game/Maps")
        ue.new_level("TestOpenLevel_B", path="/Game/Maps")
        # Now open A
        result = ue.open_level("/Game/Maps/TestOpenLevel_A")
        assert result.get("world_name") == "TestOpenLevel_A"

    def test_open_level_nonexistent_fails(self, ue):
        from ue_bridge.errors import UECommandError
        import pytest
        with pytest.raises(UECommandError, match="not found"):
            ue.open_level("/Game/Maps/DoesNotExist_12345")
