"""CLI entry point for ue_bridge. Usage: ue-bridge <command> [options]"""
from __future__ import annotations

import argparse
import json
import sys

from .bridge import UEBridge
from .errors import UECommandError, UEConnectionError


def _json_out(data):
    print(json.dumps(data, indent=2))


def _parse_location(value: str | None) -> tuple[float, float, float]:
    if not value:
        return (0.0, 0.0, 0.0)
    parts = tuple(float(x) for x in value.split(","))
    if len(parts) != 3:
        raise UECommandError("Location must be in x,y,z format", error_type="invalid_arguments")
    return parts


def cmd_ping(ue: UEBridge, args):
    result = ue.ping()
    _json_out({"pong": result})


def cmd_get_context(ue: UEBridge, args):
    _json_out(ue.get_context())


def cmd_is_ready(ue: UEBridge, args):
    _json_out(ue.is_ready())


def cmd_save(ue: UEBridge, args):
    _json_out(ue.save_all())


def cmd_get_editor_logs(ue: UEBridge, args):
    _json_out(ue.get_editor_logs(count=args.count, category=args.category, min_verbosity=args.min_verbosity))


def cmd_get_unreal_logs(ue: UEBridge, args):
    _json_out(
        ue.get_unreal_logs(
            tail_lines=args.tail_lines,
            max_bytes=args.max_bytes,
            include_meta=not args.no_include_meta,
            require_recent=args.require_recent,
            recent_window_seconds=args.recent_window_seconds,
            filter_contains=args.filter_contains,
            filter_category=args.filter_category,
        )
    )


def cmd_doctor(ue: UEBridge, args):
    _json_out(
        ue.doctor(
            editor_log_count=args.editor_log_count,
            unreal_tail_lines=args.unreal_tail_lines,
            require_recent_live_logs=args.require_recent_live_logs,
        )
    )


def cmd_verify(ue: UEBridge, args):
    result = ue.verify_installation()
    _json_out(result)
    if not result.get("verified", False):
        raise SystemExit(1)


def cmd_list_assets(ue: UEBridge, args):
    assets = ue.list_assets(path=args.path)
    _json_out({"count": len(assets), "assets": assets})


def cmd_get_actors(ue: UEBridge, args):
    actors = ue.get_actors()
    _json_out({"count": len(actors), "actors": actors})


def cmd_find_actors(ue: UEBridge, args):
    actors = ue.find_actors(args.pattern)
    _json_out({"count": len(actors), "actors": actors})


def cmd_compile(ue: UEBridge, args):
    _json_out(ue.compile(args.blueprint))


def cmd_summary(ue: UEBridge, args):
    _json_out(ue.get_blueprint_summary(args.blueprint))


def cmd_spawn_actor(ue: UEBridge, args):
    loc = _parse_location(args.location)
    _json_out(ue.spawn_actor(args.type, args.name, location=loc))


def cmd_spawn_blueprint_actor(ue: UEBridge, args):
    loc = _parse_location(args.location)
    _json_out(ue.spawn_blueprint_actor(args.blueprint, args.name, location=loc))


def cmd_delete_actor(ue: UEBridge, args):
    _json_out(ue.delete_actor(args.name))


def cmd_create_input_action(ue: UEBridge, args):
    _json_out(ue.create_input_action(args.name, value_type=args.value_type, path=args.path))


def cmd_create_input_mapping_context(ue: UEBridge, args):
    _json_out(ue.create_input_mapping_context(args.name, path=args.path))


def cmd_create_blueprint(ue: UEBridge, args):
    _json_out(ue.create_blueprint(args.name, parent_class=args.parent_class, path=args.path))


def cmd_auto_layout(ue: UEBridge, args):
    _json_out(ue.auto_layout(args.blueprint, mode=args.mode))


def cmd_add_key_mapping(ue: UEBridge, args):
    _json_out(ue.add_key_mapping(args.context, args.action, args.key,
                                  action_path=args.action_path))


def cmd_start_pie(ue: UEBridge, args):
    _json_out(ue.start_pie(mode=args.mode))


def cmd_stop_pie(ue: UEBridge, args):
    _json_out(ue.stop_pie())


def cmd_pie_state(ue: UEBridge, args):
    _json_out(ue.get_pie_state())


def cmd_raw(ue: UEBridge, args):
    params = json.loads(args.params) if args.params else None
    _json_out(ue.raw_command(args.command_type, params))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="ue-bridge",
                                     description="Unreal Editor automation CLI")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=55558)

    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("ping", help="Test connection")
    sub.add_parser("save", help="Save all")
    sub.add_parser("get-context", help="Get current editor context")
    sub.add_parser("is-ready", help="Check whether Unreal Editor is fully ready")

    p = sub.add_parser("get-editor-logs", help="Read recent captured editor logs")
    p.add_argument("--count", type=int, default=100)
    p.add_argument("--category", default=None)
    p.add_argument("--min-verbosity", default=None)

    p = sub.add_parser("get-unreal-logs", help="Read live Unreal log capture output")
    p.add_argument("--tail-lines", type=int, default=200)
    p.add_argument("--max-bytes", type=int, default=65536)
    p.add_argument("--no-include-meta", action="store_true")
    p.add_argument("--require-recent", action="store_true")
    p.add_argument("--recent-window-seconds", type=float, default=2.0)
    p.add_argument("--filter-contains", default=None)
    p.add_argument("--filter-category", default=None)

    p = sub.add_parser("doctor", help="Run install/verify/diagnose checks")
    p.add_argument("--editor-log-count", type=int, default=50)
    p.add_argument("--unreal-tail-lines", type=int, default=80)
    p.add_argument("--require-recent-live-logs", action="store_true")

    sub.add_parser("verify", help="Verify that the installed bridge is ready to use")

    p = sub.add_parser("list-assets", help="List assets")
    p.add_argument("--path", default="/Game/")

    sub.add_parser("get-actors", help="List level actors")

    p = sub.add_parser("find-actors", help="Find actors by name pattern")
    p.add_argument("--pattern", required=True)

    p = sub.add_parser("compile", help="Compile blueprint")
    p.add_argument("--blueprint", required=True)

    p = sub.add_parser("summary", help="Blueprint summary")
    p.add_argument("--blueprint", required=True)

    p = sub.add_parser("spawn-actor", help="Spawn actor")
    p.add_argument("--type", required=True)
    p.add_argument("--name", required=True)
    p.add_argument("--location", default=None, help="x,y,z")

    p = sub.add_parser("spawn-blueprint-actor", help="Spawn blueprint actor")
    p.add_argument("--blueprint", required=True)
    p.add_argument("--name", required=True)
    p.add_argument("--location", default=None, help="x,y,z")

    p = sub.add_parser("delete-actor", help="Delete actor")
    p.add_argument("--name", required=True)

    p = sub.add_parser("create-blueprint", help="Create blueprint asset")
    p.add_argument("--name", required=True)
    p.add_argument("--parent-class", default="Actor")
    p.add_argument("--path", default=None)

    p = sub.add_parser("create-input-action", help="Create Enhanced Input Action")
    p.add_argument("--name", required=True)
    p.add_argument("--value-type", default="Digital")
    p.add_argument("--path", default="/Game/Input/Actions")

    p = sub.add_parser("create-input-mapping-context", help="Create input mapping context")
    p.add_argument("--name", required=True)
    p.add_argument("--path", default="/Game/Input")

    p = sub.add_parser("add-key-mapping", help="Add key to mapping context")
    p.add_argument("--context", required=True)
    p.add_argument("--action", required=True)
    p.add_argument("--key", required=True)
    p.add_argument("--action-path", default="/Game/Input/Actions")

    p = sub.add_parser("start-pie", help="Start Play In Editor session")
    p.add_argument("--mode", default="SelectedViewport",
                   choices=["SelectedViewport", "NewWindow", "Simulate"])

    sub.add_parser("stop-pie", help="Stop Play In Editor session")
    sub.add_parser("pie-state", help="Query PIE session state")

    p = sub.add_parser("raw", help="Send raw command")
    p.add_argument("command_type")
    p.add_argument("--params", default=None, help="JSON params string")

    p = sub.add_parser("auto-layout", help="Auto-layout blueprint graph")
    p.add_argument("--blueprint", required=True)
    p.add_argument("--mode", default="all")

    return parser


COMMAND_MAP = {
    "ping": cmd_ping,
    "save": cmd_save,
    "get-context": cmd_get_context,
    "is-ready": cmd_is_ready,
    "get-editor-logs": cmd_get_editor_logs,
    "get-unreal-logs": cmd_get_unreal_logs,
    "doctor": cmd_doctor,
    "verify": cmd_verify,
    "list-assets": cmd_list_assets,
    "get-actors": cmd_get_actors,
    "find-actors": cmd_find_actors,
    "compile": cmd_compile,
    "summary": cmd_summary,
    "spawn-actor": cmd_spawn_actor,
    "spawn-blueprint-actor": cmd_spawn_blueprint_actor,
    "delete-actor": cmd_delete_actor,
    "create-blueprint": cmd_create_blueprint,
    "create-input-action": cmd_create_input_action,
    "create-input-mapping-context": cmd_create_input_mapping_context,
    "add-key-mapping": cmd_add_key_mapping,
    "start-pie": cmd_start_pie,
    "stop-pie": cmd_stop_pie,
    "pie-state": cmd_pie_state,
    "raw": cmd_raw,
    "auto-layout": cmd_auto_layout,
}


def main(argv: list[str] | None = None):
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        ue = UEBridge(host=args.host, port=args.port)
    except UEConnectionError as e:
        print(f"Connection error: {e}", file=sys.stderr)
        sys.exit(1)

    handler = COMMAND_MAP.get(args.command)
    if not handler:
        print(f"Unknown command: {args.command}", file=sys.stderr)
        sys.exit(1)

    try:
        handler(ue, args)
    except UECommandError as e:
        print(json.dumps({"success": False, "error": str(e),
                          "error_type": e.error_type}), file=sys.stderr)
        sys.exit(1)
    except UEConnectionError as e:
        print(f"Connection error: {e}", file=sys.stderr)
        sys.exit(1)
    finally:
        ue.close()


if __name__ == "__main__":
    main()
