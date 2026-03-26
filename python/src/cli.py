"""CLI entry point for ue_bridge. Usage: python -m src <command> [options]"""
from __future__ import annotations

import argparse
import json
import sys

from .bridge import UEBridge
from .errors import UECommandError, UEConnectionError


def _json_out(data):
    print(json.dumps(data, indent=2))


def cmd_ping(ue: UEBridge, args):
    result = ue.ping()
    _json_out({"pong": result})


def cmd_save(ue: UEBridge, args):
    _json_out(ue.save_all())


def cmd_list_assets(ue: UEBridge, args):
    assets = ue.list_assets(path=args.path)
    _json_out({"count": len(assets), "assets": assets})


def cmd_get_actors(ue: UEBridge, args):
    actors = ue.get_actors()
    _json_out({"count": len(actors), "actors": actors})


def cmd_compile(ue: UEBridge, args):
    _json_out(ue.compile(args.blueprint))


def cmd_summary(ue: UEBridge, args):
    _json_out(ue.get_blueprint_summary(args.blueprint))


def cmd_spawn_actor(ue: UEBridge, args):
    loc = tuple(float(x) for x in args.location.split(",")) if args.location else (0, 0, 0)
    _json_out(ue.spawn_actor(args.type, args.name, location=loc))


def cmd_delete_actor(ue: UEBridge, args):
    _json_out(ue.delete_actor(args.name))


def cmd_create_input_action(ue: UEBridge, args):
    _json_out(ue.create_input_action(args.name, value_type=args.value_type, path=args.path))


def cmd_add_key_mapping(ue: UEBridge, args):
    _json_out(ue.add_key_mapping(args.context, args.action, args.key,
                                  action_path=args.action_path))


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

    p = sub.add_parser("list-assets", help="List assets")
    p.add_argument("--path", default="/Game/")

    sub.add_parser("get-actors", help="List level actors")

    p = sub.add_parser("compile", help="Compile blueprint")
    p.add_argument("--blueprint", required=True)

    p = sub.add_parser("summary", help="Blueprint summary")
    p.add_argument("--blueprint", required=True)

    p = sub.add_parser("spawn-actor", help="Spawn actor")
    p.add_argument("--type", required=True)
    p.add_argument("--name", required=True)
    p.add_argument("--location", default=None, help="x,y,z")

    p = sub.add_parser("delete-actor", help="Delete actor")
    p.add_argument("--name", required=True)

    p = sub.add_parser("create-input-action", help="Create Enhanced Input Action")
    p.add_argument("--name", required=True)
    p.add_argument("--value-type", default="Digital")
    p.add_argument("--path", default="/Game/Input/Actions")

    p = sub.add_parser("add-key-mapping", help="Add key to mapping context")
    p.add_argument("--context", required=True)
    p.add_argument("--action", required=True)
    p.add_argument("--key", required=True)
    p.add_argument("--action-path", default="/Game/Input/Actions")

    p = sub.add_parser("raw", help="Send raw command")
    p.add_argument("command_type")
    p.add_argument("--params", default=None, help="JSON params string")

    return parser


COMMAND_MAP = {
    "ping": cmd_ping,
    "save": cmd_save,
    "list-assets": cmd_list_assets,
    "get-actors": cmd_get_actors,
    "compile": cmd_compile,
    "summary": cmd_summary,
    "spawn-actor": cmd_spawn_actor,
    "delete-actor": cmd_delete_actor,
    "create-input-action": cmd_create_input_action,
    "add-key-mapping": cmd_add_key_mapping,
    "raw": cmd_raw,
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
