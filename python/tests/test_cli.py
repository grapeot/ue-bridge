"""Unit tests for CLI argument parsing."""

import pytest

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.cli import build_parser


class TestCLIParsing:
    """Test argument parsing without actually connecting to UE."""

    def test_ping(self):
        parser = build_parser()
        args = parser.parse_args(["ping"])
        assert args.command == "ping"

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
