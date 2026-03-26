from __future__ import annotations

import time
import uuid
import json
import socket

import pytest

from ue_bridge import UEBridge
from ue_bridge.errors import UEConnectionError


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
    reason="Unreal Editor not running or plugin not loaded",
)

pytestmark = [pytest.mark.integration, skip_no_ue]


@pytest.fixture
def ue():
    bridge = UEBridge(timeout=10.0)
    yield bridge
    bridge.close()


class TestWorkflowA:
    def test_doctor_and_verify(self, ue: UEBridge):
        doctor = ue.doctor()
        assert "checks" in doctor
        assert "ping" in doctor["checks"]
        assert doctor["checks"]["ping"]["ok"] is True

        verify = ue.verify_installation()
        assert verify["verified"] is True
        assert verify["required_checks"]["ping"] is True
        assert verify["required_checks"]["editor_ready"] is True

    def test_get_context_has_basic_shape(self, ue: UEBridge):
        context = ue.get_context()
        assert "current_graph" in context
        assert "dirty_packages_count" in context

    def test_create_and_compile_blueprint(self, ue: UEBridge):
        blueprint_name = f"PyWorkflowA_{uuid.uuid4().hex[:10]}"
        asset_path = "/Game/UEBridgePythonIntegration"

        created = ue.create_blueprint(blueprint_name, parent_class="Actor", path=asset_path)
        assert created["name"] == blueprint_name
        assert created["path"].endswith(blueprint_name)

        compiled = ue.compile(blueprint_name)
        assert compiled["compiled"] is True
        assert compiled["error_count"] == 0

        assets = ue.list_assets(asset_path + "/")
        asset_names = [asset.get("asset_name", "") for asset in assets]
        assert blueprint_name in asset_names

    def test_recent_unreal_logs_are_queryable(self, ue: UEBridge):
        logs = ue.get_unreal_logs(tail_lines=20, max_bytes=8192)
        assert "linesReturned" in logs or "content" in logs or "cursor" in logs

    def test_raw_socket_ping_and_close(self):
        def send_message(sock: socket.socket, payload: dict) -> dict:
            message = json.dumps(payload).encode("utf-8")
            sock.sendall(len(message).to_bytes(4, byteorder="big") + message)

            length_bytes = sock.recv(4)
            assert len(length_bytes) == 4
            response_length = int.from_bytes(length_bytes, byteorder="big")

            chunks: list[bytes] = []
            bytes_remaining = response_length
            while bytes_remaining > 0:
                chunk = sock.recv(bytes_remaining)
                assert chunk
                chunks.append(chunk)
                bytes_remaining -= len(chunk)

            return json.loads(b"".join(chunks).decode("utf-8"))

        with socket.create_connection(("127.0.0.1", 55558), timeout=5.0) as sock:
            ping_response = send_message(sock, {"type": "ping"})
            assert ping_response["status"] == "success"
            assert ping_response["result"]["pong"] is True

            close_response = send_message(sock, {"type": "close"})
            assert close_response["status"] == "success"
            assert close_response["result"]["closed"] is True
