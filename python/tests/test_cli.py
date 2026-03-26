"""Unit tests for CLI parsing and command contract."""

import json
import pytest

from ue_bridge.cli import build_parser, main


class TestCLIParsing:
    """Test argument parsing without actually connecting to UE."""

    def test_ping(self):
        parser = build_parser()
        args = parser.parse_args(["ping"])
        assert args.command == "ping"

    def test_get_context(self):
        parser = build_parser()
        args = parser.parse_args(["get-context"])
        assert args.command == "get-context"

    def test_compile_requires_blueprint(self):
        parser = build_parser()
        with pytest.raises(SystemExit):
            parser.parse_args(["compile"])

    def test_compile_with_blueprint(self):
        parser = build_parser()
        args = parser.parse_args(["compile", "--blueprint", "BP_Foo"])
        assert args.blueprint == "BP_Foo"

    def test_create_input_action_defaults(self):
        parser = build_parser()
        args = parser.parse_args(["create-input-action", "--name", "IA_Test"])
        assert args.name == "IA_Test"
        assert args.value_type == "Digital"
        assert args.path == "/Game/Input/Actions"

    def test_add_key_mapping(self):
        parser = build_parser()
        args = parser.parse_args([
            "add-key-mapping",
            "--context", "IMC_Default",
            "--action", "IA_Crouch",
            "--key", "C",
        ])
        assert args.context == "IMC_Default"
        assert args.action == "IA_Crouch"
        assert args.key == "C"
        assert args.action_path == "/Game/Input/Actions"

    def test_spawn_actor(self):
        parser = build_parser()
        args = parser.parse_args([
            "spawn-actor",
            "--type", "StaticMeshActor",
            "--name", "Wall_01",
            "--location", "100,200,0",
        ])
        assert args.type == "StaticMeshActor"
        assert args.name == "Wall_01"
        assert args.location == "100,200,0"

    def test_find_actors(self):
        parser = build_parser()
        args = parser.parse_args(["find-actors", "--pattern", "Wall*"])
        assert args.pattern == "Wall*"

    def test_spawn_blueprint_actor(self):
        parser = build_parser()
        args = parser.parse_args([
            "spawn-blueprint-actor",
            "--blueprint", "BP_Foo",
            "--name", "Foo_01",
            "--location", "1,2,3",
        ])
        assert args.blueprint == "BP_Foo"
        assert args.name == "Foo_01"

    def test_create_blueprint_defaults(self):
        parser = build_parser()
        args = parser.parse_args(["create-blueprint", "--name", "BP_Test"])
        assert args.parent_class == "Actor"
        assert args.path is None

    def test_create_input_mapping_context_defaults(self):
        parser = build_parser()
        args = parser.parse_args(["create-input-mapping-context", "--name", "IMC_Default"])
        assert args.path == "/Game/Input"

    def test_auto_layout_defaults(self):
        parser = build_parser()
        args = parser.parse_args(["auto-layout", "--blueprint", "BP_Test"])
        assert args.mode == "all"

    def test_raw_command(self):
        parser = build_parser()
        args = parser.parse_args(["raw", "get_context"])
        assert args.command_type == "get_context"
        assert args.params is None

    def test_raw_command_with_params(self):
        parser = build_parser()
        args = parser.parse_args(["raw", "compile_blueprint", "--params", '{"blueprint_name":"BP_Foo"}'])
        assert args.command_type == "compile_blueprint"
        assert args.params == '{"blueprint_name":"BP_Foo"}'

    def test_custom_host_port(self):
        parser = build_parser()
        args = parser.parse_args(["--host", "192.168.1.1", "--port", "9999", "ping"])
        assert args.host == "192.168.1.1"
        assert args.port == 9999

    def test_list_assets_default_path(self):
        parser = build_parser()
        args = parser.parse_args(["list-assets"])
        assert args.path == "/Game/"

    def test_list_assets_custom_path(self):
        parser = build_parser()
        args = parser.parse_args(["list-assets", "--path", "/Game/ThirdPerson/"])
        assert args.path == "/Game/ThirdPerson/"


class TestCLIContract:
    def test_main_ping_outputs_json(self, monkeypatch, capsys):
        class FakeBridge:
            def __init__(self, host="127.0.0.1", port=55558):
                self.host = host
                self.port = port

            def ping(self):
                return True

            def close(self):
                return None

        monkeypatch.setattr("src.cli.UEBridge", FakeBridge)
        main(["ping"])

        captured = capsys.readouterr()
        assert json.loads(captured.out) == {"pong": True}
        assert captured.err == ""

    def test_main_connection_failure_exits_nonzero(self, monkeypatch, capsys):
        from ue_bridge.errors import UEConnectionError

        class FakeBridge:
            def __init__(self, host="127.0.0.1", port=55558):
                raise UEConnectionError("boom")

        monkeypatch.setattr("src.cli.UEBridge", FakeBridge)

        with pytest.raises(SystemExit) as exc_info:
            main(["ping"])

        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        assert "Connection error: boom" in captured.err

    def test_main_create_blueprint_uses_expected_arguments(self, monkeypatch, capsys):
        calls = {}

        class FakeBridge:
            def __init__(self, host="127.0.0.1", port=55558):
                pass

            def create_blueprint(self, name, parent_class="Actor", path=None):
                calls["args"] = (name, parent_class, path)
                return {"created": True, "name": name}

            def close(self):
                return None

        monkeypatch.setattr("src.cli.UEBridge", FakeBridge)
        main(["create-blueprint", "--name", "BP_Test", "--parent-class", "Character", "--path", "/Game/Test"])

        assert calls["args"] == ("BP_Test", "Character", "/Game/Test")
        captured = capsys.readouterr()
        assert json.loads(captured.out)["created"] is True
