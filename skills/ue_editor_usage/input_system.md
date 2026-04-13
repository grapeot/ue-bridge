← [返回总览](../ue_editor_usage.md)

# Enhanced Input 输入系统

本文档覆盖通过 ue-bridge 操作 UE5 Enhanced Input 系统的全流程：创建 Input Action、绑定按键到 Input Mapping Context (IMC)、在 PlayerController 中注册 IMC，以及常见的失败模式和排查方法。

## Input Action 创建

Input Action 是 Enhanced Input 系统的基本单元，每个 Action 对应一个逻辑操作（如蹲下、跳跃、切换卡片）。

```python
ue.create_input_action("IA_Crouch", value_type="Digital")
```

默认路径为 `/Game/Input/Actions`。创建时会自动附加 Pressed 和 Released 两个触发器。

CLI 方式：

```bash
ue-bridge create-input-action --name IA_Crouch
```

## IMC 按键绑定

Input Mapping Context (IMC) 将 Input Action 和物理按键关联起来。

### 添加绑定

```python
ue.add_key_mapping("IMC_Default", "IA_Crouch", "C")
```

CLI 方式：

```bash
ue-bridge add-key-mapping --context IMC_Default --action IA_Crouch --key C
```

### 读取 IMC 内容

```python
imc = ue.raw_command("read_imc", {"context_name": "IMC_Default"})
for m in imc["mappings"]:
    print(f'{m["action_name"]} -> {m["key"]} triggers={m["action_triggers"]}')
```

### 删除绑定

通过 `action_name` + `key` 组合定位要删除的映射：

```python
ue.raw_command("remove_key_mapping_from_context", {
    "context_name": "IMC_Default",
    "action_name": "IA_Jump",
    "key": "C",
})
```

## Enhanced Input 在自定义 PlayerController 不工作的最常见原因

Enhanced Input 配置完成后按键没有反应，原因几乎总是以下两条之一。

### 原因一：Enhanced Input 节点放在了 Pawn 而非 PlayerController 中

SpectatorPawn 及其子类的 EventGraph 中不会触发 Enhanced Input Action 事件，按键回调会静默失效。所有 Enhanced Input 处理逻辑必须放在 PlayerController Blueprint 中（如 `BP_ThirdPersonPlayerController`），而非 Pawn Blueprint 中。

### 原因二：PlayerController 的 BeginPlay 没有注册 IMC

仅创建 Input Action 和添加按键映射是不够的。IMC 必须在运行时通过 `EnhancedInputLocalPlayerSubsystem` 的 `AddMappingContext` 注册，否则所有 Enhanced Input 事件都不会触发。

ThirdPerson 模板自带的 PlayerController 已经包含这段逻辑，但新建的 PlayerController Blueprint 没有。你需要在 BeginPlay 中手动添加：

```python
pc = "BP_MyPlayerController"

# 获取 Enhanced Input 子系统
get_sub = ue.raw_command("add_blueprint_get_subsystem_node", {
    "blueprint_name": pc,
    "subsystem_class": "EnhancedInputLocalPlayerSubsystem",
    "x": -350, "y": 600,
})

# 调用 AddMappingContext
add_mc = ue.raw_command("add_blueprint_function_node", {
    "blueprint_name": pc,
    "function_name": "AddMappingContext",
    "target": "EnhancedInputLocalPlayerSubsystem",
    "x": -100, "y": 600,
})
ue.set_pin_default(pc, add_mc["node_id"], "MappingContext",
    "/Game/Input/IMC_Default.IMC_Default")
ue.connect(get_sub["node_id"], "ReturnValue",
    add_mc["node_id"], "self", blueprint_name=pc)

# 接入 BeginPlay 执行链
ue.connect(begin_play_id, "then",
    add_mc["node_id"], "execute", blueprint_name=pc)
```

注意：`MappingContext` 是 object reference 类型的 pin，`set_pin_default` 和 `set_node_pin_default` 对 object reference pin 会静默失败。命令返回成功，`get_node_pins` 也显示 pin 值为空，但运行时该 pin 没有值。如果你需要 `AddMappingContext` 正常工作，更可靠的方式是复用模板中已经连线好的 PlayerController（如 `BP_FirstPersonPlayerController`），避免从零创建。

## SpectatorPawn 占用的按键

使用 SpectatorPawn 作为 DefaultPawnClass 时，以下按键已被占用，绑定到这些键的 Input Action 会被吞掉：

- W, A, S, D：移动
- Q, E：上升、下降
- C：可能与继承的 IMC 中的蹲下绑定冲突
- 方向键、鼠标按钮

安全的按键选择：Z, X, V, F, G, H, 数字键。数字键需要使用 `One`, `Two`, `Three` 等名称（主键盘），`1`, `2`, `3` 映射到小键盘。

## SpectatorPawn + AddMappingContext 运行时警告

当 GameMode 同时使用 SpectatorPawn（DefaultPawnClass）和模板 PlayerController（如 `BP_FirstPersonPlayerController`）时，模板 BeginPlay 中的 `AddMappingContext` 可能在 local player subsystem 就绪之前执行，产生如下运行时错误：

```
Accessed None trying to read property CallFunc_GetLocalPlayerSubsystem_ReturnValue
```

这个警告是表面性的。IMC 通常会在后续帧完成注册，Enhanced Input 按键映射仍然能正常工作。

## 完整示例：为角色添加蹲下功能

```python
from ue_bridge import UEBridge

with UEBridge() as ue:
    bp = "BP_ThirdPersonCharacter"

    # 1. 启用 CharacterMovement 的蹲下能力
    ue.raw_command("set_inherited_component_property", {
        "blueprint_name": bp,
        "component_name": "CharMoveComp",
        "property_name": "NavAgentProps.bCanCrouch",
        "property_value": True,
    })

    # 2. 创建 Input Action
    ue.create_input_action("IA_Crouch", value_type="Digital")

    # 3. 在 IMC 中绑定 C 键
    ue.add_key_mapping("IMC_Default", "IA_Crouch", "C")

    # 4. 添加 Blueprint 节点
    input_node = ue.add_enhanced_input_action_node(bp, "IA_Crouch",
        position=(-400, 1200))
    crouch_node = ue.add_function_node(bp, "Crouch",
        position=(0, 1100))
    uncrouch_node = ue.add_function_node(bp, "UnCrouch",
        position=(0, 1300))

    # 5. 连线
    ue.connect(input_node, "Started", crouch_node, "execute")
    ue.connect(input_node, "Completed", uncrouch_node, "execute")

    # 6. 编译并保存
    ue.compile(bp)
    ue.save_all()

    # 7. 验证 IMC 内容
    imc = ue.raw_command("read_imc", {"context_name": "IMC_Default"})
    for m in imc["mappings"]:
        if m["action_name"] == "IA_Crouch":
            print(f'Verified: {m["action_name"]} -> {m["key"]} '
                  f'triggers={m["action_triggers"]}')
```
