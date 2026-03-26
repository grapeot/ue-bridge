from __future__ import annotations

import time
import uuid

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
