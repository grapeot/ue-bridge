# Skill: UE Editor Automation — Usage Guide

## Core Concept

`ue-bridge` is a Python library that controls Unreal Editor over TCP (port 55558). The C++ plugin inside UE handles commands; the Python library sends them.

**Two usage surfaces:**

- **CLI** (`ue-bridge <command>`) — for simple, one-off tasks: ping, inspect context, query actors, create basic assets, compile a Blueprint, spawn an actor.
- **Python library** (`from ue_bridge import UEBridge`) — for multi-step workflows: creating Blueprints, wiring nodes, configuring input systems, batch operations.

Use CLI when a single command suffices. Use the library when you need sequencing, conditionals, or access to node IDs returned by earlier calls.

## CLI Quick Reference

```bash
ue-bridge ping
ue-bridge get-context
ue-bridge save
ue-bridge get-actors
ue-bridge find-actors --pattern "Wall*"
ue-bridge list-assets --path /Game/ThirdPerson/
ue-bridge compile --blueprint BP_ThirdPersonCharacter
ue-bridge summary --blueprint BP_ThirdPersonCharacter
ue-bridge create-blueprint --name BP_Test --parent-class Character --path /Game/Test
ue-bridge create-input-action --name IA_Foo
ue-bridge create-input-mapping-context --name IMC_Default
ue-bridge add-key-mapping --context IMC_Default --action IA_Foo --key F
ue-bridge spawn-actor --type StaticMeshActor --name Wall_01 --location 100,0,0
ue-bridge spawn-blueprint-actor --blueprint BP_Test --name BP_Test_01 --location 0,0,100
ue-bridge delete-actor --name Wall_01
ue-bridge auto-layout --blueprint BP_Test
ue-bridge raw get_context
ue-bridge raw compile_blueprint --params '{"blueprint_name":"BP_Foo"}'
```

Alternatively, from the `python/` directory: `python3 -m ue_bridge <command>` (canonical) or `python3 -m src <command>` (legacy compatibility).

## Python API Quick Reference

### Connection

```python
from ue_bridge import UEBridge

with UEBridge() as ue:
    ue.ping()          # -> True
    ue.save_all()
    ue.get_context()
    ue.list_assets("/Game/ThirdPerson/Blueprints/")
```

Always use the context manager (`with`) to ensure the connection is closed.

### Scene Operations

```python
actors = ue.get_actors()
actors = ue.find_actors("Wall*")
ue.spawn_actor("StaticMeshActor", "Wall_01", location=(100, 0, 0))
ue.set_actor_transform("Wall_01", location=(200, 0, 0), scale=(2, 2, 1))
ue.delete_actor("Wall_01")
```

### Blueprint Properties

```python
summary = ue.get_blueprint_summary("BP_ThirdPersonCharacter")
ue.compile("BP_ThirdPersonCharacter")
ue.set_blueprint_property("BP_Foo", "SomeProperty", "value")
ue.add_component("BP_Foo", "BoxCollisionComponent", "MyCollider")
```

### Blueprint Nodes and Wiring

```python
# Add nodes (each returns a node_id)
input_node = ue.add_enhanced_input_action_node("BP_Foo", "IA_Crouch")
crouch_node = ue.add_function_node("BP_Foo", "Crouch")       # target defaults to "self"
uncrouch_node = ue.add_function_node("BP_Foo", "UnCrouch")

# Inspect pins
pins = ue.get_pins("BP_Foo", input_node)
# -> [{"name": "Started", "direction": "Output", ...}, ...]

# Connect
ue.connect(input_node, "Started", crouch_node, "execute")
ue.connect(input_node, "Completed", uncrouch_node, "execute")

# Compile
ue.compile("BP_Foo")
```

### Input System

```python
ue.create_input_action("IA_Crouch")                    # path defaults to /Game/Input/Actions
ue.add_key_mapping("IMC_Default", "IA_Crouch", "C")   # action_path defaults to /Game/Input/Actions
```

### Materials

```python
ue.create_colored_material("M_Red", color=(1, 0, 0, 1))
ue.compile_material("M_Red")
```

### Raw Commands (Escape Hatch)

All 77+ C++ actions are accessible through `raw_command` for anything the high-level API doesn't wrap yet:

```python
ue.raw_command("some_command", {"param1": "value1"})
```

This is the escape hatch, not the default usage surface. Prefer high-level methods when available.

## Known Limitations

### Inherited Component Properties

`set_component_property` only works on components explicitly added in a Blueprint. For components inherited from parent classes (e.g., Character's CharacterMovement), use `set_inherited_component_property`:

```python
ue.raw_command("set_inherited_component_property", {
    "blueprint_name": "BP_ThirdPersonCharacter",
    "component_name": "CharacterMovement",
    "property_name": "bCanCrouch",
    "property_value": True,
})
```

If unsure of the component name, pass an intentionally wrong name — the error message lists all available components.

### IMC Read and Cleanup

```python
# Read full IMC content (each mapping's action, key, triggers)
imc = ue.raw_command("read_imc", {"context_name": "IMC_Default"})
for m in imc["mappings"]:
    print(f'{m["action_name"]} -> {m["key"]} triggers={m["action_triggers"]}')

# Remove a specific mapping (filter by action_name + key)
ue.raw_command("remove_key_mapping_from_context", {
    "context_name": "IMC_Default",
    "action_name": "IA_Jump",
    "key": "C",
})
```

### Error Handling

`UECommandError` contains error message and error_type. Use try/except:

```python
from ue_bridge.errors import UECommandError

try:
    ue.compile("BP_NonExistent")
except UECommandError as e:
    print(f"Failed: {e} (type: {e.error_type})")
```

### UE Editor Must Be Running

All operations go over TCP to the editor. If the editor is closed, `UEConnectionError` is raised.

## Working Principles

### Save after every operation batch

API changes take effect in memory but are lost if UE crashes without saving. **Call `ue.save_all()` at the end of every script.**

### C++ changes require an editor restart

New C++ plugin capabilities (e.g., a new action) require command-line compilation + editor restart. Python-side changes do not. When a C++ change is needed:

1. Assess the work (a new action is typically 10-20 min coding + 10 sec compile).
2. Tell the user: "This requires a C++ plugin change and an editor restart. Proceed?"
3. If yes, make the change, compile, and remind the user to restart and save.
4. If no, suggest a manual workaround.

### Verify you are editing the correct Blueprint

Different GameModes use different Character Blueprints. Check World Settings or use `get_blueprint_summary` to trace GameMode -> Default Pawn Class before editing.

## Complete Example: Add Crouch to a Character

```python
from ue_bridge import UEBridge

with UEBridge() as ue:
    bp = "BP_ThirdPersonCharacter"

    # 1. Enable crouch on inherited CharacterMovement
    ue.raw_command("set_inherited_component_property", {
        "blueprint_name": bp,
        "component_name": "CharMoveComp",
        "property_name": "NavAgentProps.bCanCrouch",
        "property_value": True,
    })

    # 2. Create Input Action (auto-adds Pressed+Released triggers)
    ue.create_input_action("IA_Crouch", value_type="Digital")

    # 3. Bind C key to IMC
    ue.add_key_mapping("IMC_Default", "IA_Crouch", "C")

    # 4. Add Blueprint nodes
    input_node = ue.add_enhanced_input_action_node(bp, "IA_Crouch", position=(-400, 1200))
    crouch_node = ue.add_function_node(bp, "Crouch", position=(0, 1100))
    uncrouch_node = ue.add_function_node(bp, "UnCrouch", position=(0, 1300))

    # 5. Wire them
    ue.connect(input_node, "Started", crouch_node, "execute")
    ue.connect(input_node, "Completed", uncrouch_node, "execute")

    # 6. Compile and save
    ue.compile(bp)
    ue.save_all()

    # 7. Verify
    imc = ue.raw_command("read_imc", {"context_name": "IMC_Default"})
    for m in imc["mappings"]:
        if m["action_name"] == "IA_Crouch":
            print(f'Verified: {m["action_name"]} -> {m["key"]} triggers={m["action_triggers"]}')
```
