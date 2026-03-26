"""
UEBridge — Main API class for Unreal Editor automation.

Usage:
    from ue_bridge.src import UEBridge

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

    def save_all(self) -> dict:
        return self._cmd("save_all")

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
            "name": name,
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
            "property_value": str(property_value),
        })

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
        params: dict[str, Any] = {"name": name}
        if path:
            params["path"] = path
        return self._cmd("create_material", params)

    def create_colored_material(self, name: str,
                                color: tuple[float, float, float, float] = (1, 1, 1, 1),
                                path: str | None = None) -> dict:
        params: dict[str, Any] = {"name": name, "color": list(color)}
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
