# Skill: UE Editor Automation — Installation

## Prerequisites

- macOS or Windows
- Unreal Engine 5.7+
- Python 3.10+
- UE Editor running with the UEEditorMCP plugin enabled

## Repo Layout

This skill lives in `ue_bridge_skill/`. The key directories:

```
ue_bridge_skill/
  plugin/           C++ UE plugin (copy into your project's Plugins/)
  python/           Python library (install with pip)
  skills/           AI-facing documentation (this file)
  scripts/          Platform-specific setup helpers
```

## Installation

This markdown guide is the primary installation surface for AI agents. The setup scripts are convenience helpers, not exhaustive error-handling wrappers. If a step fails, inspect the exact failure and continue from there instead of assuming the script can recover automatically.

### Step 1: Install the C++ plugin

**macOS** — use the setup script:

```bash
cd ue_bridge_skill
./scripts/setup.sh /path/to/your/UE/project
```

The script copies the plugin into `<YourProject>/Plugins/UEEditorMCP/`, patches the RTTI build flag for macOS compatibility, and compiles using UE 5.7's build tools.

**Windows** — copy manually:

```
Copy ue_bridge_skill/plugin/ → <YourProject>/Plugins/UEEditorMCP/
```

Then restart the UE Editor.

### Step 2: Verify the plugin is running

After restarting UE, the plugin auto-starts a TCP server on port 55558. Verification:

- Output Log should contain `MCP Server started on port 55558`.
- If using the CLI (Step 3), `ue-bridge ping` will confirm end-to-end connectivity.

### Step 3: Install the Python library

```bash
cd ue_bridge_skill/python
pip install -e ".[dev]"
```

This installs the `ue-bridge` package in editable mode with test dependencies. It provides:

- **Python import**: `from ue_bridge import UEBridge`
- **CLI command**: `ue-bridge` (available after install)
- **Module invocation**: `python3 -m ue_bridge` (canonical) or `python3 -m src` (legacy compatibility)

### Step 4: Confirm end-to-end connectivity

```bash
ue-bridge doctor
ue-bridge verify
```

Use the two commands differently:

- `ue-bridge doctor` returns a structured diagnosis report across connection, editor context, readiness, and logs
- `ue-bridge verify` is the final gate and exits non-zero unless the bridge is actually ready to use

If `verify` succeeds, installation is complete.

## Troubleshooting

**"Cannot connect to Unreal Editor"**: UE Editor is not running, or the UEEditorMCP plugin is not enabled. Check Edit > Plugins in UE.

**"Connection refused on port 55558"**: The plugin's TCP server may not have started. Search for "MCP" in UE's Output Log.

**`doctor` succeeds but `verify` fails**: The editor is reachable, but not fully initialized. Wait for asset registry loading to finish, then run `ue-bridge verify` again.

**Python import errors**: Ensure you ran `pip install -e .` from the `python/` directory. The package name is `ue-bridge` and the canonical import is `from ue_bridge import UEBridge`.

**macOS RTTI build error**: The setup script patches `bUseRTTI=false` automatically. If building manually, ensure `.uplugin` or `.Build.cs` has `bUseRTTI = false`.

**Windows plugin not loading**: Ensure the plugin folder is at `<YourProject>/Plugins/UEEditorMCP/` and contains `UEEditorMCP.uplugin`. Restart the editor after copying.
