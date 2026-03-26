#!/usr/bin/env bash
#
# setup.sh -- One-click setup for ue-bridge on macOS.
#
# Usage:
#   ./scripts/setup.sh /path/to/your/UE/project
#
# What it does:
#   1. Copies plugin/ into <project>/Plugins/UEEditorMCP/
#   2. Patches bUseRTTI = true -> false in Build.cs (Mac linker fix)
#   3. Finds UE 5.7 RunUBT.sh and compiles the project
#   4. Creates a Python venv in python/.venv if it doesn't exist

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# ---------------------------------------------------------------------------
# Argument check
# ---------------------------------------------------------------------------

if [[ $# -lt 1 ]]; then
    echo "Usage: $0 <UE-project-path>"
    echo ""
    echo "  <UE-project-path>  Path to your .uproject directory"
    echo "                     (the folder containing the .uproject file)"
    exit 1
fi

UE_PROJECT_DIR="$1"

if [[ ! -d "$UE_PROJECT_DIR" ]]; then
    echo "ERROR: Directory does not exist: $UE_PROJECT_DIR"
    exit 1
fi

# Find the .uproject file
UPROJECT_FILE=$(find "$UE_PROJECT_DIR" -maxdepth 1 -name "*.uproject" | head -1)
if [[ -z "$UPROJECT_FILE" ]]; then
    echo "ERROR: No .uproject file found in $UE_PROJECT_DIR"
    exit 1
fi

UPROJECT_NAME=$(basename "$UPROJECT_FILE" .uproject)
echo "Found project: $UPROJECT_NAME ($UPROJECT_FILE)"

# ---------------------------------------------------------------------------
# Step 1: Copy plugin
# ---------------------------------------------------------------------------

PLUGIN_DEST="$UE_PROJECT_DIR/Plugins/UEEditorMCP"
echo ""
echo "==> Copying plugin to $PLUGIN_DEST ..."

mkdir -p "$PLUGIN_DEST"
rsync -a --delete \
    --exclude='.git' \
    --exclude='Binaries' \
    --exclude='Intermediate' \
    "$REPO_ROOT/plugin/" "$PLUGIN_DEST/"

echo "    Done."

# ---------------------------------------------------------------------------
# Step 2: Fix RTTI in Build.cs
# ---------------------------------------------------------------------------

BUILD_CS="$PLUGIN_DEST/Source/UEEditorMCP/UEEditorMCP.Build.cs"
if [[ -f "$BUILD_CS" ]]; then
    echo ""
    echo "==> Patching RTTI in Build.cs ..."
    # Ensure bUseRTTI is false (avoids typeinfo linker errors on Mac)
    sed -i '' 's/bUseRTTI = true/bUseRTTI = false/g' "$BUILD_CS"
    echo "    bUseRTTI set to false."
else
    echo "WARNING: Build.cs not found at $BUILD_CS, skipping RTTI patch."
fi

# ---------------------------------------------------------------------------
# Step 3: Find UE 5.7 and compile
# ---------------------------------------------------------------------------

echo ""
echo "==> Looking for Unreal Engine 5.7 ..."

# Common UE install locations on macOS
UE_SEARCH_PATHS=(
    "/Users/Shared/Epic Games/UE_5.7"
    "$HOME/UnrealEngine-5.7"
    "/opt/UnrealEngine-5.7"
)

RUN_UBT=""
for SEARCH_PATH in "${UE_SEARCH_PATHS[@]}"; do
    CANDIDATE="$SEARCH_PATH/Engine/Build/BatchFiles/Mac/RunUBT.sh"
    if [[ -f "$CANDIDATE" ]]; then
        RUN_UBT="$CANDIDATE"
        break
    fi
done

# Fallback: search the entire /Users/Shared/Epic Games/ directory
if [[ -z "$RUN_UBT" ]]; then
    RUN_UBT=$(find "/Users/Shared/Epic Games" -path "*/5.7*/Engine/Build/BatchFiles/Mac/RunUBT.sh" 2>/dev/null | head -1 || true)
fi

if [[ -n "$RUN_UBT" ]]; then
    echo "    Found RunUBT.sh: $RUN_UBT"
    echo ""
    echo "==> Compiling $UPROJECT_NAME (Development Editor, Mac) ..."
    "$RUN_UBT" "${UPROJECT_NAME}Editor" Mac Development -Project="$UPROJECT_FILE" -TargetType=Editor
    echo "    Compilation complete."
else
    echo "    WARNING: Could not find UE 5.7 RunUBT.sh."
    echo "    You will need to compile manually:"
    echo "      Open the project in UE Editor, or run RunUBT.sh yourself."
fi

# ---------------------------------------------------------------------------
# Step 4: Create Python venv
# ---------------------------------------------------------------------------

PYTHON_DIR="$REPO_ROOT/python"
VENV_DIR="$PYTHON_DIR/.venv"

echo ""
echo "==> Setting up Python environment ..."

if [[ -d "$VENV_DIR" ]]; then
    echo "    .venv already exists at $VENV_DIR, skipping."
else
    if command -v uv &>/dev/null; then
        echo "    Creating venv with uv ..."
        uv venv "$VENV_DIR"
        source "$VENV_DIR/bin/activate"
        uv pip install -e "$PYTHON_DIR[dev]"
    elif command -v python3 &>/dev/null; then
        echo "    Creating venv with python3 ..."
        python3 -m venv "$VENV_DIR"
        source "$VENV_DIR/bin/activate"
        pip install -e "$PYTHON_DIR[dev]"
    else
        echo "    WARNING: Neither uv nor python3 found. Skipping venv creation."
    fi
fi

# ---------------------------------------------------------------------------
# Done
# ---------------------------------------------------------------------------

echo ""
echo "=== Setup complete ==="
echo ""
echo "Next steps:"
echo "  1. Open $UPROJECT_FILE in Unreal Editor"
echo "  2. Run: cd $PYTHON_DIR && source .venv/bin/activate && ue-bridge doctor"
echo "  3. Run: cd $PYTHON_DIR && source .venv/bin/activate && ue-bridge verify"
echo "  4. If verify fails, inspect the structured output and retry after the editor finishes loading"
