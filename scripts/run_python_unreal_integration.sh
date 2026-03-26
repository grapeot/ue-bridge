#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

if [[ $# -lt 1 ]]; then
  echo "Usage: $0 <path-to-uproject>"
  exit 1
fi

UPROJECT_PATH="$1"
if [[ ! -f "$UPROJECT_PATH" ]]; then
  echo "ERROR: .uproject file not found: $UPROJECT_PATH"
  exit 1
fi

ENGINE_ROOT="${UE_ENGINE_ROOT:-/Users/Shared/Epic Games/UE_5.7}"
BUILD_SH="$ENGINE_ROOT/Engine/Build/BatchFiles/Mac/Build.sh"
UNREAL_EDITOR="$ENGINE_ROOT/Engine/Binaries/Mac/UnrealEditor.app/Contents/MacOS/UnrealEditor"

if [[ ! -x "$BUILD_SH" ]]; then
  echo "ERROR: Build.sh not found: $BUILD_SH"
  exit 1
fi

if [[ ! -x "$UNREAL_EDITOR" ]]; then
  echo "ERROR: UnrealEditor not found: $UNREAL_EDITOR"
  exit 1
fi

PROJECT_DIR="$(cd "$(dirname "$UPROJECT_PATH")" && pwd)"
PROJECT_NAME="$(basename "$UPROJECT_PATH" .uproject)"
REPORT_DIR="$REPO_ROOT/tmp/python_unreal_integration_${PROJECT_NAME}"
LOG_PATH="$REPORT_DIR/editor.log"

mkdir -p "$REPORT_DIR"

echo "==> Building ${PROJECT_NAME}Editor"
"$BUILD_SH" "${PROJECT_NAME}Editor" Mac Development "$UPROJECT_PATH" -WaitMutex

echo "==> Launching Unreal Editor"
"$UNREAL_EDITOR" "$UPROJECT_PATH" -AbsLog="$LOG_PATH" -stdout -FullStdOutLogOutput -unattended -nopause -NullRHI -log > "$REPORT_DIR/editor.stdout.log" 2>&1 &
EDITOR_PID=$!

cleanup() {
  if kill -0 "$EDITOR_PID" >/dev/null 2>&1; then
    kill "$EDITOR_PID" >/dev/null 2>&1 || true
    wait "$EDITOR_PID" >/dev/null 2>&1 || true
  fi
}
trap cleanup EXIT

echo "==> Waiting for ue-bridge verify"
READY=0
for _ in $(seq 1 60); do
  if PYTHONPATH="$REPO_ROOT/python" python3 -c "from ue_bridge import UEBridge; ue = UEBridge(timeout=3.0); result = ue.verify_installation(); ue.close(); import sys; sys.exit(0 if result['verified'] else 1)" >/dev/null 2>&1; then
    READY=1
    break
  fi
  sleep 2
done

if [[ "$READY" -ne 1 ]]; then
  echo "ERROR: ue-bridge verify did not succeed within timeout"
  exit 1
fi

echo "==> Running Python workflow A integration tests"
PYTHONPATH="$REPO_ROOT/python" python3 -m pytest "$REPO_ROOT/python/tests/test_integration_workflow_a.py" -v -m integration

echo "==> Integration flow completed successfully"
