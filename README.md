# ue-bridge

`ue-bridge` is an AI-first Unreal Editor bridge.

It is designed so an AI agent can:

- install the editor plugin into a UE project
- verify readiness through machine-readable checks
- use CLI for simple one-off tasks
- use Python for multi-step editor automation

The goal is not to teach a human to click through Unreal menus. The goal is to give an AI a short, reliable, verifiable path from installation to real editor work.

## Architecture

```
Python script (your code)
      |
      |  TCP :55558
      v
C++ plugin (local editor bridge)
      |
      |  Unreal Engine API
      v
UE Editor (live session)
```

The C++ plugin runs a TCP server inside the UE Editor process. The Python library (`ue-bridge`) sends JSON commands over a persistent TCP connection. Every editor action (spawn actor, add Blueprint node, connect pins, compile, etc.) is a single command/response round-trip.

## Recommended Path

If you are evaluating or developing the bridge itself, start with the checked-in host:

```text
hosts/UEBridgeHost/UEBridgeHost.uproject
```

If you are integrating into your own project, use your own `.uproject` instead.

In both cases, the preferred flow is:

1. install the plugin
2. run `ue-bridge doctor`
3. run `ue-bridge verify`
4. if you want a repo-contained end-to-end check, run `scripts/run_python_unreal_integration.sh`

## Quick Start

### 1. Install the plugin

The installation skill / docs are the primary path. The setup scripts are convenience helpers, not the product's main contract.

```bash
# macOS convenience helper
./scripts/setup.sh /path/to/your/UE/project
```

The helper script copies the plugin into your project's `Plugins/` directory, patches the RTTI build flag for macOS compatibility, and compiles the plugin using UE 5.7's build tools.

On **Windows**, copy `plugin/` into your project's `Plugins/` directory, then restart the editor.

If you want the repo-contained validation host instead of wiring your own project first, use:

```text
hosts/UEBridgeHost/UEBridgeHost.uproject
```

### 2. Start Unreal Editor and verify from the CLI

Prefer machine-verifiable checks instead of relying on manual GUI inspection:

```bash
ue-bridge doctor
ue-bridge verify
```

If `verify` succeeds, the plugin is loaded, the local command server is reachable, and the editor is ready enough for automation.

For a full repo-contained end-to-end check, run:

```bash
scripts/run_python_unreal_integration.sh hosts/UEBridgeHost/UEBridgeHost.uproject
```

That script builds the checked-in host, launches Unreal, waits for `ue-bridge verify`, and runs the Python Workflow A integration suite.

### 3. Install the Python library

```bash
cd python
pip install -e ".[dev]"
```

The canonical Python package is `ue_bridge`. The older `src` package remains as a compatibility shim for existing callers.

### 4. Run a Python script

```python
from ue_bridge import UEBridge

with UEBridge() as ue:
    print(ue.ping())  # True

    # Spawn an actor
    ue.spawn_actor("StaticMeshActor", "Wall_01", location=(100, 0, 0))

    # Create an input action and bind it
    ue.create_input_action("IA_Crouch", value_type="Digital")
    ue.add_key_mapping("IMC_Default", "IA_Crouch", "C")

    # Add Blueprint nodes and wire them
    bp = "BP_ThirdPersonCharacter"
    input_node = ue.add_enhanced_input_action_node(bp, "IA_Crouch")
    crouch_node = ue.add_function_node(bp, "Crouch")
    ue.connect(input_node, "Started", crouch_node, "execute")

    ue.compile(bp)
    ue.save_all()
```

Or use the CLI:

```bash
ue-bridge ping
ue-bridge doctor
ue-bridge verify
ue-bridge get-context
ue-bridge get-actors
ue-bridge find-actors --pattern "Wall*"
ue-bridge compile --blueprint BP_ThirdPersonCharacter
```

The CLI is the thin surface for simple one-off tasks. For multi-step automation, use the Python library.

For installation and environment validation, prefer the Workflow A commands:

```bash
ue-bridge doctor
ue-bridge verify
```

`doctor` returns a structured diagnosis report. `verify` is the stricter gate: it exits non-zero when the bridge is reachable but not fully ready.

These commands are the default path for both AI and humans. GUI inspection is a fallback, not the source of truth.

## Key Features

**Blueprint automation** -- Create Blueprints, add nodes (function calls, events, Enhanced Input actions, branches, casts, variable get/set), connect pins, and compile. Full graph construction from Python.

**Enhanced Input support** -- `create_input_action` automatically configures Pressed + Released triggers. `add_key_mapping` binds keys to Input Mapping Contexts. `read_imc` inspects existing mappings.

**Inherited component properties** -- `set_inherited_component_property` modifies properties on components inherited from parent classes (e.g., CharacterMovement.bCanCrouch), which the standard `set_component_property` cannot reach.

**Nested property paths** -- Property setters accept dot-separated paths for nested UE properties.

**Scene management** -- Spawn/delete/transform actors, query the level, manage the viewport camera.

**Materials** -- Create materials and material instances, add expressions, connect to outputs, compile.

**77+ raw commands** -- Every C++ action is accessible through `raw_command()` for anything the high-level API doesn't wrap yet.

**Error handling** -- Operations raise `UECommandError` with structured error types, so scripts can catch and recover.

## Project Structure

```
ue_bridge_skill/
  docs/
    working.md       Current changelog and lessons learned
  plugin/           C++ UE plugin (copy into your project's Plugins/)
    Source/          Plugin source code
    UEBridgeEditor.uplugin
  python/            Python library (pip install -e .)
    ue_bridge/       Canonical package surface
    src/             Compatibility package surface
    tests/           Unit and integration tests
    pyproject.toml
  skills/            AI-facing installation and usage docs
  scripts/
    setup.sh         macOS setup helper
```

## Detailed Documentation

See `skills/` for the primary AI-facing usage guides:

- `skills/ue_editor_installation.md` -- Setup, prerequisites, and troubleshooting
- `skills/ue_editor_usage.md` -- Full Python API reference, CLI reference, working principles, and a complete example

## Running Tests

```bash
cd python

# Unit tests (no UE Editor needed)
python3 -m pytest tests/ -v -k "not integration"

# Contract suite with coverage
python3 -m pytest tests/ -v -k "not integration" --cov=ue_bridge --cov=src --cov-report=term-missing

# Integration tests (requires UE Editor running with plugin enabled)
python3 -m pytest tests/test_integration.py -v -m integration

# Repo-contained end-to-end integration against the checked-in host
scripts/run_python_unreal_integration.sh hosts/UEBridgeHost/UEBridgeHost.uproject
```

GitHub Actions runs the non-integration test suite on every push and pull request.

## Workflow A: Install / Verify / Diagnose

After installing the plugin and Python package, use the diagnostic flow instead of relying only on manual GUI checks:

```bash
ue-bridge doctor
ue-bridge verify
```

- `doctor` checks connectivity, editor context, editor readiness, and log availability
- `verify` enforces the minimum readiness bar for actual use and exits non-zero if the installation is not usable yet

## Credits

The C++ plugin is based on [lilklon/UEBlueprintMCP](https://github.com/lilklon/UEBlueprintMCP) (MIT license), with significant extensions for Enhanced Input, inherited components, IMC read/write, material editing, MVVM bindings, and more.

## License

MIT -- see [LICENSE](LICENSE).
