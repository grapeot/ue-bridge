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

    def test_start_pie_default_mode(self):
        ue, mock = make_bridge_with_mock()
        mock.send_command.return_value = {
            "success": True, "mode": "SelectedViewport",
            "message": "PIE session requested", "is_async": True,
        }

        result = ue.start_pie()

        assert mock.send_command.call_args[0] == ("start_pie", {"mode": "SelectedViewport"})
        assert result["mode"] == "SelectedViewport"
        assert result["is_async"] is True

    def test_start_pie_simulate_mode(self):
        ue, mock = make_bridge_with_mock()
        mock.send_command.return_value = {
            "success": True, "mode": "Simulate",
            "message": "PIE session requested", "is_async": True,
        }

        ue.start_pie(mode="Simulate")

        assert mock.send_command.call_args[0][1]["mode"] == "Simulate"

    def test_stop_pie_sends_correct_command(self):
        ue, mock = make_bridge_with_mock()
        mock.send_command.return_value = {
            "success": True, "state": "stop_requested",
            "message": "PIE stop requested",
        }

        result = ue.stop_pie()

        assert mock.send_command.call_args[0] == ("stop_pie", None)
        assert result["state"] == "stop_requested"

    def test_get_pie_state_running(self):
        ue, mock = make_bridge_with_mock()
        mock.send_command.return_value = {
            "success": True, "state": "Running",
            "world_name": "UEDPIE_0_TestMap",
            "is_paused": False, "is_simulating": False,
        }

        result = ue.get_pie_state()

        assert mock.send_command.call_args[0] == ("get_pie_state", None)
        assert result["state"] == "Running"
        assert result["is_paused"] is False

    def test_get_pie_state_stopped(self):
        ue, mock = make_bridge_with_mock()
        mock.send_command.return_value = {
            "success": True, "state": "Stopped",
        }

        result = ue.get_pie_state()

        assert result["state"] == "Stopped"

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


class TestUMGWidgetWrappers:
    """Verify UMG Widget wrappers assemble correct parameters."""

    def test_create_widget_blueprint(self):
        ue, mock = make_bridge_with_mock()
        mock.send_command.return_value = {"success": True}

        ue.create_widget_blueprint("WBP_HUD", path="/Game/UI/")

        assert mock.send_command.call_args[0] == (
            "create_umg_widget_blueprint",
            {"widget_name": "WBP_HUD", "path": "/Game/UI/"},
        )

    def test_delete_widget_blueprint(self):
        ue, mock = make_bridge_with_mock()
        mock.send_command.return_value = {"success": True}

        ue.delete_widget_blueprint("WBP_HUD")

        assert mock.send_command.call_args[0] == (
            "delete_umg_widget_blueprint",
            {"widget_name": "WBP_HUD"},
        )

    def test_add_text_block_minimal(self):
        ue, mock = make_bridge_with_mock()
        mock.send_command.return_value = {"success": True}

        ue.add_text_block("WBP_HUD", "ScoreText")

        params = mock.send_command.call_args[0][1]
        assert params["widget_name"] == "WBP_HUD"
        assert params["text_block_name"] == "ScoreText"
        assert "text" not in params

    def test_add_text_block_with_options(self):
        ue, mock = make_bridge_with_mock()
        mock.send_command.return_value = {"success": True}

        ue.add_text_block("WBP_HUD", "ScoreText", text="Score: 0", position=(10, 20))

        params = mock.send_command.call_args[0][1]
        assert params["text"] == "Score: 0"
        assert params["position"] == [10, 20]

    def test_add_progress_bar_with_color(self):
        ue, mock = make_bridge_with_mock()
        mock.send_command.return_value = {"success": True}

        ue.add_progress_bar("WBP_HUD", "BossHP", percent=1.0, color=(1, 0, 0, 1))

        params = mock.send_command.call_args[0][1]
        assert params == {
            "widget_name": "WBP_HUD",
            "progress_bar_name": "BossHP",
            "percent": 1.0,
            "color": [1, 0, 0, 1],
        }

    def test_add_image(self):
        ue, mock = make_bridge_with_mock()
        mock.send_command.return_value = {"success": True}

        ue.add_image("WBP_HUD", "LifeIcon", position=(5, 5), size=(32, 32))

        params = mock.send_command.call_args[0][1]
        assert params["image_name"] == "LifeIcon"
        assert params["position"] == [5, 5]
        assert params["size"] == [32, 32]

    def test_add_canvas_panel(self):
        ue, mock = make_bridge_with_mock()
        mock.send_command.return_value = {"success": True}

        ue.add_canvas_panel("WBP_HUD", "MainCanvas")

        assert mock.send_command.call_args[0] == (
            "add_canvas_panel_to_widget",
            {"widget_name": "WBP_HUD", "canvas_panel_name": "MainCanvas"},
        )

    def test_add_vertical_box(self):
        ue, mock = make_bridge_with_mock()
        mock.send_command.return_value = {"success": True}

        ue.add_vertical_box("WBP_HUD", "InfoBox")

        assert mock.send_command.call_args[0] == (
            "add_vertical_box_to_widget",
            {"widget_name": "WBP_HUD", "vertical_box_name": "InfoBox"},
        )

    def test_set_widget_text_with_font_size(self):
        ue, mock = make_bridge_with_mock()
        mock.send_command.return_value = {"success": True}

        ue.set_widget_text("WBP_HUD", "ScoreText", "Score: 1000", font_size=24)

        params = mock.send_command.call_args[0][1]
        assert params == {
            "widget_name": "WBP_HUD",
            "target": "ScoreText",
            "text": "Score: 1000",
            "font_size": 24,
        }

    def test_set_widget_properties_passes_kwargs(self):
        ue, mock = make_bridge_with_mock()
        mock.send_command.return_value = {"success": True}

        ue.set_widget_properties("WBP_HUD", "ScoreText",
                                 position=[100, 50], visibility="Visible")

        params = mock.send_command.call_args[0][1]
        assert params["widget_name"] == "WBP_HUD"
        assert params["target"] == "ScoreText"
        assert params["position"] == [100, 50]
        assert params["visibility"] == "Visible"

    def test_set_text_block_binding(self):
        ue, mock = make_bridge_with_mock()
        mock.send_command.return_value = {"success": True}

        ue.set_text_block_binding("WBP_HUD", "ScoreText", "ScoreVar")

        assert mock.send_command.call_args[0] == (
            "set_text_block_binding",
            {
                "widget_name": "WBP_HUD",
                "text_block_name": "ScoreText",
                "binding_property": "ScoreVar",
            },
        )

    def test_add_widget_to_viewport(self):
        ue, mock = make_bridge_with_mock()
        mock.send_command.return_value = {"success": True, "class_path": "/Game/UI/WBP_HUD.WBP_HUD_C"}

        result = ue.add_widget_to_viewport("WBP_HUD", z_order=10)

        params = mock.send_command.call_args[0][1]
        assert params == {"widget_name": "WBP_HUD", "z_order": 10}
        assert result["class_path"] == "/Game/UI/WBP_HUD.WBP_HUD_C"

    def test_list_widget_components(self):
        ue, mock = make_bridge_with_mock()
        mock.send_command.return_value = {"success": True, "components": [{"name": "ScoreText"}]}

        result = ue.list_widget_components("WBP_HUD")

        assert mock.send_command.call_args[0] == (
            "list_widget_components", {"widget_name": "WBP_HUD"},
        )

    def test_get_widget_tree(self):
        ue, mock = make_bridge_with_mock()
        mock.send_command.return_value = {"success": True, "tree": {}}

        ue.get_widget_tree("WBP_HUD")

        assert mock.send_command.call_args[0] == (
            "get_widget_tree", {"widget_name": "WBP_HUD"},
        )

    def test_reparent_widgets(self):
        ue, mock = make_bridge_with_mock()
        mock.send_command.return_value = {"success": True}

        ue.reparent_widgets("WBP_HUD", "MainCanvas", ["ScoreText", "BossHP"])

        assert mock.send_command.call_args[0] == (
            "reparent_widgets",
            {
                "widget_name": "WBP_HUD",
                "target_container_name": "MainCanvas",
                "children": ["ScoreText", "BossHP"],
            },
        )

    def test_add_generic_widget(self):
        ue, mock = make_bridge_with_mock()
        mock.send_command.return_value = {"success": True}

        ue.add_generic_widget("WBP_HUD", "ScrollBox", "MyScrollBox")

        assert mock.send_command.call_args[0] == (
            "add_generic_widget_to_widget",
            {
                "widget_name": "WBP_HUD",
                "component_class": "ScrollBox",
                "component_name": "MyScrollBox",
            },
        )


class TestParamNameMatching:
    """Verify Python param names match C++ expectations exactly.

    These tests catch the class of bug where bridge.py sends a different
    param key than the C++ action expects (e.g., "name" vs "material_name").
    """

    def test_create_material_sends_material_name(self):
        ue, mock = make_bridge_with_mock()
        ue.create_material("M_Test")
        params = mock.send_command.call_args[0][1]
        assert "material_name" in params
        assert params["material_name"] == "M_Test"
        assert "name" not in params

    def test_create_colored_material_sends_material_name(self):
        ue, mock = make_bridge_with_mock()
        ue.create_colored_material("M_Red", color=(1, 0, 0, 1))
        params = mock.send_command.call_args[0][1]
        assert "material_name" in params
        assert params["material_name"] == "M_Red"
        assert "name" not in params
        assert params["color"] == [1, 0, 0, 1]

    def test_create_colored_material_with_path(self):
        ue, mock = make_bridge_with_mock()
        ue.create_colored_material("M_Blue", color=(0, 0, 1, 1), path="/Game/Mats")
        params = mock.send_command.call_args[0][1]
        assert params["material_name"] == "M_Blue"
        assert params["path"] == "/Game/Mats"

    def test_add_canvas_panel_sends_canvas_panel_name(self):
        ue, mock = make_bridge_with_mock()
        ue.add_canvas_panel("WBP_HUD", "MainCanvas")
        params = mock.send_command.call_args[0][1]
        assert "canvas_panel_name" in params
        assert params["canvas_panel_name"] == "MainCanvas"
        assert "canvas_name" not in params

    def test_reparent_widgets_sends_target_container_name(self):
        ue, mock = make_bridge_with_mock()
        ue.reparent_widgets("WBP_HUD", "MainCanvas", ["Text1", "Text2"])
        params = mock.send_command.call_args[0][1]
        assert "target_container_name" in params
        assert params["target_container_name"] == "MainCanvas"
        assert "target_parent" not in params
        assert params["children"] == ["Text1", "Text2"]
