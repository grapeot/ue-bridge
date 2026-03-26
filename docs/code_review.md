# Code Review：C++ Action 文件拆分与测试覆盖

## 现状

C++ 侧 Action 文件总计 25,371 行，分布如下：

| 文件 | 行数 | 大小 | 状态 |
|------|------|------|------|
| NodeActions.cpp | 5,244 | 179K | 需要拆分 |
| UMGActions.cpp | 4,016 | 135K | 需要拆分 |
| MaterialActions.cpp | 3,919 | 135K | 需要拆分 |
| EditorActions.cpp | 3,570 | 119K | 需要拆分 |
| LayoutActions.cpp | 3,349 | 105K | 可观察 |
| GraphActions.cpp | 2,176 | 64K | 可观察 |
| BlueprintActions.cpp | 1,432 | 47K | 可接受 |
| ProjectActions.cpp | 638 | 21K | 良好 |
| EditorDiffActions.cpp | 556 | 19K | 良好 |
| EditorAction.cpp | 471 | 13K | 良好（基类） |

**结论：前四个文件（NodeActions、UMGActions、MaterialActions、EditorActions）都超过 3,500 行，是优先拆分对象。**

## 拆分建议

### NodeActions.cpp (5,244 行) — 最高优先级

这个文件包含了至少六种不同类型的节点操作，可以按功能拆分：

1. **NodeConnectionActions.cpp** — 连接、断开、pin 操作（connect, disconnect, get_pins, set_pin_default）
2. **NodeCRUDActions.cpp** — 节点的增删查改（find, delete, move, add_reroute, get_selected, set_selected, batch_select_and_act）
3. **EventNodeActions.cpp** — 事件节点（event, custom_event, enhanced_input_action, event_dispatcher 系列）
4. **VariableNodeActions.cpp** — 变量节点（variable add/get/set/delete/rename/default, function local variable）
5. **FunctionNodeActions.cpp** — 函数和控制流节点（function, branch, cast, self_reference, spawn_actor, sequence, macro, switch, make/break struct）
6. **GraphPatchActions.cpp** — 图操作（describe_graph, describe_graph_enhanced, apply_graph_patch, validate_graph_patch, export/import_nodes_to_text, comment 系列）

### UMGActions.cpp (4,016 行) — 高优先级

按 Widget 类型和操作类型拆分：

1. **WidgetBlueprintActions.cpp** — 蓝图级操作（create, delete, list_components, get_widget_tree）
2. **WidgetComponentActions.cpp** — 添加各种组件（text_block, button, image, progress_bar, slider, 各种 box/panel, generic_widget）
3. **WidgetPropertyActions.cpp** — 属性和文本操作（set_widget_properties, set_widget_text, set_slider_properties, set_combo_box_options）
4. **WidgetStructureActions.cpp** — 结构操作（reparent, add_child, delete, rename）
5. **WidgetBindingActions.cpp** — 绑定操作（bind_widget_event, set_text_block_binding, add_widget_to_viewport）
6. **MVVMActions.cpp** — MVVM 相关（add_viewmodel, add_binding, get_bindings, remove_binding, remove_viewmodel）

### MaterialActions.cpp (3,919 行)

1. **MaterialCRUDActions.cpp** — 材质的增删改查（create, compile, get_summary, set_property）
2. **MaterialExpressionActions.cpp** — 表达式节点操作（add, connect, set_property, remove）
3. **MaterialInstanceActions.cpp** — 材质实例和 Post Process Volume
4. **MaterialLayoutActions.cpp** — 材质编辑器布局和选择操作

### EditorActions.cpp (3,570 行)

1. **ActorActions.cpp** — Actor 操作（get, find, spawn, delete, set_transform, properties, rename, folder, select, outliner）
2. **ViewportActions.cpp** — Viewport 操作（focus, get/set_transform）
3. **AssetActions.cpp** — 资产操作（list, rename, get_thumbnail, get_selected, save_all, open_asset_editor）
4. **DiagnosticsActions.cpp** — 诊断操作（get_editor_logs, get_unreal_logs, is_ready, clear_logs, assert_log, get_blueprint_summary, describe_full）
5. **PIEActions.cpp** — PIE 控制（start_pie, stop_pie, get_pie_state）
6. **EditorLifecycleActions.cpp** — 编辑器控制（batch_execute, request_shutdown）

## 代码重复模式

跨文件观察到的重复 pattern：

1. **Widget 添加 boilerplate** — UMGActions.cpp 中每个 `Add*ToWidget` action 都有近乎相同的模式：FindWidgetBlueprintByName → 检查 RootCanvas → ConstructWidget → ApplyCanvasSlot → MarkDirty → 返回。可以提取一个 `AddWidgetHelper` 模板方法。

2. **Validate boilerplate** — 所有 action 的 `Validate()` 基本是检查必填参数是否存在，模式完全相同。可以用声明式参数列表替代手写 Validate。

3. **错误响应构造** — `FUEBridgeCommonUtils::CreateErrorResponse(FString::Printf(...))` 在每个文件中重复数百次。

## 测试覆盖

### C++ 侧

- `WorkflowAHealthTests.cpp` — 7 个健康检查测试
- `GraphNodeWorkflowTests.cpp` — graph/node 工作流测试

缺口：UMG、Material、Layout 没有 C++ 自动化测试。

### Python 侧

- `test_bridge.py` — 93 个测试（含 PIE 和 UMG wrapper 测试）
- `test_cli.py` — CLI 解析和 contract 测试
- `test_connection.py` — 连接层测试
- `test_package_contract.py` — 包导入 contract
- `test_integration.py` / `test_integration_workflow_a.py` — 集成测试（需要 UE 运行）

Python 侧覆盖率较好，但测试的是参数传递正确性（mock），不测试 C++ 行为。

### 测试覆盖优先级

在做 C++ 拆分时，应先确保有对应的 Python integration 测试或 C++ 自动化测试，否则拆分可能引入回归。建议拆分顺序与测试建立同步进行：先拆有测试保护的模块，再为没有测试的模块补测试后再拆。

## 执行建议

1. **不要一次性拆分所有文件。** 每次拆分一个文件，验证编译和测试通过后再 merge。
2. **从 EditorActions.cpp 的 PIEActions 开始**——最小、最独立、已有 Python 测试覆盖。
3. **NodeActions.cpp 拆分量最大**，但每个子模块边界清晰（事件节点 vs 变量节点 vs 函数节点），可以安全拆分。
4. **UMGActions.cpp 的 MVVM 部分**是最独立的子模块，可以先拆出来作为低风险试点。
5. 拆分过程中不改行为，纯文件搬移 + header 调整。
