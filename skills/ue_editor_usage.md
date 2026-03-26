# Skill: UE Editor 自动化 — 使用指南

## 核心概念

ue_bridge 是一个 Python 库，通过 TCP 连接 Unreal Editor 的 MCP 插件，执行编辑器操作。用法有两种：写 Python 脚本（推荐批量操作）、或用 CLI 单条执行。

## Python API 速查

### 连接与基础

```python
from src import UEBridge

ue = UEBridge()              # 自动连接 127.0.0.1:55558
ue.ping()                     # -> True
ue.save_all()                 # 保存所有
ue.get_context()              # 当前编辑器状态
ue.list_assets("/Game/ThirdPerson/Blueprints/")  # 列出资产
ue.close()                    # 断开

# 推荐用 context manager
with UEBridge() as ue:
    ue.ping()
```

### 场景操作

```python
actors = ue.get_actors()                    # 列出所有 Actor
actors = ue.find_actors("Wall*")            # 按名称搜索
ue.spawn_actor("StaticMeshActor", "Wall_01", location=(100, 0, 0))
ue.set_actor_transform("Wall_01", location=(200, 0, 0), scale=(2, 2, 1))
ue.delete_actor("Wall_01")
```

### Blueprint 属性

```python
summary = ue.get_blueprint_summary("BP_PlatformingCharacter")
ue.compile("BP_PlatformingCharacter")
ue.set_blueprint_property("BP_Foo", "SomeProperty", "value")
ue.add_component("BP_Foo", "BoxCollisionComponent", "MyCollider")
```

### Blueprint 节点与连线

```python
# 添加节点（返回 node_id）
input_node = ue.add_enhanced_input_action_node("BP_Foo", "IA_Crouch")
crouch_node = ue.add_function_node("BP_Foo", "Crouch")       # target 默认 "self"
uncrouch_node = ue.add_function_node("BP_Foo", "UnCrouch")

# 查看 pin
pins = ue.get_pins("BP_Foo", input_node)
# -> [{"name": "Started", "direction": "Output", ...}, ...]

# 连线
ue.connect(input_node, "Started", crouch_node, "execute")
ue.connect(input_node, "Completed", uncrouch_node, "execute")

# 编译
ue.compile("BP_Foo")
```

### Input 系统

```python
ue.create_input_action("IA_Crouch")                    # path 默认 /Game/Input/Actions
ue.add_key_mapping("IMC_Default", "IA_Crouch", "C")   # action_path 默认 /Game/Input/Actions
```

### 材质

```python
ue.create_colored_material("M_Red", color=(1, 0, 0, 1))
ue.compile_material("M_Red")
```

### 万能后门

所有 77 个 C++ 命令都可以通过 `raw_command` 调用：

```python
ue.raw_command("some_command", {"param1": "value1"})
```

## CLI 速查

```bash
python3 -m src ping
python3 -m src save
python3 -m src get-actors
python3 -m src list-assets --path /Game/ThirdPerson/
python3 -m src compile --blueprint BP_PlatformingCharacter
python3 -m src summary --blueprint BP_PlatformingCharacter
python3 -m src create-input-action --name IA_Foo
python3 -m src add-key-mapping --context IMC_Default --action IA_Foo --key F
python3 -m src spawn-actor --type StaticMeshActor --name Wall_01 --location 100,0,0
python3 -m src delete-actor --name Wall_01
python3 -m src raw get_context
python3 -m src raw compile_blueprint --params '{"blueprint_name":"BP_Foo"}'
```

## 已知限制

### 继承组件属性

`set_component_property` 只能操作 Blueprint 中显式添加的组件。对于继承自父类的组件（如 Character 的 CharacterMovement），使用 `set_inherited_component_property`：

```python
# 设置 CharacterMovement 的 bCanCrouch
ue.raw_command("set_inherited_component_property", {
    "blueprint_name": "BP_ThirdPersonCharacter",
    "component_name": "CharacterMovement",
    "property_name": "bCanCrouch",
    "property_value": True,
})
```

如果不确定组件名，故意传一个错误名称，错误信息会列出所有可用组件。

### IMC 读取和清理

```python
# 读取 IMC 完整内容（每条映射的 action、key、triggers）
imc = ue.raw_command("read_imc", {"context_name": "IMC_Default"})
for m in imc["mappings"]:
    print(f'{m["action_name"]} -> {m["key"]} triggers={m["action_triggers"]}')

# 删除特定映射（按 action_name + key 过滤）
ue.raw_command("remove_key_mapping_from_context", {
    "context_name": "IMC_Default",
    "action_name": "IA_Jump",
    "key": "C",
})
```

### 操作失败时抛异常

`UECommandError` 包含 error message 和 error_type。用 try/except 处理：

```python
from src.errors import UECommandError

try:
    ue.compile("BP_NonExistent")
except UECommandError as e:
    print(f"Failed: {e} (type: {e.error_type})")
```

### 需要 UE Editor 运行

所有操作都通过 TCP 发到编辑器执行。编辑器关闭时会抛 `UEConnectionError`。

## 重要工作原则

### 每次操作后都 save_all

通过 API 做的修改在内存中生效，但如果 UE Editor 关闭或崩溃时没保存，修改会丢失。**每个脚本结尾都要调 `ue.save_all()`**。

### C++ 修改需要重启 UE Editor

如果需要新的 C++ 插件能力（如新增 action），修改 C++ 代码后需要命令行编译 + 重启 UE Editor。Python 侧的修改不需要重启。

遇到需要 C++ 改动的场景时，按以下流程决策：
1. 先评估工作量（新增一个 action 通常 10-20 分钟编码 + 10 秒编译）
2. 告知用户：这个功能需要改 C++ 插件，预计 X 分钟，但需要你重启 UE Editor。要做吗？
3. 如果用户同意，执行改动、编译、提醒用户重启并保存
4. 如果用户拒绝，给出手动操作的替代方案

### 确认你操作的是正确的 Blueprint

不同 GameMode 使用不同的 Character Blueprint。用 World Settings 或 `describe_blueprint_full` 检查当前关卡用的是哪个 GameMode，追踪到它的 Default Pawn Class，确认那才是你应该编辑的 Blueprint。

## 完整示例：给角色添加蹲下功能

```python
import sys
sys.path.insert(0, "/path/to/combat_game/tools/ue_editor")
from src import UEBridge

with UEBridge() as ue:
    bp = "BP_ThirdPersonCharacter"  # 确认这是实际运行的角色 Blueprint

    # 1. 启用蹲下能力（继承组件属性）
    ue.raw_command("set_inherited_component_property", {
        "blueprint_name": bp,
        "component_name": "CharMoveComp",  # C++ 变量名，不是显示名
        "property_name": "NavAgentProps.bCanCrouch",  # 嵌套属性用点号分隔
        "property_value": True,
    })

    # 2. 创建 Input Action（自动带 Pressed+Released triggers）
    ue.create_input_action("IA_Crouch", value_type="Digital")

    # 3. 绑定 C 键到 IMC
    ue.add_key_mapping("IMC_Default", "IA_Crouch", "C")

    # 4. 在 Blueprint 里添加节点
    input_node = ue.add_enhanced_input_action_node(bp, "IA_Crouch", position=(-400, 1200))
    crouch_node = ue.add_function_node(bp, "Crouch", position=(0, 1100))
    uncrouch_node = ue.add_function_node(bp, "UnCrouch", position=(0, 1300))

    # 5. 连线
    ue.connect(input_node, "Started", crouch_node, "execute")
    ue.connect(input_node, "Completed", uncrouch_node, "execute")

    # 6. 编译并保存
    ue.compile(bp)
    ue.save_all()

    # 7. 验证
    imc = ue.raw_command("read_imc", {"context_name": "IMC_Default"})
    for m in imc["mappings"]:
        if m["action_name"] == "IA_Crouch":
            print(f'Verified: {m["action_name"]} -> {m["key"]} triggers={m["action_triggers"]}')
```
