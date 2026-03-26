"""Unit tests for bridge.py — parameter handling and default values."""

import pytest
from unittest.mock import patch
from typing import Optional

from ue_bridge import UEBridge, UECommandError
from ue_bridge.errors import UEConnectionError


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

    def test_raw_command_preserves_recoverable_and_data(self):
        ue, mock = make_bridge_with_mock()
        mock.send_command.return_value = {
            "success": False,
            "error": "temporary failure",
            "error_type": "temporary",
            "recoverable": False,
            "details": {"step": "compile"},
        }

        with pytest.raises(UECommandError) as exc_info:
            ue.raw_command("compile_blueprint", {"blueprint_name": "BP_Bad"})

        assert exc_info.value.recoverable is False
        assert exc_info.value.data["details"] == {"step": "compile"}


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

    def test_find_actors_returns_list(self):
        ue, mock = make_bridge_with_mock()
        mock.send_command.return_value = {
            "success": True,
            "actors": [{"name": "Wall_01"}],
        }

        result = ue.find_actors("Wall*")

        assert result == [{"name": "Wall_01"}]
        assert mock.send_command.call_args[0][0] == "find_actors_by_name"

    def test_spawn_blueprint_actor_location_as_list(self):
        ue, mock = make_bridge_with_mock()
        mock.send_command.return_value = {"success": True}

        ue.spawn_blueprint_actor("BP_Foo", "Foo_01", location=(1, 2, 3))

        params = mock.send_command.call_args[0][1]
        assert params["blueprint_name"] == "BP_Foo"
        assert params["actor_name"] == "Foo_01"
        assert params["location"] == [1, 2, 3]

    def test_set_component_property_preserves_value_shape(self):
        ue, mock = make_bridge_with_mock()
        mock.send_command.return_value = {"success": True}

        ue.set_component_property(
            "BP_Test",
            "ObstacleMesh",
            "RelativeScale3D",
            {"X": 2.0, "Y": 2.0, "Z": 1.0},
        )

        params = mock.send_command.call_args[0][1]
        assert params["property_value"] == {"X": 2.0, "Y": 2.0, "Z": 1.0}

    def test_set_static_mesh_properties_wrapper(self):
        ue, mock = make_bridge_with_mock()
        mock.send_command.return_value = {"success": True}

        ue.set_static_mesh_properties(
            "BP_Obstacle",
            "ObstacleMesh",
            static_mesh="/Engine/BasicShapes/Cube.Cube",
            mobility="Static",
            materials=["/Game/M_Test"],
        )

        assert mock.send_command.call_args[0] == (
            "set_static_mesh_properties",
            {
                "blueprint_name": "BP_Obstacle",
                "component_name": "ObstacleMesh",
                "static_mesh": "/Engine/BasicShapes/Cube.Cube",
                "mobility": "Static",
                "materials": ["/Game/M_Test"],
            },
        )

    def test_create_blueprint_optional_path(self):
        ue, mock = make_bridge_with_mock()
        mock.send_command.return_value = {"success": True}

        ue.create_blueprint("BP_Foo", parent_class="Character", path="/Game/Test")

        params = mock.send_command.call_args[0][1]
        assert params == {
            "name": "BP_Foo",
            "parent_class": "Character",
            "path": "/Game/Test",
        }

    def test_create_input_mapping_context_default_path(self):
        ue, mock = make_bridge_with_mock()
        mock.send_command.return_value = {"success": True}

        ue.create_input_mapping_context("IMC_Default")

        params = mock.send_command.call_args[0][1]
        assert params == {"name": "IMC_Default", "path": "/Game/Input"}

    def test_add_variable_optional_fields(self):
        ue, mock = make_bridge_with_mock()
        mock.send_command.return_value = {"success": True}

        ue.add_variable(
            "BP_Test",
            "Speed",
            "float",
            default_value=600,
            instance_editable=True,
            category="Movement",
        )

        params = mock.send_command.call_args[0][1]
        assert params == {
            "blueprint_name": "BP_Test",
            "variable_name": "Speed",
            "variable_type": "float",
            "default_value": 600,
            "is_instance_editable": True,
            "category": "Movement",
        }

    def test_disconnect_param_names(self):
        ue, mock = make_bridge_with_mock()
        mock.send_command.return_value = {"success": True}

        ue.disconnect("BP_Test", "node1", "execute")

        params = mock.send_command.call_args[0][1]
        assert params == {
            "blueprint_name": "BP_Test",
            "node_id": "node1",
            "pin_name": "execute",
        }

    def test_auto_layout_default_mode(self):
        ue, mock = make_bridge_with_mock()
        mock.send_command.return_value = {"success": True}

        ue.auto_layout("BP_Test")

        params = mock.send_command.call_args[0][1]
        assert params == {"blueprint_name": "BP_Test", "mode": "all"}

    def test_is_ready_uses_expected_command(self):
        ue, mock = make_bridge_with_mock()
        mock.send_command.return_value = {"success": True, "ready": True}

        result = ue.is_ready()

        assert result["ready"] is True
        assert mock.send_command.call_args[0] == ("is_ready", None)

    def test_get_editor_logs_sends_optional_filters(self):
        ue, mock = make_bridge_with_mock()
        mock.send_command.return_value = {"success": True, "lines": []}

        ue.get_editor_logs(count=25, category="LogTemp", min_verbosity="Warning")

        assert mock.send_command.call_args[0] == (
            "get_editor_logs",
            {"count": 25, "category": "LogTemp", "min_verbosity": "Warning"},
        )

    def test_get_unreal_logs_sends_filters(self):
        ue, mock = make_bridge_with_mock()
        mock.send_command.return_value = {"success": True, "content": ""}

        ue.get_unreal_logs(
            tail_lines=120,
            max_bytes=20480,
            include_meta=False,
            require_recent=True,
            recent_window_seconds=5.0,
            filter_contains="error",
            filter_category="LogBlueprint",
        )

        assert mock.send_command.call_args[0] == (
            "get_unreal_logs",
            {
                "tail_lines": 120,
                "max_bytes": 20480,
                "include_meta": False,
                "require_recent": True,
                "recent_window_seconds": 5.0,
                "filter_contains": "error",
                "filter_category": "LogBlueprint",
            },
        )


class TestWorkflowADiagnostics:
    def test_doctor_reports_ready_when_all_required_checks_pass(self):
        ue, _mock = make_bridge_with_mock()

        ue.ping = lambda: True
        ue.get_context = lambda: {"project_name": "Foo"}
        ue.is_ready = lambda: {"ready": True, "editor_valid": True}

        def fake_get_editor_logs(count: int = 100, category: Optional[str] = None, min_verbosity: Optional[str] = None):
            return {"total": 3, "capturing": True}

        def fake_get_unreal_logs(
            tail_lines: int = 200,
            max_bytes: int = 65536,
            include_meta: bool = True,
            require_recent: bool = False,
            recent_window_seconds: float = 2.0,
            filter_contains: Optional[str] = None,
            filter_category: Optional[str] = None,
        ):
            return {"cursor": "live:123", "linesReturned": 8, "truncated": False}

        ue.get_editor_logs = fake_get_editor_logs
        ue.get_unreal_logs = fake_get_unreal_logs

        result = ue.doctor()

        assert result["ok"] is True
        assert result["status"] == "ready"
        assert result["checks"]["ping"]["ok"] is True
        assert result["checks"]["context"]["ok"] is True
        assert result["checks"]["editor_ready"]["ok"] is True

    def test_doctor_returns_connection_error_without_raising(self):
        ue, _mock = make_bridge_with_mock()
        ue.ping = lambda: (_ for _ in ()).throw(UEConnectionError("cannot connect"))

        result = ue.doctor()

        assert result["ok"] is False
        assert result["status"] == "connection_error"
        assert result["checks"]["ping"]["ok"] is False
        assert "cannot connect" in result["checks"]["ping"]["error"]

    def test_doctor_marks_not_ready_when_editor_ready_is_false(self):
        ue, _mock = make_bridge_with_mock()

        ue.ping = lambda: True
        ue.get_context = lambda: {"project_name": "Foo"}
        ue.is_ready = lambda: {"ready": False, "editor_valid": True, "world_ready": False}

        def fake_get_editor_logs(count: int = 100, category: Optional[str] = None, min_verbosity: Optional[str] = None):
            return {"total": 1, "capturing": True}

        def fake_get_unreal_logs(
            tail_lines: int = 200,
            max_bytes: int = 65536,
            include_meta: bool = True,
            require_recent: bool = False,
            recent_window_seconds: float = 2.0,
            filter_contains: Optional[str] = None,
            filter_category: Optional[str] = None,
        ):
            return {"cursor": "live:12", "linesReturned": 4, "truncated": False}

        ue.get_editor_logs = fake_get_editor_logs
        ue.get_unreal_logs = fake_get_unreal_logs

        result = ue.doctor()

        assert result["ok"] is False
        assert result["status"] == "needs_attention"
        assert result["checks"]["editor_ready"]["ok"] is False

    def test_verify_installation_uses_doctor_required_checks(self):
        ue, _mock = make_bridge_with_mock()

        def fake_doctor(
            editor_log_count: int = 50,
            unreal_tail_lines: int = 80,
            require_recent_live_logs: bool = False,
        ):
            return {
            "ok": False,
            "checks": {
                "ping": {"ok": True},
                "context": {"ok": True},
                "editor_ready": {"ok": False},
            },
        }

        ue.doctor = fake_doctor

        result = ue.verify_installation()

        assert result["verified"] is False
        assert result["required_checks"] == {
            "ping": True,
            "context": True,
            "editor_ready": False,
        }
