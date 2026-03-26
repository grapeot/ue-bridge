"""Unit tests for bridge.py — parameter handling and default values."""

import pytest
from unittest.mock import MagicMock, patch

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.bridge import UEBridge
from src.errors import UECommandError


def make_bridge_with_mock():
    """Create a UEBridge with mocked connection."""
    with patch("src.bridge.Connection") as MockConn:
        mock_conn = MockConn.return_value
        mock_conn.send_command.return_value = {"success": True}
        ue = UEBridge(auto_connect=False)
        ue._conn = mock_conn
        return ue, mock_conn


class TestDefaultValues:
    """Verify that known pitfalls are fixed by default values."""

    def test_create_input_action_default_path(self):
        ue, mock = make_bridge_with_mock()
        mock.send_command.return_value = {"success": True, "name": "IA_Test", "path": "/Game/Input/Actions/IA_Test"}

        ue.create_input_action("IA_Test")

        call_args = mock.send_command.call_args
        assert call_args[0][0] == "create_input_action"
        params = call_args[0][1]
        assert params["path"] == "/Game/Input/Actions"

    def test_add_key_mapping_default_action_path(self):
        ue, mock = make_bridge_with_mock()
        mock.send_command.return_value = {"success": True}

        ue.add_key_mapping("IMC_Default", "IA_Test", "C")

        params = mock.send_command.call_args[0][1]
        assert params["action_path"] == "/Game/Input/Actions"

    def test_add_function_node_default_target(self):
        ue, mock = make_bridge_with_mock()
        mock.send_command.return_value = {"success": True, "node_id": "abc"}

        ue.add_function_node("BP_Test", "Crouch")

        params = mock.send_command.call_args[0][1]
        assert params["target"] == "self"

    def test_add_enhanced_input_action_default_path(self):
        ue, mock = make_bridge_with_mock()
        mock.send_command.return_value = {"success": True, "node_id": "abc"}

        ue.add_enhanced_input_action_node("BP_Test", "IA_Crouch")

        params = mock.send_command.call_args[0][1]
        assert params["action_path"] == "/Game/Input/Actions"


class TestErrorHandling:
    """Verify that errors are properly raised."""

    def test_raw_command_raises_on_failure(self):
        ue, mock = make_bridge_with_mock()
        mock.send_command.return_value = {
            "success": False,
            "error": "Blueprint not found",
            "error_type": "not_found",
        }

        with pytest.raises(UECommandError) as exc_info:
            ue.raw_command("compile_blueprint", {"blueprint_name": "BP_Missing"})

        assert "Blueprint not found" in str(exc_info.value)
        assert exc_info.value.error_type == "not_found"

    def test_ping_returns_bool(self):
        ue, mock = make_bridge_with_mock()
        mock.send_command.return_value = {"success": True, "pong": True}
        assert ue.ping() is True

    def test_ping_false_when_no_pong(self):
        ue, mock = make_bridge_with_mock()
        mock.send_command.return_value = {"success": True}
        assert ue.ping() is False


class TestParameterPassing:
    """Verify parameters are correctly assembled."""

    def test_spawn_actor_location_as_list(self):
        ue, mock = make_bridge_with_mock()
        mock.send_command.return_value = {"success": True}

        ue.spawn_actor("StaticMeshActor", "Wall_01", location=(100, 200, 0))

        params = mock.send_command.call_args[0][1]
        assert params["location"] == [100, 200, 0]
        assert params["type"] == "StaticMeshActor"

    def test_connect_nodes_param_names(self):
        ue, mock = make_bridge_with_mock()
        mock.send_command.return_value = {"success": True}

        ue.connect("node1", "Started", "node2", "execute")

        params = mock.send_command.call_args[0][1]
        assert params["source_node_id"] == "node1"
        assert params["source_pin"] == "Started"
        assert params["target_node_id"] == "node2"
        assert params["target_pin"] == "execute"

    def test_optional_position_not_sent_when_none(self):
        ue, mock = make_bridge_with_mock()
        mock.send_command.return_value = {"success": True, "node_id": "abc"}

        ue.add_function_node("BP_Test", "Crouch")

        params = mock.send_command.call_args[0][1]
        assert "x" not in params
        assert "y" not in params

    def test_optional_position_sent_when_provided(self):
        ue, mock = make_bridge_with_mock()
        mock.send_command.return_value = {"success": True, "node_id": "abc"}

        ue.add_function_node("BP_Test", "Crouch", position=(100, 200))

        params = mock.send_command.call_args[0][1]
        assert params["x"] == 100
        assert params["y"] == 200

    def test_list_assets_returns_list(self):
        ue, mock = make_bridge_with_mock()
        mock.send_command.return_value = {
            "success": True,
            "assets": [{"name": "a"}, {"name": "b"}],
        }

        result = ue.list_assets("/Game/")
        assert len(result) == 2
        assert result[0]["name"] == "a"

    def test_get_pins_returns_list(self):
        ue, mock = make_bridge_with_mock()
        mock.send_command.return_value = {
            "success": True,
            "pins": [{"name": "execute", "direction": "Input"}],
        }

        result = ue.get_pins("BP_Test", "node123")
        assert len(result) == 1
        assert result[0]["name"] == "execute"
