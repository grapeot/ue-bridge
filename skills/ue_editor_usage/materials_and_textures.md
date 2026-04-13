← [返回总览](../ue_editor_usage.md)

# 材质、纹理与视觉调试

## 材质创建 API

基础材质创建和编译：

```python
ue.create_colored_material("M_Red", color=(1, 0, 0, 1))
ue.compile_material("M_Red")
```

材质表达式 API 细节：

- `add_material_expression` 的 `expression_class` 必须用短名：`TextureSample`、`VectorParameter`、`ScalarParameter`、`Constant`、`Add`、`Multiply`。不要用完整类名如 `MaterialExpressionConstant3Vector`。
- `node_name` 是输入参数（由你命名节点），不是返回值。
- `set_material_expression_property` 的 `property_value` 必须是字符串（UE 反射解析）。LinearColor 格式：`"(R=1.0,G=0.5,B=0.0,A=1.0)"`。
- `connect_material_expressions` 用于表达式节点之间的连接。`connect_to_material_output` 用于连接到材质主输入（BaseColor、EmissiveColor 等）。
- 材质默认路径 `/Game/Materials/`，引用格式 `/Game/Materials/M_Foo.M_Foo`。

### 场景 Actor 上应用材质

`set_static_mesh_properties` 只对 Blueprint 组件生效。场景中的 Actor 用以下方式：

```python
ue.raw_command("apply_material_to_actor", {
    "actor_name": full_name,  # 必须包含 UAID 后缀
    "material_path": "/Game/Materials/M_Foo.M_Foo",
})
```

注意：`apply_material_to_actor` 只影响编辑器中的 Actor 实例。PIE 运行时，Actor 从 Blueprint CDO 生成，可能仍使用默认材质。如果创建时已通过 `set_static_mesh_properties` 的 `materials` 参数设置了材质，CDO 中就已经是正确的。`apply_material_to_actor` 适合作为编辑器视口的视觉修正，不应作为主要材质赋值路径。

## 纹理导入

Bridge 提供 `import_asset` 命令，可以将外部文件（PNG、JPG、TGA、BMP、EXR 等图片格式）直接导入为 UE 资产，无需用户手动在编辑器中操作。

```python
# 单个文件导入
result = ue.import_asset(
    source_path="/absolute/path/to/card.png",  # 必须是绝对路径
    destination_path="/Game/CardArt",           # UE Content 路径
    asset_name="T_Card_0",                      # 可选，覆盖导入后的资产名
)
print(result)
# {'source_path': '...', 'destination_path': '/Game/CardArt',
#  'imported_asset_path': '/Game/CardArt/T_Card_0.T_Card_0',
#  'asset_name': 'T_Card_0', 'asset_class': 'Texture2D'}

# 批量导入
result = ue.import_assets([
    {"source_path": "/path/a.png", "destination_path": "/Game/Art"},
    {"source_path": "/path/b.png", "destination_path": "/Game/Art"},
])
# {'total': 2, 'succeeded': 2, 'failed': 0, 'results': [...]}
```

注意事项：
- 首次导入可正常工作；对已存在的同名资产重复导入可能触发 access violation（crash prevention 会阻止崩溃但返回错误）。导入前用 `list_assets` 检查目标路径下是否已有同名资产。
- 非图片格式（FBX 等）走的是 `IAssetTools::ImportAssets` 通用路径，行为可能与图片导入不同。
- 文件名必须是 ASCII 安全的（如 `T_Card_0.png`）。中文或 Unicode 文件名可能导致导入失败。

## Unlit 材质配方

在任意光照条件下保证材质可见的完整流程：

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

关键点：ShadingModel 设为 Unlit，纹理输出连接到 EmissiveColor（不是 BaseColor），这样不依赖场景光源就能显示纹理。

## 自动曝光

空关卡没有光源时，UE 自动曝光会适应黑暗环境并大幅放大 Emissive 输出，导致使用 Unlit Emissive 材质的物体过曝发白。

修复方法是在 `DefaultEngine.ini` 中禁用自动曝光：

```ini
[/Script/Engine.RendererSettings]
r.DefaultFeature.AutoExposure=0
```

此配置需要重启编辑器才生效。编辑器运行中修改文件对当前会话无效。

替代方案是添加 PostProcessVolume 并手动设置曝光参数，但 bridge 的 `spawn_actor` 不支持 `PostProcessVolume`，需要手动操作。

## 截图

`take_screenshot` 捕获视口缓冲区，但截图结果可能比用户在屏幕上看到的明显偏暗，尤其在暗场景中使用 Unlit Emissive 材质时。这是视口显示管线和截图捕获路径之间的 tonemapping/HDR 渲染差异。不要仅凭截图亮度判断材质是否正确，有疑问时请用户确认屏幕上的实际效果。

另外，`set_viewport_transform` 之后视口渲染不会立即更新。在 `take_screenshot` 之前对可见 Actor 调用 `select_actors` 可以强制刷新，否则截图可能显示过期或白屏内容。

## 踩坑记录

### add_material_expression 的 properties 对纹理不可靠

`add_material_expression` 的 `properties` 字段设置 Texture 行为不稳定：引用不存在的纹理会崩溃（access violation），引用存在的纹理也可能静默失败（渲染为灰白格子图案）。

推荐两步安全写法：

```python
# 第一步：创建节点（不带 properties）
ue.raw_command("add_material_expression", {
    "material_name": mat, "expression_class": "TextureSample",
    "node_name": "MyTex", "x": -300, "y": 0,
})

# 第二步：用 get_material_summary 获取内部节点名
summary = ue.raw_command("get_material_summary", {"material_name": mat})
internal_name = summary["expressions"][0]["node_name"]  # 如 "$expr_0"
ue.raw_command("set_material_expression_property", {
    "material_name": mat, "node_name": internal_name,
    "property_name": "Texture", "property_value": "/Game/CardArt/T_Card_0.T_Card_0",
})
```

关键点：`add_material_expression` 中传的 `node_name` 是用户标签，`set_material_expression_property` 需要 `get_material_summary` 返回的内部名称（如 `$expr_0`）。两者不是同一个名字空间。

### `get_material_summary` 不显示纹理引用

`get_material_summary` 返回的 `properties` 字段对 TextureSample 节点始终为空 `{}`，即使纹理已正确赋值。材质能正常编译和渲染，但无法通过 bridge API 验证纹理是否设置成功。

### 中文文件名问题

纹理 PNG 应使用 ASCII 安全的文件名（如 `T_Card_0.png`），无论是通过 `import_asset` 导入还是手动放入 `Content/`。UE 资产路径内部使用 ASCII，中文或 Unicode 文件名可能导致导入失败或资产引用异常。
