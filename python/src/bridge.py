"""
UEBridge — Main API class for Unreal Editor automation.

Usage:
    from ue_bridge import UEBridge

    ue = UEBridge()
    ue.ping()
    ue.save_all()
    ue.compile("BP_MyCharacter")
"""

from __future__ import annotations

import logging
from typing import Any

from .connection import Connection
from .errors import UECommandError, UEConnectionError

logger = logging.getLogger(__name__)


class UEBridge:
    """Python interface to Unreal Editor via TCP."""

    def __init__(self, host: str = "127.0.0.1", port: int = 55558,
                 timeout: float = 30.0, auto_connect: bool = True):
        self._conn = Connection(host=host, port=port, timeout=timeout)
        if auto_connect:
            self._conn.connect()

    def close(self) -> None:
        self._conn.disconnect()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
        return False

    # -------------------------------------------------------------------------
    # Core: raw command + result extraction
    # -------------------------------------------------------------------------

    def raw_command(self, command_type: str,
                    params: dict[str, Any] | None = None) -> dict:
        """Send any command and return raw response data. Raises on failure."""
        response = self._conn.send_command(command_type, params)
        if not response.get("success"):
            error_msg = response.get("error", "Unknown error")
            error_type = response.get("error_type", "unknown")
            raise UECommandError(
                error_msg, error_type=error_type,
                recoverable=response.get("recoverable", True),
                data={k: v for k, v in response.items()
                      if k not in ("success", "error", "error_type", "recoverable")}
            )
        return {k: v for k, v in response.items() if k != "success"}

    def _cmd(self, command_type: str,
             params: dict[str, Any] | None = None) -> dict:
        """Alias for raw_command (internal use)."""
        return self.raw_command(command_type, params)

    # -------------------------------------------------------------------------
    # Connection
    # -------------------------------------------------------------------------

    def ping(self) -> bool:
        data = self._cmd("ping")
        return data.get("pong", False)

    def get_context(self) -> dict:
        return self._cmd("get_context")

    def is_ready(self) -> dict:
        return self._cmd("is_ready")

    def save_all(self) -> dict:
        return self._cmd("save_all")

    def get_editor_logs(
        self,
        count: int = 100,
        category: str | None = None,
        min_verbosity: str | None = None,
    ) -> dict:
        params: dict[str, Any] = {"count": count}
        if category:
            params["category"] = category
        if min_verbosity:
            params["min_verbosity"] = min_verbosity
        return self._cmd("get_editor_logs", params)

    def get_unreal_logs(
        self,
        tail_lines: int = 200,
        max_bytes: int = 65536,
        include_meta: bool = True,
        require_recent: bool = False,
        recent_window_seconds: float = 2.0,
        filter_contains: str | None = None,
        filter_category: str | None = None,
    ) -> dict:
        params: dict[str, Any] = {
            "tail_lines": tail_lines,
            "max_bytes": max_bytes,
            "include_meta": include_meta,
            "require_recent": require_recent,
            "recent_window_seconds": recent_window_seconds,
        }
        if filter_contains:
            params["filter_contains"] = filter_contains
        if filter_category:
            params["filter_category"] = filter_category
        return self._cmd("get_unreal_logs", params)

    def doctor(
        self,
        editor_log_count: int = 50,
        unreal_tail_lines: int = 80,
        require_recent_live_logs: bool = False,
    ) -> dict:
        report: dict[str, Any] = {
            "ok": False,
            "status": "starting",
            "summary": [],
            "checks": {},
        }

        try:
            pong = self.ping()
            report["checks"]["ping"] = {"ok": pong, "pong": pong}
            if not pong:
                report["status"] = "connection_unhealthy"
                report["summary"].append("ping returned false")
                return report
        except UEConnectionError as exc:
            report["status"] = "connection_error"
            report["summary"].append(str(exc))
            report["checks"]["ping"] = {"ok": False, "error": str(exc)}
            return report

        try:
            context = self.get_context()
            report["checks"]["context"] = {"ok": True, "data": context}
        except (UEConnectionError, UECommandError) as exc:
            report["checks"]["context"] = {"ok": False, "error": str(exc)}
            report["summary"].append(f"context unavailable: {exc}")

        try:
            ready = self.is_ready()
            ready_ok = bool(ready.get("ready", False))
            report["checks"]["editor_ready"] = {"ok": ready_ok, "data": ready}
            if not ready_ok:
                report["summary"].append("editor is reachable but not fully ready")
        except (UEConnectionError, UECommandError) as exc:
            report["checks"]["editor_ready"] = {"ok": False, "error": str(exc)}
            report["summary"].append(f"editor readiness check failed: {exc}")

        try:
            editor_logs = self.get_editor_logs(count=editor_log_count)
            report["checks"]["editor_logs"] = {
                "ok": True,
                "total": editor_logs.get("total"),
                "capturing": editor_logs.get("capturing"),
            }
        except UECommandError as exc:
            report["checks"]["editor_logs"] = {
                "ok": False,
                "error": str(exc),
                "error_type": exc.error_type,
            }
            report["summary"].append(f"editor logs unavailable: {exc}")

        try:
            unreal_logs = self.get_unreal_logs(
                tail_lines=unreal_tail_lines,
                require_recent=require_recent_live_logs,
            )
            report["checks"]["unreal_logs"] = {
                "ok": True,
                "cursor": unreal_logs.get("cursor"),
                "linesReturned": unreal_logs.get("linesReturned"),
                "truncated": unreal_logs.get("truncated"),
            }
        except UECommandError as exc:
            report["checks"]["unreal_logs"] = {
                "ok": False,
                "error": str(exc),
                "error_type": exc.error_type,
            }
            report["summary"].append(f"live unreal logs unavailable: {exc}")

        required_checks = [
            report["checks"].get("ping", {}).get("ok", False),
            report["checks"].get("context", {}).get("ok", False),
            report["checks"].get("editor_ready", {}).get("ok", False),
        ]
        report["ok"] = all(required_checks)
        report["status"] = "ready" if report["ok"] else "needs_attention"
        if report["ok"] and not report["summary"]:
            report["summary"].append("editor bridge is reachable and ready")
        return report

    def verify_installation(self) -> dict:
        doctor_report = self.doctor(require_recent_live_logs=False)
        required = {
            "ping": doctor_report["checks"].get("ping", {}).get("ok", False),
            "context": doctor_report["checks"].get("context", {}).get("ok", False),
            "editor_ready": doctor_report["checks"].get("editor_ready", {}).get("ok", False),
        }
        return {
            "verified": all(required.values()),
            "required_checks": required,
            "doctor": doctor_report,
        }

    # -------------------------------------------------------------------------
    # Assets
    # -------------------------------------------------------------------------

    def list_assets(self, path: str = "/Game/",
                    class_filter: str | None = None,
                    name_filter: str | None = None) -> list[dict]:
        params: dict[str, Any] = {"path": path}
        if class_filter:
            params["class_filter"] = class_filter
        if name_filter:
            params["name_filter"] = name_filter
        data = self._cmd("list_assets", params)
        return data.get("assets", [])

    # -------------------------------------------------------------------------
    # Scene / Actors
    # -------------------------------------------------------------------------

    def get_actors(self) -> list[dict]:
        data = self._cmd("get_actors_in_level")
        return data.get("actors", [])

    def find_actors(self, pattern: str) -> list[dict]:
        data = self._cmd("find_actors_by_name", {"pattern": pattern})
        return data.get("actors", [])

    def spawn_actor(self, actor_type: str, name: str,
                    location: tuple[float, float, float] = (0, 0, 0),
                    rotation: tuple[float, float, float] = (0, 0, 0),
                    scale: tuple[float, float, float] = (1, 1, 1)) -> dict:
        return self._cmd("spawn_actor", {
            "type": actor_type,
            "name": name,
            "location": list(location),
            "rotation": list(rotation),
            "scale": list(scale),
        })

    def spawn_blueprint_actor(self, blueprint_name: str, name: str,
                              location: tuple[float, float, float] = (0, 0, 0),
                              rotation: tuple[float, float, float] = (0, 0, 0),
                              scale: tuple[float, float, float] = (1, 1, 1)) -> dict:
        return self._cmd("spawn_blueprint_actor", {
            "blueprint_name": blueprint_name,
            "actor_name": name,
            "location": list(location),
            "rotation": list(rotation),
            "scale": list(scale),
        })

    def delete_actor(self, name: str) -> dict:
        return self._cmd("delete_actor", {"name": name})

    def set_actor_transform(self, name: str,
                            location: tuple[float, float, float] | None = None,
                            rotation: tuple[float, float, float] | None = None,
                            scale: tuple[float, float, float] | None = None) -> dict:
        params: dict[str, Any] = {"name": name}
        if location is not None:
            params["location"] = list(location)
        if rotation is not None:
            params["rotation"] = list(rotation)
        if scale is not None:
            params["scale"] = list(scale)
        return self._cmd("set_actor_transform", params)

    def get_actor_properties(self, name: str) -> dict:
        return self._cmd("get_actor_properties", {"name": name})

    def set_actor_property(self, name: str, property_name: str,
                           property_value: Any) -> dict:
        return self._cmd("set_actor_property", {
            "name": name,
            "property_name": property_name,
            "property_value": property_value,
        })

    # -------------------------------------------------------------------------
    # Viewport
    # -------------------------------------------------------------------------

    def focus_viewport(self, target: str | None = None,
                       location: tuple[float, float, float] | None = None) -> dict:
        params: dict[str, Any] = {}
        if target:
            params["target"] = target
        if location:
            params["location"] = list(location)
        return self._cmd("focus_viewport", params)

    def get_viewport_transform(self) -> dict:
        return self._cmd("get_viewport_transform")

    def set_viewport_transform(self,
                               location: tuple[float, float, float] | None = None,
                               rotation: tuple[float, float, float] | None = None) -> dict:
        params: dict[str, Any] = {}
        if location:
            params["location"] = list(location)
        if rotation:
            params["rotation"] = list(rotation)
        return self._cmd("set_viewport_transform", params)

    # -------------------------------------------------------------------------
    # Blueprint — Properties
    # -------------------------------------------------------------------------

    def create_blueprint(self, name: str, parent_class: str = "Actor",
                         path: str | None = None) -> dict:
        params: dict[str, Any] = {"name": name, "parent_class": parent_class}
        if path:
            params["path"] = path
        return self._cmd("create_blueprint", params)

    def get_blueprint_summary(self, blueprint_name: str) -> dict:
        return self._cmd("get_blueprint_summary", {"blueprint_name": blueprint_name})

    def compile(self, blueprint_name: str) -> dict:
        return self._cmd("compile_blueprint", {"blueprint_name": blueprint_name})

    def set_blueprint_property(self, blueprint_name: str,
                               property_name: str, property_value: Any) -> dict:
        return self._cmd("set_blueprint_property", {
            "blueprint_name": blueprint_name,
            "property_name": property_name,
            "property_value": property_value,
        })

    def add_component(self, blueprint_name: str, component_type: str,
                      component_name: str | None = None) -> dict:
        params: dict[str, Any] = {
            "blueprint_name": blueprint_name,
            "component_type": component_type,
        }
        if component_name:
            params["component_name"] = component_name
        return self._cmd("add_component_to_blueprint", params)

    def set_component_property(self, blueprint_name: str, component_name: str,
                               property_name: str, property_value: Any) -> dict:
        return self._cmd("set_component_property", {
            "blueprint_name": blueprint_name,
            "component_name": component_name,
            "property_name": property_name,
            "property_value": property_value,
        })

    def set_static_mesh_properties(self, blueprint_name: str, component_name: str,
                                   static_mesh: str | None = None,
                                   mobility: str | None = None,
                                   materials: list[str] | None = None) -> dict:
        params: dict[str, Any] = {
            "blueprint_name": blueprint_name,
            "component_name": component_name,
        }
        if static_mesh is not None:
            params["static_mesh"] = static_mesh
        if mobility is not None:
            params["mobility"] = mobility
        if materials is not None:
            params["materials"] = materials
        return self._cmd("set_static_mesh_properties", params)

    def set_blueprint_parent_class(self, blueprint_name: str,
                                    parent_class: str) -> dict:
        return self._cmd("set_blueprint_parent_class", {
            "blueprint_name": blueprint_name,
            "parent_class": parent_class,
        })

    # -------------------------------------------------------------------------
    # Blueprint — Nodes
    # -------------------------------------------------------------------------

    def add_enhanced_input_action_node(
            self, blueprint_name: str, action_name: str,
            action_path: str = "/Game/Input/Actions",
            position: tuple[int, int] | None = None) -> str:
        """Add Enhanced Input Action event node. Returns node_id."""
        params: dict[str, Any] = {
            "blueprint_name": blueprint_name,
            "action_name": action_name,
            "action_path": action_path,
        }
        if position:
            params["x"], params["y"] = position
        data = self._cmd("add_enhanced_input_action_node", params)
        return data["node_id"]

    def add_function_node(self, blueprint_name: str, function_name: str,
                          target: str = "self",
                          position: tuple[int, int] | None = None) -> str:
        """Add function call node. Returns node_id."""
        params: dict[str, Any] = {
            "blueprint_name": blueprint_name,
            "function_name": function_name,
            "target": target,
        }
        if position:
            params["x"], params["y"] = position
        data = self._cmd("add_blueprint_function_node", params)
        return data["node_id"]

    def add_event_node(self, blueprint_name: str, event_name: str,
                       position: tuple[int, int] | None = None) -> str:
        """Add event node (BeginPlay, Tick, etc). Returns node_id."""
        params: dict[str, Any] = {
            "blueprint_name": blueprint_name,
            "event_name": event_name,
        }
        if position:
            params["x"], params["y"] = position
        data = self._cmd("add_blueprint_event_node", params)
        return data["node_id"]

    def add_custom_event(self, blueprint_name: str, event_name: str,
                         position: tuple[int, int] | None = None) -> str:
        """Add custom event. Returns node_id."""
        params: dict[str, Any] = {
            "blueprint_name": blueprint_name,
            "event_name": event_name,
        }
        if position:
            params["x"], params["y"] = position
        data = self._cmd("add_blueprint_custom_event", params)
        return data["node_id"]

    def add_variable(self, blueprint_name: str, variable_name: str,
                     variable_type: str, default_value: Any = None,
                     instance_editable: bool = False,
                     category: str | None = None) -> dict:
        params: dict[str, Any] = {
            "blueprint_name": blueprint_name,
            "variable_name": variable_name,
            "variable_type": variable_type,
        }
        if default_value is not None:
            params["default_value"] = default_value
        if instance_editable:
            params["is_instance_editable"] = True
        if category:
            params["category"] = category
        return self._cmd("add_blueprint_variable", params)

    def add_variable_get(self, blueprint_name: str, variable_name: str,
                         position: tuple[int, int] | None = None) -> str:
        params: dict[str, Any] = {
            "blueprint_name": blueprint_name,
            "variable_name": variable_name,
        }
        if position:
            params["x"], params["y"] = position
        data = self._cmd("add_blueprint_variable_get", params)
        return data["node_id"]

    def add_variable_set(self, blueprint_name: str, variable_name: str,
                         position: tuple[int, int] | None = None) -> str:
        params: dict[str, Any] = {
            "blueprint_name": blueprint_name,
            "variable_name": variable_name,
        }
        if position:
            params["x"], params["y"] = position
        data = self._cmd("add_blueprint_variable_set", params)
        return data["node_id"]

    def set_variable_default(self, blueprint_name: str, variable_name: str,
                             default_value: Any) -> dict:
        return self._cmd("set_blueprint_variable_default", {
            "blueprint_name": blueprint_name,
            "variable_name": variable_name,
            "default_value": default_value,
        })

    def add_branch_node(self, blueprint_name: str,
                        position: tuple[int, int] | None = None) -> str:
        params: dict[str, Any] = {"blueprint_name": blueprint_name}
        if position:
            params["x"], params["y"] = position
        data = self._cmd("add_blueprint_branch_node", params)
        return data["node_id"]

    def add_self_reference(self, blueprint_name: str,
                           position: tuple[int, int] | None = None) -> str:
        params: dict[str, Any] = {"blueprint_name": blueprint_name}
        if position:
            params["x"], params["y"] = position
        data = self._cmd("add_blueprint_self_reference", params)
        return data["node_id"]

    def add_cast_node(self, blueprint_name: str, cast_to: str,
                      position: tuple[int, int] | None = None) -> str:
        params: dict[str, Any] = {
            "blueprint_name": blueprint_name,
            "cast_to": cast_to,
        }
        if position:
            params["x"], params["y"] = position
        data = self._cmd("add_blueprint_cast_node", params)
        return data["node_id"]

    # -------------------------------------------------------------------------
    # Blueprint — Graph operations
    # -------------------------------------------------------------------------

    def connect(self, source_node_id: str, source_pin: str,
                target_node_id: str, target_pin: str,
                blueprint_name: str | None = None) -> dict:
        """Connect two blueprint nodes."""
        params: dict[str, Any] = {
            "source_node_id": source_node_id,
            "source_pin": source_pin,
            "target_node_id": target_node_id,
            "target_pin": target_pin,
        }
        if blueprint_name:
            params["blueprint_name"] = blueprint_name
        return self._cmd("connect_blueprint_nodes", params)

    def disconnect(self, blueprint_name: str, node_id: str,
                   pin_name: str) -> dict:
        return self._cmd("disconnect_blueprint_pin", {
            "blueprint_name": blueprint_name,
            "node_id": node_id,
            "pin_name": pin_name,
        })

    def get_pins(self, blueprint_name: str, node_id: str) -> list[dict]:
        data = self._cmd("get_node_pins", {
            "blueprint_name": blueprint_name,
            "node_id": node_id,
        })
        return data.get("pins", [])

    def set_pin_default(self, blueprint_name: str, node_id: str,
                        pin_name: str, default_value: str) -> dict:
        return self._cmd("set_node_pin_default", {
            "blueprint_name": blueprint_name,
            "node_id": node_id,
            "pin_name": pin_name,
            "default_value": default_value,
        })

    def find_nodes(self, blueprint_name: str,
                   query: str | None = None) -> list[dict]:
        params: dict[str, Any] = {"blueprint_name": blueprint_name}
        if query:
            params["query"] = query
        data = self._cmd("find_blueprint_nodes", params)
        return data.get("nodes", [])

    def delete_node(self, blueprint_name: str, node_id: str) -> dict:
        return self._cmd("delete_blueprint_node", {
            "blueprint_name": blueprint_name,
            "node_id": node_id,
        })

    def move_node(self, blueprint_name: str, node_id: str,
                  x: int, y: int) -> dict:
        return self._cmd("move_node", {
            "blueprint_name": blueprint_name,
            "node_id": node_id,
            "x": x, "y": y,
        })

    # -------------------------------------------------------------------------
    # Input System
    # -------------------------------------------------------------------------

    def create_input_action(self, name: str, value_type: str = "Digital",
                            path: str = "/Game/Input/Actions",
                            description: str | None = None) -> dict:
        params: dict[str, Any] = {
            "name": name,
            "value_type": value_type,
            "path": path,
        }
        if description:
            params["description"] = description
        return self._cmd("create_input_action", params)

    def create_input_mapping_context(self, name: str,
                                     path: str = "/Game/Input") -> dict:
        return self._cmd("create_input_mapping_context", {
            "name": name,
            "path": path,
        })

    def add_key_mapping(self, context_name: str, action_name: str,
                        key: str,
                        action_path: str = "/Game/Input/Actions",
                        context_path: str | None = None) -> dict:
        params: dict[str, Any] = {
            "context_name": context_name,
            "action_name": action_name,
            "key": key,
            "action_path": action_path,
        }
        if context_path:
            params["context_path"] = context_path
        return self._cmd("add_key_mapping_to_context", params)

    # -------------------------------------------------------------------------
    # Materials
    # -------------------------------------------------------------------------

    def create_material(self, name: str, path: str | None = None) -> dict:
        params: dict[str, Any] = {"material_name": name}
        if path:
            params["path"] = path
        return self._cmd("create_material", params)

    def create_colored_material(self, name: str,
                                color: tuple[float, float, float, float] = (1, 1, 1, 1),
                                path: str | None = None) -> dict:
        params: dict[str, Any] = {"material_name": name, "color": list(color)}
        if path:
            params["path"] = path
        return self._cmd("create_colored_material", params)

    def compile_material(self, material_name: str) -> dict:
        return self._cmd("compile_material", {"material_name": material_name})

    def create_material_instance(self, name: str, parent: str,
                                 path: str | None = None) -> dict:
        params: dict[str, Any] = {"name": name, "parent": parent}
        if path:
            params["path"] = path
        return self._cmd("create_material_instance", params)

    # -------------------------------------------------------------------------
    # Layout
    # -------------------------------------------------------------------------

    def auto_layout(self, blueprint_name: str,
                    mode: str = "all") -> dict:
        return self._cmd("auto_layout_selected", {
            "blueprint_name": blueprint_name,
            "mode": mode,
        })

    # -------------------------------------------------------------------------
    # Level / Map
    # -------------------------------------------------------------------------

    def take_screenshot(self, output_path: str) -> dict:
        """Capture the active viewport (PIE or editor) and save as PNG."""
        return self._cmd("take_screenshot", {"output_path": output_path})

    def new_level(self, level_name: str = "NewMap",
                  path: str = "/Game/Maps",
                  template: str = "Empty") -> dict:
        """Create and open a new empty level."""
        return self._cmd("new_level", {
            "level_name": level_name,
            "path": path,
            "template": template,
        })

    def open_level(self, level_path: str) -> dict:
        """Open an existing level in the editor.

        Args:
            level_path: Asset path of the level (e.g. "/Game/Maps/CardShowcase").

        Returns:
            dict with level_path, filename, world_name fields.
        """
        return self._cmd("open_level", {"level_path": level_path})

    # -------------------------------------------------------------------------
    # PIE (Play In Editor)
    # -------------------------------------------------------------------------

    def start_pie(self, mode: str = "SelectedViewport") -> dict:
        """Start a Play In Editor session.

        Args:
            mode: "SelectedViewport" (default), "NewWindow", or "Simulate".

        Returns:
            dict with mode, message, is_async fields.
            The session starts asynchronously; poll get_pie_state() to confirm.
        """
        return self._cmd("start_pie", {"mode": mode})

    def stop_pie(self) -> dict:
        """Stop the current PIE session."""
        return self._cmd("stop_pie")

    def get_pie_state(self) -> dict:
        """Query current PIE session state.

        Returns:
            dict with 'state' ("Running" or "Stopped") and, when running:
            world_name, is_paused, is_simulating, engine_time,
            is_play_session_in_progress.
        """
        return self._cmd("get_pie_state")

    # -------------------------------------------------------------------------
    # UMG Widgets
    # -------------------------------------------------------------------------

    def create_widget_blueprint(self, widget_name: str,
                                path: str = "/Game/UI/") -> dict:
        params: dict[str, Any] = {"widget_name": widget_name}
        if path:
            params["path"] = path
        return self._cmd("create_umg_widget_blueprint", params)

    def delete_widget_blueprint(self, widget_name: str) -> dict:
        return self._cmd("delete_umg_widget_blueprint", {"widget_name": widget_name})

    def add_text_block(self, widget_name: str, text_block_name: str,
                       text: str | None = None,
                       position: tuple[float, float] | None = None) -> dict:
        params: dict[str, Any] = {
            "widget_name": widget_name,
            "text_block_name": text_block_name,
        }
        if text is not None:
            params["text"] = text
        if position is not None:
            params["position"] = list(position)
        return self._cmd("add_text_block_to_widget", params)

    def add_progress_bar(self, widget_name: str, progress_bar_name: str,
                         percent: float | None = None,
                         color: tuple[float, float, float, float] | None = None,
                         position: tuple[float, float] | None = None,
                         size: tuple[float, float] | None = None) -> dict:
        params: dict[str, Any] = {
            "widget_name": widget_name,
            "progress_bar_name": progress_bar_name,
        }
        if percent is not None:
            params["percent"] = percent
        if color is not None:
            params["color"] = list(color)
        if position is not None:
            params["position"] = list(position)
        if size is not None:
            params["size"] = list(size)
        return self._cmd("add_progress_bar_to_widget", params)

    def add_image(self, widget_name: str, image_name: str,
                  position: tuple[float, float] | None = None,
                  size: tuple[float, float] | None = None) -> dict:
        params: dict[str, Any] = {
            "widget_name": widget_name,
            "image_name": image_name,
        }
        if position is not None:
            params["position"] = list(position)
        if size is not None:
            params["size"] = list(size)
        return self._cmd("add_image_to_widget", params)

    def add_button(self, widget_name: str, button_name: str,
                   position: tuple[float, float] | None = None) -> dict:
        params: dict[str, Any] = {
            "widget_name": widget_name,
            "button_name": button_name,
        }
        if position is not None:
            params["position"] = list(position)
        return self._cmd("add_button_to_widget", params)

    def add_canvas_panel(self, widget_name: str,
                         canvas_name: str) -> dict:
        return self._cmd("add_canvas_panel_to_widget", {
            "widget_name": widget_name,
            "canvas_panel_name": canvas_name,
        })

    def add_vertical_box(self, widget_name: str,
                         box_name: str) -> dict:
        return self._cmd("add_vertical_box_to_widget", {
            "widget_name": widget_name,
            "vertical_box_name": box_name,
        })

    def add_horizontal_box(self, widget_name: str,
                           box_name: str) -> dict:
        return self._cmd("add_horizontal_box_to_widget", {
            "widget_name": widget_name,
            "horizontal_box_name": box_name,
        })

    def add_size_box(self, widget_name: str,
                     size_box_name: str) -> dict:
        return self._cmd("add_size_box_to_widget", {
            "widget_name": widget_name,
            "size_box_name": size_box_name,
        })

    def add_overlay(self, widget_name: str,
                    overlay_name: str) -> dict:
        return self._cmd("add_overlay_to_widget", {
            "widget_name": widget_name,
            "overlay_name": overlay_name,
        })

    def add_border(self, widget_name: str,
                   border_name: str) -> dict:
        return self._cmd("add_border_to_widget", {
            "widget_name": widget_name,
            "border_name": border_name,
        })

    def add_generic_widget(self, widget_name: str,
                           component_class: str,
                           component_name: str) -> dict:
        return self._cmd("add_generic_widget_to_widget", {
            "widget_name": widget_name,
            "component_class": component_class,
            "component_name": component_name,
        })

    def set_widget_text(self, widget_name: str, target: str,
                        text: str,
                        font_size: int | None = None,
                        color: tuple[float, float, float, float] | None = None) -> dict:
        params: dict[str, Any] = {
            "widget_name": widget_name,
            "target": target,
            "text": text,
        }
        if font_size is not None:
            params["font_size"] = font_size
        if color is not None:
            params["color"] = list(color)
        return self._cmd("set_widget_text", params)

    def set_widget_properties(self, widget_name: str, target: str,
                              **properties: Any) -> dict:
        params: dict[str, Any] = {
            "widget_name": widget_name,
            "target": target,
        }
        params.update(properties)
        return self._cmd("set_widget_properties", params)

    def set_text_block_binding(self, widget_name: str,
                               text_block_name: str,
                               binding_property: str) -> dict:
        return self._cmd("set_text_block_binding", {
            "widget_name": widget_name,
            "text_block_name": text_block_name,
            "binding_property": binding_property,
        })

    def add_widget_to_viewport(self, widget_name: str,
                               z_order: int = 0) -> dict:
        params: dict[str, Any] = {"widget_name": widget_name}
        if z_order:
            params["z_order"] = z_order
        return self._cmd("add_widget_to_viewport", params)

    def bind_widget_event(self, widget_name: str, target: str,
                          event_name: str,
                          function_name: str) -> dict:
        return self._cmd("bind_widget_event", {
            "widget_name": widget_name,
            "target": target,
            "event_name": event_name,
            "function_name": function_name,
        })

    def list_widget_components(self, widget_name: str) -> dict:
        return self._cmd("list_widget_components", {"widget_name": widget_name})

    def get_widget_tree(self, widget_name: str) -> dict:
        return self._cmd("get_widget_tree", {"widget_name": widget_name})

    def reparent_widgets(self, widget_name: str,
                         target_parent: str,
                         children: list[str]) -> dict:
        return self._cmd("reparent_widgets", {
            "widget_name": widget_name,
            "target_container_name": target_parent,
            "children": children,
        })

    def delete_widget(self, widget_name: str, target: str) -> dict:
        return self._cmd("delete_widget_from_blueprint", {
            "widget_name": widget_name,
            "target": target,
        })

    def rename_widget(self, widget_name: str, target: str,
                      new_name: str) -> dict:
        return self._cmd("rename_widget_in_blueprint", {
            "widget_name": widget_name,
            "target": target,
            "new_name": new_name,
        })

    def add_widget_child(self, widget_name: str, parent: str,
                         child: str) -> dict:
        return self._cmd("add_widget_child", {
            "widget_name": widget_name,
            "parent": parent,
            "child": child,
        })
