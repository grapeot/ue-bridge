← [返回总览](../ue_editor_usage.md)

# 常用模式与踩坑记录

## 常用模式

### Unlit 纹理材质

在没有光源的空关卡中，标准 Lit 材质会全黑。将 ShadingModel 设为 Unlit，纹理连接到 EmissiveColor，可以保证任何光照条件下都可见。

```python
ue.create_material("M_Name")
ue.raw_command("set_material_property", {
    "material_name": "M_Name", "property_name": "ShadingModel", "property_value": "Unlit"})

# 创建 TextureSample 节点（不带 properties，避免静默失败）
ue.raw_command("add_material_expression", {
    "material_name": "M_Name", "expression_class": "TextureSample",
    "node_name": "Tex", "x": -300, "y": 0})

# 用 get_material_summary 获取内部节点名，再设置纹理
summary = ue.raw_command("get_material_summary", {"material_name": "M_Name"})
internal_name = summary["expressions"][0]["node_name"]  # 如 "$expr_0"
ue.raw_command("set_material_expression_property", {
    "material_name": "M_Name", "node_name": internal_name,
    "property_name": "Texture", "property_value": "/Game/Textures/T_Foo.T_Foo"})

ue.raw_command("connect_to_material_output", {
    "material_name": "M_Name", "source_node": internal_name,
    "source_output": "RGB", "material_property": "EmissiveColor"})
ue.compile_material("M_Name")
```

### 卡牌竖版朝向（面向 -X 摄像机）

使用 `Cube` 基础网格（不要用 `Plane`，Plane 面朝 +Z 上方，Yaw 旋转无法使其面向摄像机）。Scale 设为 `(width, 0.03, height)`，其中 Y 维度极薄作为厚度。Yaw 设为 90 度让薄面朝向摄像机。如果需要扇形排列多张卡牌，在 90 度基础上加偏移：`Yaw = 90 + offset`。

### SpectatorPawn 用于空关卡

没有地面的关卡中，默认 Pawn 会一直下坠。改用 SpectatorPawn 作为 DefaultPawnClass，可以用 WASD 飞行、右键拖拽转向。

```python
ue.create_blueprint("BP_GM", parent_class="GameModeBase", path="/Game/")
ue.set_blueprint_property("BP_GM", "DefaultPawnClass", "/Script/Engine.SpectatorPawn")
ue.compile("BP_GM")
ue.set_actor_property("WorldSettings", "DefaultGameMode", "/Game/BP_GM.BP_GM_C")
```

### 场景 Actor 的材质指定

`set_static_mesh_properties` 只对 Blueprint 组件生效。如果需要对已在场景中的 Actor 实例设置材质，用 `apply_material_to_actor`：

```python
ue.raw_command("apply_material_to_actor", {
    "actor_name": full_name,  # 必须包含 UAID 后缀
    "material_path": "/Game/Materials/M_Foo.M_Foo",
})
```

### 材质表达式 API 要点

`expression_class` 必须用短名：`TextureSample`、`VectorParameter`、`ScalarParameter`、`Constant`、`Add`、`Multiply`，不能用全称如 `MaterialExpressionConstant3Vector`。`node_name` 是调用方自己起的名字，不是返回值。`property_value` 必须是字符串，LinearColor 的格式为 `"(R=1.0,G=0.5,B=0.0,A=1.0)"`。`connect_material_expressions` 连接表达式节点之间的线，`connect_to_material_output` 连接到材质主输出（BaseColor、EmissiveColor 等）。材质默认路径为 `/Game/Materials/`，引用格式为 `/Game/Materials/M_Foo.M_Foo`。

### 继承组件属性的修改

`set_component_property` 只能修改 Blueprint 中显式添加的组件。对于从父类继承的组件（如 Character 的 CharacterMovement），用 `set_inherited_component_property`：

```python
ue.raw_command("set_inherited_component_property", {
    "blueprint_name": "BP_ThirdPersonCharacter",
    "component_name": "CharacterMovement",
    "property_name": "bCanCrouch",
    "property_value": True,
})
```

如果不确定组件名称，故意传一个错的名字，报错信息会列出所有可用组件。

### IMC 的读取与清理

```python
# 读取 IMC 全部内容
imc = ue.raw_command("read_imc", {"context_name": "IMC_Default"})
for m in imc["mappings"]:
    print(f'{m["action_name"]} -> {m["key"]} triggers={m["action_triggers"]}')

# 删除指定映射
ue.raw_command("remove_key_mapping_from_context", {
    "context_name": "IMC_Default",
    "action_name": "IA_Jump",
    "key": "C",
})
```

### 错误处理

`UECommandError` 包含错误信息和错误类型，用 try/except 处理：

```python
from ue_bridge.errors import UECommandError

try:
    ue.compile("BP_NonExistent")
except UECommandError as e:
    print(f"Failed: {e} (type: {e.error_type})")
```

编辑器未运行时，所有操作都会抛出 `UEConnectionError`。

## 工作原则

### 每批操作后保存

API 的变更只在内存中生效，如果 UE 崩溃则全部丢失。每段脚本末尾都要调用 `ue.save_all()`。

### C++ 改动需要重启编辑器

新增 C++ 插件功能（如新 action）需要命令行编译后重启编辑器。Python 端的改动不需要重启。需要 C++ 改动时，先向用户说明需要重启，得到确认后再进行。

### 确认编辑的是正确的 Blueprint

不同 GameMode 使用不同的 Character Blueprint。编辑前先检查 World Settings 或用 `get_blueprint_summary` 追溯 GameMode 到 Default Pawn Class 的链路。

### 不要在 AnimBP CDO 上用 set_object_property

`set_object_property` 会在 EventGraph 中注入 Set 节点，而不是直接修改 CDO。对 AnimInstance 属性（如 `RootMotionMode`）使用它会导致 AnimBP 被污染：每次调用新增一个 Set 节点，蓝图累积编译错误，且无法撤销。唯一修复方式是用 `find_blueprint_nodes` + `delete_blueprint_node` 手动删除所有被注入的节点。

正确做法是在 `Event Blueprint Initialize Animation` 中添加 `SetRootMotionMode` 函数调用节点：

```python
node = ue.raw_command("add_blueprint_function_node", {
    "blueprint_name": "ABP_Unarmed",
    "graph_name": "EventGraph",
    "target": "self",
    "function_name": "SetRootMotionMode",
    "x": 160, "y": -760,
})
ue.raw_command("set_node_pin_default", {
    "blueprint_name": "ABP_Unarmed",
    "node_id": node["node_id"],
    "pin_name": "Value",
    "default_value": "IgnoreRootMotion",
})
```

### Root motion 动画会导致角色飘走

带有根骨骼位移的动画（dash、sprint、attack、vault 等）会将位移应用到角色胶囊体上，角色会按动画速度飞出去。症状是角色在播放特定动画时瞬间冲出地图。预防措施：不要把移动动画当作站立状态的占位动画；如果必须用，全局关闭 root motion；引擎插件的动画资产可能无法在项目本地 AnimBP 中加载，赋值后立即测试编译。

### AnimBP 状态机编辑需要先 open_asset_editor

`list_anim_states`、`add_anim_state`、`add_anim_transition` 等命令操作的是内存中的状态机图。如果 AnimBP 没有在编辑器中打开，命令会报 "state machine not found"。操作前先调用：

```python
ue.raw_command("open_asset_editor", {
    "asset_path": "/Game/Characters/Mannequins/Anims/Unarmed/ABP_Unarmed.ABP_Unarmed"
})
```

打开后，用短名（如 `ABP_Unarmed`）作为 `blueprint_name` 即可，完整包路径可能解析失败。

### AnimBP compile 返回值可能误导

`compile_blueprint` 返回的 `saved_packages_count: 0` 即使保存成功也是 0，因为 bridge 的 dirty tracking 和 UE 的 `FEditorFileUtils::GetDirtyPackages()` 是独立系统。判断编译是否成功应看 `compiled: true` 和 `error_count: 0`，不要看 `saved_packages_count`。

### Content 目录不在 git 中

UE 项目的 `Content/` 文件夹通常被 gitignore（二进制 `.uasset` 文件）。bridge 操作如果损坏了资产，没有 `git checkout` 的恢复路径。高风险操作前可以手动备份 `.uasset` 文件。如果 `set_object_property` 污染了 AnimBP，用 `find_blueprint_nodes` + `delete_blueprint_node` 找到并删除所有注入的节点，然后重新编译。

## 已知限制

### UE 编辑器必须运行

所有操作都通过 TCP 发往编辑器。编辑器关闭时会抛出 `UEConnectionError`。

### 没有 import_asset 命令

bridge 没有资产导入命令。PNG 文件放到 `Content/` 不会自动导入为 uasset。`execute_console_command` 的各种 Import 命令也都无效。解决方式：编辑器运行时将 PNG 复制到 `Content/<subfolder>/`，UE 会弹出导入对话框，用户点击 Import All。导入后用 `list_assets` 验证。不过在 UE 5.7 上，编辑器启动前放入的 PNG 可能也会自动导入，行为取决于子目录是否已有对应 `.uasset`，以 `list_assets` 的实际结果为准。

### 对象引用类型的 pin 不能通过 set_pin_default 设置

`set_pin_default` 和 `set_node_pin_default` 对对象引用类型的 pin（如 `AddMappingContext` 的 `MappingContext` pin）会静默失败。命令返回成功，但 `get_node_pins` 显示 pin 值为空，运行时也没有值。解决方式：使用模板自带的、已经接好对象引用的 PlayerController（如 `BP_FirstPersonPlayerController`），不要新建需要手动接 `AddMappingContext` 的 PlayerController。

### get_material_summary 不显示 TextureSample 的纹理引用

`get_material_summary` 返回的 TextureSample 节点的 `properties` 字段始终为空 `{}`，即使纹理已正确赋值。纹理确实设置成功了（材质可以编译和渲染），但无法通过 bridge API 验证。

### PostProcessVolume 不能通过 bridge 创建

`spawn_actor` 不支持 `PostProcessVolume`。需要手动 exposure 控制时，改用 `DefaultEngine.ini` 配置。

## 踩坑记录

### Actor 名称有 UAID 后缀（编辑器模式）

`spawn_blueprint_actor("BP_Foo", "MyActor")` 在编辑器中实际创建的是 `MyActor_UAID_XXXX`。要找到完整名称，用 `get_actors()` 配合前缀匹配。`find_actors()` 的模式匹配不可靠。PIE 模式下例外：`get_pie_actors()` 返回的是干净的名称如 `CardActor_0`，`set_actor_transform()` 可以直接用这些名称。

### spawn_blueprint_actor 不应用 scale

`spawn_blueprint_actor` 的 scale 参数会被忽略。spawn 之后必须调用 `set_actor_transform()` 来设置缩放。

### connect() 需要 blueprint_name 参数

`ue.connect(source, pin, target, pin)` 如果不传 `blueprint_name` 会报 "Source or target node not found"。必须显式传 `blueprint_name=bp`。

### set_blueprint_property 用于 CDO 属性

`set_object_property` 会在 EventGraph 中注入 Set 节点。设置 DefaultPawnClass、PlayerControllerClass 等 class-default 属性时，用 `set_blueprint_property`。

### take_screenshot 需要先刷新 viewport

`set_viewport_transform` 之后 viewport 不会立刻更新渲染。截图前先对一个可见 Actor 调用 `select_actors` 强制重绘，否则截图可能是白屏或旧画面。

### execute_console_command 不能用 Python scripting

`execute_console_command` 配合 `py "import unreal; ..."` 会导致 UE 崩溃（access violation）。不要用它执行 Python 脚本，改用 bridge 的专用命令或手动编辑器操作。

### CreateWidget 是 K2Node

`CreateWidget` 不能通过 `add_function_node` 创建，它是特殊的 UK2Node 而不是普通函数。UMG Widget 的显示需要通过已有 K2Node 的 Blueprint 接线（BeginPlay -> CreateWidget -> AddToViewport），或者用 `PrintString` 作为运行时文字显示的替代方案。

### 数学和逻辑节点的 target 是 KismetMathLibrary

算术和比较节点需要指定 `target='KismetMathLibrary'`：

```python
ue.raw_command("add_blueprint_function_node", {
    "blueprint_name": bp,
    "function_name": "Add_IntInt",  # 也包括 Percent_IntInt, EqualEqual_IntInt
    "target": "KismetMathLibrary",
    "x": 0, "y": 0,
})
```

### GetActorOfClass + SetActorScale3D 在 PIE 中正常工作

`GetActorOfClass`（target 为 `GameplayStatics`）和 `SetActorScale3D` 都可以作为 Blueprint 函数节点在 PIE 中正确执行。bridge 的 `set_actor_transform` 在 PIE 中也可以直接操作 Actor。

### Branch 节点打断顺序执行链

Branch 节点有 `then`（True）和 `else`（False）两个输出，不能把两条路径重新汇合到同一个下游节点。处理"对列表中每个元素做条件操作"的模式：先用一条顺序链将所有元素设为默认状态，然后对每个元素用 Branch 检查条件，只修改匹配的那个，通过 `else` pin 串联各个 Branch。

### .uproject 必须声明 UEBridgeEditor 插件

把插件放到 `Plugins/UEBridgeEditor/` 目录下还不够，`.uproject` 文件的 `Plugins` 数组中也要加上：

```json
{
    "Name": "UEBridgeEditor",
    "Enabled": true
}
```

否则 UE 加载项目但不会启动 bridge 的 TCP 监听（端口 55558）。

### new_level 会覆盖同名关卡

`new_level` 如果目标名称已存在，会创建一个全新的空关卡，之前放置的所有 Actor 都会丢失。bridge 没有 `open_level` 或 `load_level` 命令。如果需要重启后回到某个关卡，可以在 `DefaultEngine.ini` 中设置 `EditorStartupMap`，让编辑器启动时自动打开目标关卡。

### take_screenshot 可能比屏幕显示更暗

截图捕获的是 viewport buffer，结果可能比用户在屏幕上看到的明显偏暗，尤其是空暗场景中的 Unlit Emissive 材质。这是 viewport 显示管线和截图捕获路径的 tonemapping/HDR 渲染差异。不要仅凭截图亮度判断材质是否正确，有疑问时让用户确认屏幕实际显示。

### Auto-exposure 配置需要重启编辑器

`DefaultEngine.ini` 中的 `r.DefaultFeature.AutoExposure=0` 设置只在重启编辑器后生效。编辑器运行期间修改该文件对当前会话无影响。修改渲染器设置后要安排一次重启。

空暗关卡中 UE 的 auto-exposure 会对黑暗环境做增益补偿，将 Emissive 输出放大到过曝（纯白）。在 `DefaultEngine.ini` 中关闭：

```ini
[/Script/Engine.RendererSettings]
r.DefaultFeature.AutoExposure=0
```

### 中文/Unicode 文件名可能有问题

将纹理 PNG 放入 `Content/` 导入前，重命名为 ASCII 安全的文件名（如 `T_Card_0.png`）。UE 资产路径内部使用 ASCII，Unicode 文件名可能导致导入失败或资产引用异常。

### apply_material_to_actor 只影响场景实例

`apply_material_to_actor` 设置的是关卡编辑器中的 Actor 实例的材质。PIE 中的 Actor 是从 Blueprint CDO 生成的，可能仍使用默认材质。如果创建时已通过 `set_static_mesh_properties` 的 `materials` 参数设置了材质，CDO 已经是正确的。`apply_material_to_actor` 适合用作编辑器 viewport 的视觉修正，不是主要的材质赋值路径。

### SpectatorPawn + FirstPerson PlayerController 的 AddMappingContext 警告

自定义 GameMode 使用 `SpectatorPawn` 为 DefaultPawnClass、`BP_FirstPersonPlayerController` 为 PlayerControllerClass 时，模板的 BeginPlay 中 `AddMappingContext` 节点可能在 local player subsystem 就绪之前触发，产生 "Accessed None trying to read property CallFunc_GetLocalPlayerSubsystem_ReturnValue" 错误。Enhanced Input 键位映射通常仍然有效（IMC 会在后续帧注册），但日志中会有噪音警告。

### add_material_expression 的 properties 对纹理不可靠

`add_material_expression` 的 `properties` 字段设置 Texture 引用（如 `{"Texture": "/Game/CardArt/T_Card_0.T_Card_0"}`）行为不稳定：引用不存在的纹理会崩溃（access violation），引用存在的纹理也可能静默失败（编译通过但渲染为灰白格子图案）。

推荐的两步安全写法：

```python
# 第一步：创建 TextureSample 节点（不带 properties）
ue.raw_command("add_material_expression", {
    "material_name": mat, "expression_class": "TextureSample",
    "node_name": "MyTex", "x": -300, "y": 0,
})

# 第二步：用 get_material_summary 找到内部节点名，再设置 Texture
summary = ue.raw_command("get_material_summary", {"material_name": mat})
internal_name = summary["expressions"][0]["node_name"]  # 通常是 "$expr_0"
ue.raw_command("set_material_expression_property", {
    "material_name": mat, "node_name": internal_name,
    "property_name": "Texture", "property_value": "/Game/CardArt/T_Card_0.T_Card_0",
})
```

注意：`add_material_expression` 中你传的 `node_name` 是用户标签，但 `set_material_expression_property` 需要 `get_material_summary` 返回的内部名称（如 `$expr_0`）。两者不是同一个名字空间。

### 卡牌用 Cube 不用 Plane

UE 的 `Plane` 基础网格朝向 +Z（面朝上方），用 Yaw 旋转无法使其面向摄像机。做卡牌等扁平物体应使用 `Cube`，通过 scale 把一个维度压扁：Scale `(宽度, 0.03, 高度)` 创建极薄的卡牌形状，Yaw 旋转控制朝向。

### Enhanced Input 必须在 PlayerController 中接线

SpectatorPawn 子类的 EventGraph 中接收不到 Enhanced Input Action 事件，事件会静默不触发。Enhanced Input 处理逻辑应该写在 PlayerController Blueprint 中（如 `BP_ThirdPersonPlayerController`）。

### PlayerController 必须在 BeginPlay 中注册 IMC

创建 Input Action 并添加到 IMC 还不够，IMC 必须在运行时通过 `EnhancedInputLocalPlayerSubsystem` 注册。否则 Enhanced Input Action 事件静默不触发。ThirdPerson 模板的 PC 自动做了这步，新建的 PlayerController Blueprint 没有。

### SpectatorPawn 占用 WASD、Q、E、C 键

使用 SpectatorPawn 时避免绑定：W/A/S/D（移动）、Q/E（上下）、C（可能与继承的 IMC 绑定冲突）、方向键、鼠标按键。安全的按键：Z、X、V、F、G、H、数字键（用 `One`、`Two`、`Three` 表示主键盘数字键，`1`、`2`、`3` 对应的是小键盘）。
