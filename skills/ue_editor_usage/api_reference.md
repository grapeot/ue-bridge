← [返回总览](../ue_editor_usage.md)

# API 速查

## CLI 命令速查

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
ue-bridge start-pie                              # 启动 PIE（默认: SelectedViewport）
ue-bridge start-pie --mode Simulate               # 以 Simulate 模式启动
ue-bridge stop-pie                                # 停止 PIE
ue-bridge pie-state                               # 查询 PIE 状态（Running/Stopped）
ue-bridge raw get_context
ue-bridge raw compile_blueprint --params '{"blueprint_name":"BP_Foo"}'
```

也可以在 `python/` 目录下使用 `python3 -m ue_bridge <command>`（标准方式）或 `python3 -m src <command>`（兼容旧版）。

## Python API 速查

### 连接

```python
from ue_bridge import UEBridge

with UEBridge() as ue:
    ue.ping()          # -> True
    ue.save_all()
    ue.get_context()
    ue.list_assets("/Game/ThirdPerson/Blueprints/")
```

始终使用上下文管理器（`with`）以确保连接正确关闭。

### 场景操作

```python
actors = ue.get_actors()
actors = ue.find_actors("Wall*")
ue.spawn_actor("StaticMeshActor", "Wall_01", location=(100, 0, 0))
ue.set_actor_transform("Wall_01", location=(200, 0, 0), scale=(2, 2, 1))
ue.delete_actor("Wall_01")
```

### Blueprint 属性

```python
summary = ue.get_blueprint_summary("BP_ThirdPersonCharacter")
ue.compile("BP_ThirdPersonCharacter")
ue.set_blueprint_property("BP_Foo", "SomeProperty", "value")
ue.add_component("BP_Foo", "BoxCollisionComponent", "MyCollider")
```

### Blueprint 节点与连线

```python
# 添加节点（每个调用返回一个 node_id）
input_node = ue.add_enhanced_input_action_node("BP_Foo", "IA_Crouch")
crouch_node = ue.add_function_node("BP_Foo", "Crouch")       # target 默认为 "self"
uncrouch_node = ue.add_function_node("BP_Foo", "UnCrouch")

# 查看引脚
pins = ue.get_pins("BP_Foo", input_node)
# -> [{"name": "Started", "direction": "Output", ...}, ...]

# 连线
ue.connect(input_node, "Started", crouch_node, "execute")
ue.connect(input_node, "Completed", uncrouch_node, "execute")

# 编译
ue.compile("BP_Foo")
```

### 输入系统

```python
ue.create_input_action("IA_Crouch")                    # path 默认为 /Game/Input/Actions
ue.add_key_mapping("IMC_Default", "IA_Crouch", "C")   # action_path 默认为 /Game/Input/Actions
```

### PIE（编辑器内运行）

```python
# 启动 PIE 会话
ue.start_pie()                          # 默认: SelectedViewport
ue.start_pie(mode="Simulate")          # Simulate 模式
ue.start_pie(mode="NewWindow")         # 独立窗口

# 查询状态（start_pie 后轮询此方法，启动是异步的）
state = ue.get_pie_state()
print(state["state"])                   # "Running" 或 "Stopped"

# 停止
ue.stop_pie()
```

PIE 用于运行时验证。构建 Blueprint 逻辑后，启动 PIE，再用 `get_unreal_logs()` 检查运行时错误。

### UMG Widget

```python
# 创建 Widget Blueprint
ue.create_widget_blueprint("WBP_HUD", path="/Game/UI/")

# 添加组件
ue.add_text_block("WBP_HUD", "ScoreText", text="Score: 0")
ue.add_progress_bar("WBP_HUD", "BossHP", percent=1.0, color=(1, 0, 0, 1))
ue.add_image("WBP_HUD", "LifeIcon", position=(10, 10), size=(32, 32))

# 布局容器
ue.add_canvas_panel("WBP_HUD", "MainCanvas")
ue.add_vertical_box("WBP_HUD", "InfoBox")
ue.add_horizontal_box("WBP_HUD", "LivesRow")

# 设置文本和属性
ue.set_widget_text("WBP_HUD", "ScoreText", "Score: 1000", font_size=24)
ue.set_widget_properties("WBP_HUD", "ScoreText", position=[100, 50], visibility="Visible")

# 将文本绑定到 Blueprint 变量以支持运行时更新
ue.set_text_block_binding("WBP_HUD", "ScoreText", "ScoreVar")

# 查看 Widget 树
tree = ue.get_widget_tree("WBP_HUD")
components = ue.list_widget_components("WBP_HUD")

# 获取类路径（用于 Blueprint 中 CreateWidget + AddToViewport）
info = ue.add_widget_to_viewport("WBP_HUD", z_order=10)
print(info["class_path"])  # 在 Blueprint 中用此路径创建并显示 Widget

# 结构操作
ue.reparent_widgets("WBP_HUD", "MainCanvas", ["ScoreText", "BossHP"])
ue.rename_widget("WBP_HUD", "ScoreText", "PlayerScore")
ue.delete_widget("WBP_HUD", "OldWidget")
```

### 材质

```python
ue.create_colored_material("M_Red", color=(1, 0, 0, 1))
ue.compile_material("M_Red")
```

### Raw Commands（兜底方案）

所有 77+ 个 C++ action 均可通过 `raw_command` 调用，用于高层 API 尚未封装的功能：

```python
ue.raw_command("some_command", {"param1": "value1"})
```

优先使用高层方法，仅在缺少对应封装时使用 `raw_command`。
