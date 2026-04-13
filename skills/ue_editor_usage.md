# Skill: UE Editor Automation — Usage Guide

## Core Concept

`ue-bridge` is a Python library that controls Unreal Editor over TCP (port 55558). The C++ plugin inside UE handles commands; the Python library sends them.

**Two usage surfaces:**

- **CLI** (`ue-bridge <command>`) — for simple, one-off tasks: ping, inspect context, query actors, create basic assets, compile a Blueprint, spawn an actor.
- **Python library** (`from ue_bridge import UEBridge`) — for multi-step workflows: creating Blueprints, wiring nodes, configuring input systems, batch operations.

Use CLI when a single command suffices. Use the library when you need sequencing, conditionals, or access to node IDs returned by earlier calls.

Before doing real work, use the Workflow A checks once:

```bash
ue-bridge doctor
ue-bridge verify
```

If you want a full repo-contained validation run before editing anything, use:

```bash
scripts/run_python_unreal_integration.sh hosts/UEBridgeHost/UEBridgeHost.uproject
```

## CLI Quick Reference

```bash
ue-bridge ping
ue-bridge doctor
ue-bridge verify
ue-bridge get-context
ue-bridge is-ready
ue-bridge get-editor-logs --count 50
ue-bridge get-unreal-logs --tail-lines 80
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
ue-bridge start-pie                              # Start PIE (default: SelectedViewport)
ue-bridge start-pie --mode Simulate               # Start in Simulate mode
ue-bridge stop-pie                                # Stop PIE
ue-bridge pie-state                               # Query PIE state (Running/Stopped)
ue-bridge raw get_context
ue-bridge raw compile_blueprint --params '{"blueprint_name":"BP_Foo"}'
```

Alternatively, from the `python/` directory: `python3 -m ue_bridge <command>` (canonical) or `python3 -m src <command>` (legacy compatibility).

The checked-in `hosts/UEBridgeHost` project is the preferred automation baseline. Use larger UE projects only when you need parity with a more realistic environment.

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

### PIE (Play In Editor)

```python
# Start a PIE session
ue.start_pie()                          # default: SelectedViewport
ue.start_pie(mode="Simulate")          # Simulate mode
ue.start_pie(mode="NewWindow")         # Standalone window

# Check state (poll this after start_pie — startup is async)
state = ue.get_pie_state()
print(state["state"])                   # "Running" or "Stopped"

# Stop
ue.stop_pie()
```

PIE is essential for runtime verification. After building Blueprint logic, start PIE, then use `get_unreal_logs()` to check for runtime errors.

### UMG Widgets

```python
# Create a Widget Blueprint
ue.create_widget_blueprint("WBP_HUD", path="/Game/UI/")

# Add components
ue.add_text_block("WBP_HUD", "ScoreText", text="Score: 0")
ue.add_progress_bar("WBP_HUD", "BossHP", percent=1.0, color=(1, 0, 0, 1))
ue.add_image("WBP_HUD", "LifeIcon", position=(10, 10), size=(32, 32))

# Layout containers
ue.add_canvas_panel("WBP_HUD", "MainCanvas")
ue.add_vertical_box("WBP_HUD", "InfoBox")
ue.add_horizontal_box("WBP_HUD", "LivesRow")

# Set text and properties
ue.set_widget_text("WBP_HUD", "ScoreText", "Score: 1000", font_size=24)
ue.set_widget_properties("WBP_HUD", "ScoreText", position=[100, 50], visibility="Visible")

# Bind text to a Blueprint variable for runtime updates
ue.set_text_block_binding("WBP_HUD", "ScoreText", "ScoreVar")

# Inspect widget tree
tree = ue.get_widget_tree("WBP_HUD")
components = ue.list_widget_components("WBP_HUD")

# Get class path for Blueprint use (CreateWidget + AddToViewport)
info = ue.add_widget_to_viewport("WBP_HUD", z_order=10)
print(info["class_path"])  # Use this in Blueprint to create and show the widget

# Structure operations
ue.reparent_widgets("WBP_HUD", "MainCanvas", ["ScoreText", "BossHP"])
ue.rename_widget("WBP_HUD", "ScoreText", "PlayerScore")
ue.delete_widget("WBP_HUD", "OldWidget")
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

### DO NOT use `set_object_property` on AnimBP CDO properties

`set_object_property` creates variable-set nodes in the **EventGraph** rather than modifying the CDO directly. For AnimInstance properties (like `RootMotionMode`), this corrupts the AnimBP: each call adds a new `Set RootMotionMode` node to the graph, the blueprint accumulates compile errors, and there is no undo. The only fix is to manually delete every corrupted node via `delete_blueprint_node`.

**Wrong way**: `set_object_property` on an AnimBP for `RootMotionMode`.

**Safer way**: add a real function call node in `Event Blueprint Initialize Animation` and call `SetRootMotionMode(IgnoreRootMotion)`.

This is persistent at the blueprint logic level and survives editor restarts because it is part of the graph, not an external console-side state:

```python
node = ue.raw_command("add_blueprint_function_node", {
    "blueprint_name": "ABP_Unarmed",
    "graph_name": "EventGraph",
    "target": "self",
    "function_name": "SetRootMotionMode",
    "x": 160,
    "y": -760,
})

ue.raw_command("set_node_pin_default", {
    "blueprint_name": "ABP_Unarmed",
    "node_id": node["node_id"],
    "pin_name": "Value",
    "default_value": "IgnoreRootMotion",
})

ue.raw_command("connect_blueprint_nodes", {
    "blueprint_name": "ABP_Unarmed",
    "source_node_id": "<BlueprintInitializeAnimation node>",
    "source_pin": "then",
    "target_node_id": node["node_id"],
    "target_pin": "execute",
})
```

**Fallback / temporary runtime workaround**: use the console command, which can be useful for quick diagnosis but is a worse long-term fix:

```python
ue.raw_command("execute_console_command", {
    "command": "AnimInstance.RootMotionMode IgnoreRootMotion"
})
```

The console command is useful to confirm root motion is the problem. The function-node approach is the actual durable fix.

### Animation assets with root motion cause uncontrolled character movement

Many locomotion animations (dash, sprint, attack, vault) bake translational displacement into the root bone. When UE extracts root motion from these clips, it applies the baked displacement to the character's capsule component every frame. The character will fly across the map at the animation's velocity.

**Symptoms**: Character lunges or shoots forward the instant a state plays a root-motion clip. The displacement is proportional to the clip's baked velocity, not a small jitter.

**Prevention**:

1. Never use dash/sprint/attack animations as placeholder poses for stationary states (crouch, idle, etc.). Visual similarity is misleading; what matters is whether the clip's root bone translates.
2. If you must use a movement clip in a stationary state, suppress root motion globally:
   ```python
   ue.raw_command("execute_console_command", {
       "command": "AnimInstance.RootMotionMode IgnoreRootMotion"
   })
   ```
3. Engine plugin animation assets (e.g. MoverExamples) may not be loadable in project-local AnimBPs even if the skeleton name matches. Always test compilation immediately after assigning a new animation asset.

### AnimBP state machine editing requires the AnimBP to be open

The `list_anim_states`, `add_anim_state`, `add_anim_transition`, `set_anim_transition_rule`, and `set_anim_state_animation` commands operate on the AnimBP's in-memory state machine graph. If the AnimBP has not been loaded into an asset editor, the commands will fail with "state machine not found." Always call `open_asset_editor` first:

```python
ue.raw_command("open_asset_editor", {
    "asset_path": "/Game/Characters/Mannequins/Anims/Unarmed/ABP_Unarmed.ABP_Unarmed"
})
```

After opening, the short asset name (e.g. `ABP_Unarmed`) works reliably as `blueprint_name` for all AnimBP commands. Full package paths may not resolve.

### AnimBP `compile` return value can be misleading

The `compile_blueprint` command returns `saved_packages_count: 0` even when saves succeed. The bridge's internal dirty tracking and UE's `FEditorFileUtils::GetDirtyPackages()` are separate systems. Trust the `compiled: true` / `error_count: 0` fields, not `saved_packages_count`.

### Content directory is not in git

UE project `Content/` folders are typically gitignored (binary `.uasset` files). If a bridge operation corrupts an asset, there is no `git checkout` recovery path. Mitigations:

1. Before risky operations, consider manually duplicating the `.uasset` file as a backup.
2. If `set_object_property` corrupts an AnimBP, recover by finding and deleting all injected nodes via `find_blueprint_nodes` + `delete_blueprint_node`, then recompile.

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

## Complete Example: Textured Card Display Scene

```python
from ue_bridge import UEBridge

with UEBridge() as ue:
    # 1. Create new empty level
    ue.raw_command("new_level", {
        "level_name": "CardShowcase",
        "path": "/Game/Maps",
        "template": "Empty",
    })

    # 2. Create Unlit material with texture
    #    (texture must be imported first — UE auto-detects PNGs in Content/)
    mat = "M_Card"
    ue.create_material(mat)
    ue.raw_command("set_material_property", {
        "material_name": mat,
        "property_name": "ShadingModel",
        "property_value": "Unlit",
    })
    ue.raw_command("add_material_expression", {
        "material_name": mat,
        "expression_class": "TextureSample",
        "node_name": "CardArt",
        "x": -300, "y": 0,
        "properties": {"Texture": "/Game/CardArt/T_Card.T_Card"},
    })
    ue.raw_command("connect_to_material_output", {
        "material_name": mat,
        "source_node": "CardArt",
        "source_output": "RGB",
        "material_property": "EmissiveColor",
    })
    ue.compile_material(mat)

    # 3. Create card Blueprint with mesh + material
    bp = "BP_Card"
    ue.create_blueprint(bp, parent_class="Actor", path="/Game/Cards")
    ue.add_component(bp, "StaticMeshComponent", "CardMesh")
    ue.set_static_mesh_properties(bp, "CardMesh",
        static_mesh="/Engine/BasicShapes/Cube.Cube",
        materials=[f"/Game/Materials/{mat}.{mat}"])
    ue.compile(bp)

    # 4. Spawn and orient card
    #    Scale (0.7, 0.03, 1.0) = width, THIN, height (portrait card)
    #    Yaw=90 rotates face toward camera at -X
    ue.spawn_blueprint_actor(bp, "Card_0", location=(0, 0, 100))
    full_name = [a["name"] for a in ue.get_actors() if "Card_0" in a["name"]][0]
    ue.set_actor_transform(full_name,
        location=(0, 0, 100),
        rotation=(0, 90, 0),
        scale=(0.7, 0.03, 1.0))
    ue.raw_command("apply_material_to_actor", {
        "actor_name": full_name,
        "material_path": f"/Game/Materials/{mat}.{mat}",
    })

    # 5. SpectatorPawn GameMode (fly camera, no gravity)
    gm = "BP_ShowcaseGameMode"
    ue.create_blueprint(gm, parent_class="GameModeBase", path="/Game/Showcase")
    ue.set_blueprint_property(gm, "DefaultPawnClass", "/Script/Engine.SpectatorPawn")
    ue.compile(gm)
    ue.set_actor_property("WorldSettings", "DefaultGameMode",
        "/Game/Showcase/BP_ShowcaseGameMode.BP_ShowcaseGameMode_C")

    ue.save_all()
```

## Complete Example: Cycling Card Selection with Scale Feedback

Wire Z/X keys to cycle through cards, scaling the selected one up. Uses the "set-all-then-highlight" pattern to avoid Branch merging issues.

```python
from ue_bridge import UEBridge

with UEBridge() as ue:
    bp = "BP_ThirdPersonPlayerController"  # Enhanced Input MUST be here, not in Pawn
    SELECTED = "0.9, 0.04, 1.3"
    NORMAL = "0.7, 0.03, 1.0"
    card_classes = [
        "/Game/Cards/BP_Card_0.BP_Card_0_C",
        "/Game/Cards/BP_Card_1.BP_Card_1_C",
        "/Game/Cards/BP_Card_2.BP_Card_2_C",
    ]

    # Variable to track selection
    ue.add_variable(bp, "CurrentCard", "int", default_value=0)

    # Create input: Z=prev (left), X=next (right) — avoid Q/E (SpectatorPawn uses them)
    for ia, key in [("IA_PrevCard", "Z"), ("IA_NextCard", "X")]:
        ue.create_input_action(ia, value_type="Digital")
        ue.add_key_mapping("IMC_Default", ia, key)

    def build_chain(ia_name, delta, y_base):
        # Input -> compute (CurrentCard + delta) % 3 -> set variable
        ia = ue.add_enhanced_input_action_node(bp, ia_name, position=(-600, y_base))
        get_cur = ue.add_variable_get(bp, "CurrentCard", position=(-400, y_base + 200))

        add_n = ue.raw_command("add_blueprint_function_node", {
            "blueprint_name": bp, "function_name": "Add_IntInt",
            "target": "KismetMathLibrary", "x": -200, "y": y_base + 200,
        })["node_id"]
        ue.connect(get_cur, "CurrentCard", add_n, "A", blueprint_name=bp)
        ue.set_pin_default(bp, add_n, "B", str(delta))

        mod_n = ue.raw_command("add_blueprint_function_node", {
            "blueprint_name": bp, "function_name": "Percent_IntInt",
            "target": "KismetMathLibrary", "x": 0, "y": y_base + 200,
        })["node_id"]
        ue.connect(add_n, "ReturnValue", mod_n, "A", blueprint_name=bp)
        ue.set_pin_default(bp, mod_n, "B", str(len(card_classes)))

        set_cur = ue.add_variable_set(bp, "CurrentCard", position=(200, y_base))
        ue.connect(mod_n, "ReturnValue", set_cur, "CurrentCard", blueprint_name=bp)
        ue.connect(ia, "Started", set_cur, "execute", blueprint_name=bp)

        # Pass 1: set ALL cards to NORMAL scale
        prev, pin = set_cur, "then"
        for i, cc in enumerate(card_classes):
            get_a = ue.add_function_node(bp, "GetActorOfClass",
                target="GameplayStatics", position=(500 + i*400, y_base))
            ue.set_pin_default(bp, get_a, "ActorClass", cc)
            set_s = ue.add_function_node(bp, "SetActorScale3D", position=(700 + i*400, y_base))
            ue.set_pin_default(bp, set_s, "NewScale3D", NORMAL)
            ue.connect(get_a, "ReturnValue", set_s, "self", blueprint_name=bp)
            ue.connect(prev, pin, get_a, "execute", blueprint_name=bp)
            ue.connect(get_a, "then", set_s, "execute", blueprint_name=bp)
            prev, pin = set_s, "then"

        # Pass 2: Branch per card — if CurrentCard==i, scale SELECTED
        for i, cc in enumerate(card_classes):
            x = 1900 + i * 800
            get_c = ue.add_variable_get(bp, "CurrentCard", position=(x - 200, y_base + 200))
            eq = ue.raw_command("add_blueprint_function_node", {
                "blueprint_name": bp, "function_name": "EqualEqual_IntInt",
                "target": "KismetMathLibrary", "x": x, "y": y_base + 200,
            })["node_id"]
            ue.connect(get_c, "CurrentCard", eq, "A", blueprint_name=bp)
            ue.set_pin_default(bp, eq, "B", str(i))

            br = ue.add_branch_node(bp, position=(x + 200, y_base))
            ue.connect(eq, "ReturnValue", br, "Condition", blueprint_name=bp)

            ga = ue.add_function_node(bp, "GetActorOfClass",
                target="GameplayStatics", position=(x + 400, y_base - 150))
            ue.set_pin_default(bp, ga, "ActorClass", cc)
            ss = ue.add_function_node(bp, "SetActorScale3D", position=(x + 600, y_base - 150))
            ue.set_pin_default(bp, ss, "NewScale3D", SELECTED)
            ue.connect(ga, "ReturnValue", ss, "self", blueprint_name=bp)
            ue.connect(br, "then", ga, "execute", blueprint_name=bp)
            ue.connect(ga, "then", ss, "execute", blueprint_name=bp)

            ue.connect(prev, pin, br, "execute", blueprint_name=bp)
            prev, pin = br, "else"  # chain via False path

    build_chain("IA_PrevCard", len(card_classes) - 1, 2000)  # Z = left (previous)
    build_chain("IA_NextCard", 1, 4000)                      # X = right (next)
    ue.compile(bp)
    ue.save_all()
```

## Recipes

### Unlit textured material (guaranteed visibility in any lighting)

```python
ue.create_material("M_Name")
ue.raw_command("set_material_property", {
    "material_name": "M_Name", "property_name": "ShadingModel", "property_value": "Unlit"})
ue.raw_command("add_material_expression", {
    "material_name": "M_Name", "expression_class": "TextureSample",
    "node_name": "Tex", "x": -300, "y": 0,
    "properties": {"Texture": "/Game/Textures/T_Foo.T_Foo"}})
ue.raw_command("connect_to_material_output", {
    "material_name": "M_Name", "source_node": "Tex",
    "source_output": "RGB", "material_property": "EmissiveColor"})
ue.compile_material("M_Name")
```

### Card orientation (portrait, facing -X camera)

Scale `(width, 0.03, height)` with `Yaw=90`. The thin Y dimension faces the camera. Fan spread: `Yaw = 90 + offset`.

### SpectatorPawn for empty levels

Prevents character falling in levels without floors. WASD to fly, right-click + drag to look.

```python
ue.create_blueprint("BP_GM", parent_class="GameModeBase", path="/Game/")
ue.set_blueprint_property("BP_GM", "DefaultPawnClass", "/Script/Engine.SpectatorPawn")
ue.compile("BP_GM")
ue.set_actor_property("WorldSettings", "DefaultGameMode", "/Game/BP_GM.BP_GM_C")
```

### Apply material to scene actor (bypasses Blueprint)

`set_static_mesh_properties` only works on Blueprint components. For scene actors, use:

```python
ue.raw_command("apply_material_to_actor", {
    "actor_name": full_name,  # must include UAID suffix
    "material_path": "/Game/Materials/M_Foo.M_Foo",
})
```

### Actor names have UAID suffixes (editor only)

`spawn_blueprint_actor("BP_Foo", "MyActor")` creates `MyActor_UAID_XXXX` in the editor. Use `get_actors()` + prefix match to find the full name. `find_actors()` pattern matching is unreliable.

**Exception**: During PIE, actor names do NOT have UAID suffixes. `get_pie_actors()` returns clean names like `CardActor_0`. `set_actor_transform()` works with these clean names during PIE.

### spawn_blueprint_actor does not apply scale

Always call `set_actor_transform()` after spawning to set scale. The scale parameter in `spawn_blueprint_actor` is ignored.

### connect() requires blueprint_name

`ue.connect(source, pin, target, pin)` without `blueprint_name` fails with "Source or target node not found". Always pass `blueprint_name=bp` explicitly.

### Enhanced Input must be wired in PlayerController, not Pawn

SpectatorPawn subclasses do NOT receive Enhanced Input Action events in their EventGraph. The events silently don't fire. Wire Enhanced Input handlers in the **PlayerController** Blueprint instead (e.g., `BP_ThirdPersonPlayerController`).

### PlayerController must add IMC to Enhanced Input Subsystem at BeginPlay

Creating Input Actions and adding key mappings to an IMC is not enough — the IMC must be registered with `EnhancedInputLocalPlayerSubsystem` at runtime. Without this, Enhanced Input Action events silently don't fire. Add this to the PlayerController's BeginPlay chain:

```python
# Get the subsystem
get_sub = ue.raw_command("add_blueprint_get_subsystem_node", {
    "blueprint_name": pc,
    "subsystem_class": "EnhancedInputLocalPlayerSubsystem",
    "x": -350, "y": 600,
})

# Call AddMappingContext
add_mc = ue.raw_command("add_blueprint_function_node", {
    "blueprint_name": pc,
    "function_name": "AddMappingContext",
    "target": "EnhancedInputLocalPlayerSubsystem",
    "x": -100, "y": 600,
})
ue.set_pin_default(pc, add_mc["node_id"], "MappingContext",
    "/Game/Input/IMC_Default.IMC_Default")
ue.connect(get_sub["node_id"], "ReturnValue", add_mc["node_id"], "self", blueprint_name=pc)

# Wire into BeginPlay: BeginPlay -> AddMappingContext -> rest of chain
ue.connect(begin_play_id, "then", add_mc["node_id"], "execute", blueprint_name=pc)
```

**This is the most common reason Enhanced Input "doesn't work" in a custom PlayerController.** The ThirdPerson template's PC does this automatically, but freshly created PlayerController Blueprints do not.

### SpectatorPawn consumes WASD, Q, E, C keys

When using SpectatorPawn, avoid binding gameplay actions to: W, A, S, D (movement), Q/E (up/down), C (may conflict with crouch from inherited IMC bindings), arrow keys, mouse buttons. Safe keys: Z, X, V, F, G, H, number keys (use `One`, `Two`, `Three` for main keyboard — not `1`, `2`, `3` which map to numpad).

### set_blueprint_property for CDO properties (not set_object_property)

`set_object_property` injects Set nodes into the EventGraph instead of modifying the CDO. Use `set_blueprint_property` for DefaultPawnClass, PlayerControllerClass, and similar class-default properties on GameMode/PlayerController Blueprints.

### take_screenshot needs viewport refresh

After `set_viewport_transform`, the viewport render doesn't update immediately. Call `select_actors` on a visible actor before `take_screenshot` to force a redraw. Otherwise screenshot may show stale/white content.

### Material expression API details

- `add_material_expression` `expression_class` must be a **short name**: `TextureSample`, `VectorParameter`, `ScalarParameter`, `Constant`, `Add`, `Multiply` — NOT `MaterialExpressionConstant3Vector`
- `add_material_expression` requires `node_name` as **input** (you name the node), not returned
- `set_material_expression_property` `property_value` must be a **string** (uses UE reflection parsing). For LinearColor: `"(R=1.0,G=0.5,B=0.0,A=1.0)"`
- `connect_material_expressions` connects between expression nodes. `connect_to_material_output` connects to main material inputs (BaseColor, EmissiveColor, etc.)
- Material default path is `/Game/Materials/`. Reference format: `/Game/Materials/M_Foo.M_Foo`

### execute_console_command: avoid Python scripting

`execute_console_command` with `py "import unreal; ..."` crashes UE (access violation). Do NOT use for Python scripting. Use dedicated bridge commands or manual editor operations instead.

### CreateWidget is a K2Node

`CreateWidget` cannot be created via `add_function_node` — it's a special UK2Node, not a regular function. UMG widgets must be displayed via Blueprint wiring (BeginPlay → CreateWidget → AddToViewport) in a Blueprint that already has the K2Node, or use PrintString as a runtime text display fallback.

### Math and logic nodes target KismetMathLibrary

Arithmetic and comparison nodes use `target='KismetMathLibrary'`:
```python
ue.raw_command("add_blueprint_function_node", {
    "blueprint_name": bp,
    "function_name": "Add_IntInt",        # also: Percent_IntInt, EqualEqual_IntInt
    "target": "KismetMathLibrary",
    "x": 0, "y": 0,
})
```

### GetActorOfClass + SetActorScale3D work in PIE

Both `GetActorOfClass` (target `GameplayStatics`) and `SetActorScale3D` work as Blueprint function nodes and execute correctly during PIE. `set_actor_transform` also works during PIE for direct actor manipulation from the bridge.

### Branch nodes break sequential exec chains

A Branch node has `then` (True) and `else` (False) outputs. You cannot reconnect both paths to the same downstream node. Pattern for "do something conditional for each item in a list":
1. Set ALL items to default state first (sequential chain)
2. Then check condition for each item and only modify the matching one (Branch per item, chain via `else` pin)

### No `import_asset` command — texture import requires manual step

The bridge has no `import_asset` or equivalent. PNG/texture files placed in `Content/` are NOT automatically imported as uasset by UE. `execute_console_command` with `ContentBrowser.ImportFiles`, `Asset.ImportDir`, or `FbxAutomation.ImportDir` do not work either.

**Workaround**: Copy PNG files into the project's `Content/<subfolder>/` while the editor is running. UE will detect the new files and show an import dialog. The user clicks "Import All". After import, `list_assets` will show the textures.

**Important**: If PNGs are placed before the editor opens, UE will NOT detect them on startup. Delete and re-copy while the editor is running to trigger detection.

### `add_material_expression` crashes when referencing non-existent textures

`add_material_expression` with `properties: {"Texture": "/Game/Foo/T_Bar.T_Bar"}` causes an access violation crash (safely caught) if the texture asset does not exist yet. Always verify the texture is imported (`list_assets`) before referencing it in a material expression.

**Safe pattern**: Create the TextureSample node without the `properties` field, then use `set_material_expression_property` to set the Texture after confirming the asset exists.

### Object reference pins cannot be set via `set_pin_default` or `set_node_pin_default`

`set_pin_default` and `set_node_pin_default` silently fail on object reference pins (e.g., `MappingContext` on `AddMappingContext`). The command returns success and `get_node_pins` shows the pin default as empty. Compilation succeeds but the pin has no value at runtime.

**Workaround**: Use a PlayerController that already has the object reference wired in (e.g., `BP_FirstPersonPlayerController` from the template). Do not create a new PlayerController that needs manual `AddMappingContext` wiring.

### Auto-exposure blows out Unlit Emissive materials in dark scenes

In an empty level with no light sources, UE auto-exposure adapts to the darkness and massively amplifies any Emissive output, making cards appear washed out or pure white. Fix by disabling auto-exposure in `DefaultEngine.ini`:

```ini
[/Script/Engine.RendererSettings]
r.DefaultFeature.AutoExposure=0
```

Requires editor restart. Alternative: add a PostProcessVolume with manual exposure settings (cannot be done via bridge — `spawn_actor` does not support `PostProcessVolume`).

### `get_material_summary` does not show TextureSample texture references

The `properties` field in `get_material_summary` expressions is always empty `{}` for TextureSample nodes, even when a valid texture is assigned via `add_material_expression`. The texture IS set — the material compiles and renders correctly — but you cannot verify it through the bridge API.

### `.uproject` must declare the UEBridgeEditor plugin

Placing the plugin in `Plugins/UEBridgeEditor/` is not sufficient — the `.uproject` file must also list it in the `Plugins` array:
```json
{
    "Name": "UEBridgeEditor",
    "Enabled": true
}
```
Without this declaration, UE loads the project but does not start the bridge TCP listener on port 55558.

### `new_level` overwrites existing levels with the same name

`new_level` with a `level_name` that already exists will create a **fresh empty level**, destroying all actors that were placed in the previous version. There is no `open_level` or `load_level` command in the bridge. To reopen an existing level after an editor restart, use `new_level` only if you're prepared to re-populate it, or set `EditorStartupMap` in `DefaultEngine.ini` to your target level so the editor opens it automatically.

### `take_screenshot` may appear darker than the live viewport

`take_screenshot` captures the viewport buffer but the result may appear significantly darker than what the user sees on screen, especially with Unlit Emissive materials in dark scenes. This is a tonemapping/HDR rendering difference between the viewport display pipeline and the screenshot capture path. Do not use screenshot brightness as the sole indicator of material correctness — ask the user to confirm what they see on screen if in doubt.

### Auto-exposure config requires editor restart

The `r.DefaultFeature.AutoExposure=0` setting in `DefaultEngine.ini` only takes effect after restarting the UE Editor. Changing the file while the editor is running has no effect on the current session. Plan for a restart after modifying renderer settings.

### Texture import auto-detects PNGs placed before editor launch (contradicts earlier finding)

Despite the earlier note that PNGs placed before the editor opens are NOT auto-detected, in practice UE 5.7 **does** auto-import PNGs found in `Content/` subdirectories on project open, at least for fresh projects. The behavior may depend on whether the `Content/` subfolder already has a corresponding `.uasset` or not. Verify with `list_assets` after editor load rather than assuming either behavior.

### Chinese/Unicode filenames in Content/ may cause issues

Rename texture PNGs to ASCII-safe names (e.g., `T_Card_0.png`) before placing them in `Content/` for import. UE asset paths use ASCII internally and Unicode filenames can cause import failures or asset reference issues.

### `apply_material_to_actor` only affects scene actor instances

`apply_material_to_actor` sets the material on the editor-level actor instance (the one visible in the level editor). During PIE, actors are spawned from their Blueprint CDO, which may still have the default material. If the Blueprint's `set_static_mesh_properties` with `materials` parameter was used during creation, the CDO should already have the correct material. Use `apply_material_to_actor` as a visual fix for the editor viewport, not as the primary material assignment path.

### SpectatorPawn + FirstPerson PlayerController causes AddMappingContext warnings

When using a custom GameMode with `SpectatorPawn` as DefaultPawnClass and `BP_FirstPersonPlayerController` as PlayerControllerClass, the template's BeginPlay `AddMappingContext` node may fire before the local player subsystem is ready, producing runtime errors like "Accessed None trying to read property CallFunc_GetLocalPlayerSubsystem_ReturnValue". Despite these errors, Enhanced Input key mappings typically still work because the IMC gets registered on a subsequent frame. These warnings are cosmetic but noisy.
