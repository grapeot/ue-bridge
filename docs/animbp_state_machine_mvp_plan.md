# ue-bridge AnimBP 状态机编辑 MVP 实施方案

## 目标

在现有 ue-bridge C++ 插件上，补齐最小可用的 Animation Blueprint 状态机编辑能力，支持以下闭环：

1. 打开指定 AnimBP
2. 读取状态机结构
3. 新增状态
4. 新增双向 transition
5. 把 transition 规则设置成单个布尔变量判断
6. 给状态绑定一个 AnimSequence
7. 编译并保存

这里严格控制在 MVP 范围内，只支持：

- AnimBP 内已有状态机的读取与修改
- 普通 State，不支持 Conduit
- 单个布尔变量驱动的 transition rule
- State 内播放单个 AnimSequence
- 不设计 Blend Space、复杂 rule graph、嵌套 state machine

## 设计原则

- 命令命名继续沿用现有 snake_case 风格
- 输入保持 raw_command 的 JSON 形式
- 输出保持 ue-bridge 现有风格：顶层 `success: true/false`，成功时平铺结果字段，失败时返回 `error` 和 `error_type`
- 新 Action 尽量复用现有 `FBlueprintAction` / `FBlueprintNodeAction` 的验证、上下文、dirty 标记和编译路径
- 明确要求 AnimBP 先通过现有 `open_asset_editor` 打开。新命令不承担打开编辑器职责

## MVP 命令集

建议新增 5 个命令，复用 3 个现有命令：

- 新增：`list_anim_states`
- 新增：`add_anim_state`
- 新增：`add_anim_transition`
- 新增：`set_anim_transition_rule`
- 新增：`set_anim_state_animation`
- 复用：`open_asset_editor`
- 复用：`compile_blueprint`
- 复用：`save_all`

这里故意不增加 `add_bidirectional_anim_transition`。最小 API 面应该让一个 `add_anim_transition` 支持单向边，调用两次就能完成双向连接。这样和现有 `connect_blueprint_nodes` 的粒度一致，也更容易调试。

## 命令依赖关系

完整调用链建议如下：

1. `open_asset_editor`
2. `list_anim_states`
3. `add_anim_state`
4. `add_anim_transition`：Idle/Run -> Crouch
5. `add_anim_transition`：Crouch -> Idle/Run
6. `set_anim_transition_rule`：Idle/Run -> Crouch，`IsCrouching == true`
7. `set_anim_transition_rule`：Crouch -> Idle/Run，`IsCrouching == false`
8. `set_anim_state_animation`：Crouch 绑定 crouch AnimSequence
9. `compile_blueprint`
10. `save_all`

依赖约束：

- 所有新命令都依赖目标 AnimBP 已打开，且必须能通过 `blueprint_name` 找到
- `add_anim_state` 依赖目标 state machine 已存在
- `add_anim_transition` 依赖 source state 和 target state 已存在
- `set_anim_transition_rule` 依赖对应 transition 已存在，且布尔变量已经存在于 AnimBP 或其父类中
- `set_anim_state_animation` 依赖 state 已存在，且资源路径对应 `UAnimSequence`

## 每个命令的详细设计

### 1. `list_anim_states`

#### 作用

列出 AnimBP 中某个状态机的状态、入口、transition，用于后续命令拿到稳定标识并确认现有结构。

#### 输入 JSON

```json
{
  "blueprint_name": "ABP_Unarmed",
  "state_machine_name": "Locomotion"
}
```

可选扩展：后续如果需要支持多状态机批量列出，可以加入 `include_all_state_machines: true`。MVP 先不做。

#### 输出 JSON

```json
{
  "success": true,
  "blueprint_name": "ABP_Unarmed",
  "state_machine_name": "Locomotion",
  "state_machine_node_id": "...",
  "entry_node_id": "...",
  "states": [
    {
      "state_name": "Idle/Run",
      "state_node_id": "...",
      "bound_graph_name": "Idle_Run",
      "state_type": "SingleAnimation"
    }
  ],
  "transitions": [
    {
      "transition_node_id": "...",
      "from_state": "Idle/Run",
      "to_state": "Crouch",
      "rule_graph_name": "TransitionRule_...",
      "crossfade_duration": 0.2,
      "priority_order": 0
    }
  ]
}
```

#### 使用的 C++ 类与方法

- `UAnimBlueprint`
- `FBlueprintEditorUtils::GetAllGraphs`
- `UAnimGraphNode_StateMachineBase`
- `UAnimationStateMachineGraph`
- `UAnimStateEntryNode`
- `UAnimStateNode`
- `UAnimStateTransitionNode`
- `UEdGraphNode::NodeGuid`
- `UEdGraphNode::GetNodeTitle`

推荐内部实现：

1. 先把 `UBlueprint*` 强转成 `UAnimBlueprint*`
2. 遍历 Blueprint 所有 graph，找到承载状态机的 `UAnimGraphNode_StateMachineBase`
3. 用 `EditorStateMachineGraph` 拿到 `UAnimationStateMachineGraph`
4. 遍历 `Graph->Nodes`，分别序列化 entry/state/transition

#### 对齐现有 Action 模式

最接近 `FDescribeGraphAction` 和 `FGraphDescribeEnhancedAction`。本质是一个只读拓扑描述动作。

#### 依赖

- 依赖 `open_asset_editor`
- 后续的 `add_anim_state` / `add_anim_transition` / `set_anim_transition_rule` / `set_anim_state_animation` 都依赖它返回的结构信息做确认

### 2. `add_anim_state`

#### 作用

在指定状态机里新增一个 State 节点，并自动创建该 State 的 BoundGraph。

#### 输入 JSON

```json
{
  "blueprint_name": "ABP_Unarmed",
  "state_machine_name": "Locomotion",
  "state_name": "Crouch",
  "node_position": [900, 300]
}
```

说明：

- `node_position` 复用现有节点命令风格
- MVP 不暴露 `state_type`。默认创建 `AST_SingleAnimation`

#### 输出 JSON

```json
{
  "success": true,
  "state_machine_name": "Locomotion",
  "state_name": "Crouch",
  "state_node_id": "...",
  "bound_graph_name": "Crouch"
}
```

#### 使用的 C++ 类与方法

- `NewObject<UAnimStateNode>(StateMachineGraph)`
- `UAnimationStateMachineGraph::AddNode`
- `UAnimStateNode::PostPlacedNewNode`
- `UAnimStateNode::AllocateDefaultPins`
- `UAnimStateNode::BoundGraph`
- `FBlueprintEditorUtils::MarkBlueprintAsModified`

实现建议：

1. 定位 `UAnimationStateMachineGraph`
2. 检查同名 state 是否已存在
3. `NewObject<UAnimStateNode>(Graph)` 创建节点
4. 设置 `NodePosX/Y` 与显示名称
5. `Graph->AddNode(Node, true, true)`
6. 调用 `PostPlacedNewNode()`，让 UE 自动创建内部 `BoundGraph`
7. 标脏并刷新 Blueprint

#### 对齐现有 Action 模式

最接近 `FAddBlueprintEventNodeAction` 和 `FAddBlueprintFunctionNodeAction` 的创建节点流程。

#### 依赖

- 依赖 `open_asset_editor`
- 建议在 `list_anim_states` 后调用，用于确认状态机名称与现有布局
- `add_anim_transition` 和 `set_anim_state_animation` 依赖它创建出的 state

### 3. `add_anim_transition`

#### 作用

在两个已有 state 之间创建一条单向 transition。

#### 输入 JSON

```json
{
  "blueprint_name": "ABP_Unarmed",
  "state_machine_name": "Locomotion",
  "from_state": "Idle/Run",
  "to_state": "Crouch",
  "crossfade_duration": 0.2,
  "priority_order": 0
}
```

#### 输出 JSON

```json
{
  "success": true,
  "state_machine_name": "Locomotion",
  "from_state": "Idle/Run",
  "to_state": "Crouch",
  "transition_node_id": "...",
  "rule_graph_name": "TransitionRule_IdleRun_To_Crouch",
  "crossfade_duration": 0.2,
  "priority_order": 0
}
```

#### 使用的 C++ 类与方法

- `NewObject<UAnimStateTransitionNode>(StateMachineGraph)`
- `UAnimationStateMachineGraph::AddNode`
- `UAnimStateTransitionNode::PostPlacedNewNode`
- `UAnimStateTransitionNode::CreateConnections(PreviousState, NextState)`
- `UAnimStateTransitionNode::BoundGraph`
- `UAnimStateTransitionNode::CrossfadeDuration`
- `UAnimStateTransitionNode::PriorityOrder`
- `UAnimationStateMachineSchema`

实现建议：

1. 在状态机图中找到 `from_state` 和 `to_state`
2. 校验是否已经存在同方向 transition
3. 创建 `UAnimStateTransitionNode`
4. `Graph->AddNode(TransitionNode, true, true)`
5. 调用 `PostPlacedNewNode()` 和 `CreateConnections(FromState, ToState)`
6. 设置 `CrossfadeDuration`、`PriorityOrder`
7. 标脏

#### 对齐现有 Action 模式

最接近 `FConnectBlueprintNodesAction`，因为它本质上也是利用 schema 在两个节点之间建立合法连接。

#### 依赖

- 依赖 `from_state`、`to_state` 已存在
- 双向 transition 通过调用两次完成
- `set_anim_transition_rule` 依赖它创建出的 transition

### 4. `set_anim_transition_rule`

#### 作用

把某条 transition 的 rule graph 重写成最简单的布尔变量判断：

- `expected_value: true` 表示变量为 true 时通过
- `expected_value: false` 表示变量为 false 时通过

这正好覆盖 crouch 的两个方向。

#### 输入 JSON

```json
{
  "blueprint_name": "ABP_Unarmed",
  "state_machine_name": "Locomotion",
  "from_state": "Idle/Run",
  "to_state": "Crouch",
  "bool_variable_name": "IsCrouching",
  "expected_value": true
}
```

反向 transition：

```json
{
  "blueprint_name": "ABP_Unarmed",
  "state_machine_name": "Locomotion",
  "from_state": "Crouch",
  "to_state": "Idle/Run",
  "bool_variable_name": "IsCrouching",
  "expected_value": false
}
```

#### 输出 JSON

```json
{
  "success": true,
  "transition_node_id": "...",
  "from_state": "Idle/Run",
  "to_state": "Crouch",
  "bool_variable_name": "IsCrouching",
  "expected_value": true,
  "rule_graph_name": "TransitionRule_IdleRun_To_Crouch"
}
```

#### 使用的 C++ 类与方法

- `UAnimStateTransitionNode::BoundGraph`
- `UK2Node_VariableGet`
- `UK2Node_CallFunction`
- `UK2Node_FunctionResult` 或 transition graph 的结果节点
- `FEdGraphSchemaAction_K2NewNode::SpawnNode`
- `UEdGraphSchema_K2::TryCreateConnection`
- `UKismetMathLibrary::Not_PreBool`

实现建议：

1. 通过 `from_state` + `to_state` 找到唯一 transition node
2. 拿到 `TransitionNode->BoundGraph`
3. 校验 `bool_variable_name` 在 AnimBP 中可解析
4. 清理 rule graph 中除入口/结果节点外的已有逻辑，避免叠加旧规则
5. 创建 `UK2Node_VariableGet`
6. 如果 `expected_value == false`，再插入一个 `Not_PreBool` 节点
7. 把最终布尔输出连到结果节点的 bool pin
8. 标脏

这里建议把规则能力刻意限制为一类模板，而不是开放成通用 transition graph patch API。原因很简单：MVP 的目标是可靠完成 crouch 场景，不是现在就复制 K2 图编辑器的全部表达力。

#### 对齐现有 Action 模式

内部实现会复用 `FAddBlueprintVariableGetAction`、`FAddBlueprintFunctionNodeAction`、`FConnectBlueprintNodesAction` 的节点创建与连线手法，但外部暴露成一个更高层的原子命令，减少 Python 端对 transition rule graph 细节的了解。

#### 依赖

- 依赖目标 transition 已存在
- 依赖 `bool_variable_name` 已存在
- 建议在 `add_anim_transition` 之后立即调用

### 5. `set_anim_state_animation`

#### 作用

把某个 state 的内部动画图设置成播放一个 AnimSequence。这是 crouch 场景真正把动作挂上去的关键步骤。

#### 输入 JSON

```json
{
  "blueprint_name": "ABP_Unarmed",
  "state_machine_name": "Locomotion",
  "state_name": "Crouch",
  "animation_asset": "/Game/Characters/Animations/AS_Crouch.AS_Crouch"
}
```

#### 输出 JSON

```json
{
  "success": true,
  "state_name": "Crouch",
  "state_node_id": "...",
  "bound_graph_name": "Crouch",
  "animation_asset": "/Game/Characters/Animations/AS_Crouch.AS_Crouch"
}
```

#### 使用的 C++ 类与方法

- `UAnimStateNode::BoundGraph`
- `UAnimGraphNode_SequencePlayer`
- `FGraphNodeCreator<UAnimGraphNode_SequencePlayer>` 或等价节点创建方式
- `UAnimGraphNode_SequencePlayer::Node.Sequence`
- `UAnimationGraphSchema` 或图 schema 的连接接口
- 状态内部结果节点，例如 AnimGraph Result 节点
- `LoadObject<UAnimSequence>` 或 `UEditorAssetLibrary::LoadAsset`

实现建议：

1. 找到目标 `UAnimStateNode`
2. 拿到其 `BoundGraph`
3. 加载 `UAnimSequence`
4. 清理 state 内已有的 SequencePlayer 等播放节点，避免重复输出
5. 创建 `UAnimGraphNode_SequencePlayer`
6. 设置 `SequencePlayerNode->Node.Sequence = LoadedSequence`
7. 将 SequencePlayer 的 Pose 输出连到 state graph 的结果节点输入
8. 标脏

#### 对齐现有 Action 模式

最接近 `FAddBlueprintFunctionNodeAction` 的创建节点思路，加上 `FSetNodePinDefaultAction` 的资产绑定语义。

#### 依赖

- 依赖 state 已存在
- 依赖 `animation_asset` 可加载且类型为 `UAnimSequence`

## 建议复用的现有命令

这部分不新增实现，但需要在文档和 Python 包装层明确串起来。

### `open_asset_editor`

用法示例：

```json
{
  "command": "open_asset_editor",
  "params": {
    "asset_path": "/Game/Characters/ABP_Unarmed",
    "focus": true
  }
}
```

它只负责打开编辑器，不会自动设置 `CurrentBlueprint`。因此所有新 AnimBP 命令都建议显式传 `blueprint_name`。

### `compile_blueprint`

直接复用现有实现。AnimBP 也是 `UBlueprint` 子类，这条命令无需扩展。

### `save_all`

继续复用现有全局保存逻辑。

## C++ 实现建议

### 新文件

建议新增一组独立文件：

- `plugin/Source/UEBridgeEditor/Public/Actions/AnimGraphActions.h`
- `plugin/Source/UEBridgeEditor/Private/Actions/AnimGraphActions.cpp`

原因：

- 这批命令虽然也属于 Blueprint 编辑，但依赖的是 AnimGraph 编辑器模块和状态机专用类
- 单独拆文件可以避免把 `NodeActions.cpp` 进一步膨胀
- 后续如果增加 state machine、blend space、conduit、anim graph patch 等能力，也有自然的归宿

### 推荐类结构

```cpp
class FListAnimStatesAction : public FBlueprintAction
class FAddAnimStateAction : public FBlueprintAction
class FAddAnimTransitionAction : public FBlueprintAction
class FSetAnimTransitionRuleAction : public FBlueprintAction
class FSetAnimStateAnimationAction : public FBlueprintAction
```

这里统一继承 `FBlueprintAction`，而不是 `FBlueprintNodeAction`。原因是这些命令面对的是 AnimBP 的嵌套专用 graph，不适合复用 `graph_name -> FindGraph()` 这一套默认逻辑。它们需要自己先解析 state machine，再下钻到 state graph 或 transition rule graph。

### `AnimGraphActions.h` 需要的 includes

头文件尽量轻，只保留：

```cpp
#pragma once

#include "CoreMinimal.h"
#include "Actions/EditorAction.h"
```

其余使用 forward declaration：

```cpp
class UAnimBlueprint;
class UAnimationStateMachineGraph;
class UAnimStateNode;
class UAnimStateTransitionNode;
class UEdGraph;
```

### `AnimGraphActions.cpp` 需要的 includes

建议至少包含：

```cpp
#include "Actions/AnimGraphActions.h"

#include "Animation/AnimBlueprint.h"
#include "Animation/AnimSequence.h"
#include "AnimGraphNode_StateMachineBase.h"
#include "AnimStateNode.h"
#include "AnimStateEntryNode.h"
#include "AnimStateTransitionNode.h"
#include "AnimationStateMachineGraph.h"
#include "AnimationStateMachineSchema.h"
#include "AnimGraphNode_SequencePlayer.h"
#include "AnimationGraphSchema.h"

#include "EdGraph/EdGraph.h"
#include "EdGraph/EdGraphNode.h"
#include "EdGraph/EdGraphPin.h"
#include "EdGraphSchema_K2.h"
#include "EdGraphSchema_K2_Actions.h"

#include "K2Node_VariableGet.h"
#include "K2Node_CallFunction.h"
#include "K2Node_FunctionResult.h"

#include "Kismet2/BlueprintEditorUtils.h"
#include "Kismet2/KismetEditorUtilities.h"
#include "Kismet/KismetMathLibrary.h"

#include "EditorAssetLibrary.h"
```

如果编译时发现 `UAnimGraphNode_SequencePlayer`、`UAnimationStateMachineGraph` 或 schema 头所在模块未导出到当前模块，需要同步调整 Build.cs。

### Build.cs 依赖

现有 `UEBridgeEditor.Build.cs` 已有 `BlueprintGraph`、`KismetCompiler` 等依赖，但没有看到 `AnimGraph`。这批功能大概率还需要把以下模块加入 `PrivateDependencyModuleNames`：

- `AnimGraph`

如果后续需要直接操作动画蓝图编辑器专用工具，再评估是否需要 `AnimationBlueprintEditor`。MVP 先不要加，尽量只依赖 `AnimGraph`。

## 内部辅助函数建议

为了避免 5 个 Action 各自重复找状态机和节点，建议在 `AnimGraphActions.cpp` 里加一组私有 helper：

- `UAnimBlueprint* ResolveAnimBlueprint(UBlueprint* Blueprint, FString& OutError)`
- `UAnimGraphNode_StateMachineBase* FindStateMachineNode(UAnimBlueprint* AnimBP, const FString& StateMachineName, FString& OutError)`
- `UAnimationStateMachineGraph* GetStateMachineGraph(...)`
- `UAnimStateNode* FindStateNodeByName(UAnimationStateMachineGraph* Graph, const FString& StateName)`
- `UAnimStateTransitionNode* FindTransitionByEndpoints(UAnimationStateMachineGraph* Graph, const FString& FromState, const FString& ToState)`
- `UEdGraphNode* FindTransitionResultNode(UEdGraph* RuleGraph)`
- `UEdGraphNode* FindStateResultNode(UEdGraph* StateGraph)`
- `void MarkAnimBlueprintModified(UBlueprint* Blueprint, FUEEditorContext& Context)`，内部直接复用现有 `MarkBlueprintModified`

这些 helper 应该优先使用名字定位，再输出 GUID 给调用端。原因是 Python 侧最自然传的是 state 名和 transition 端点，而不是编辑器内部 GUID。

## ActionRegistry.cpp 注册方式

### 1. 顶部 include

在 `ActionRegistry.cpp` 增加：

```cpp
#include "Actions/AnimGraphActions.h"
```

### 2. 新增注册函数

```cpp
void RegisterAnimGraphActions(TMap<FString, TSharedRef<FEditorAction>>& ActionHandlers)
{
    ActionHandlers.Add(TEXT("list_anim_states"), MakeShared<FListAnimStatesAction>());
    ActionHandlers.Add(TEXT("add_anim_state"), MakeShared<FAddAnimStateAction>());
    ActionHandlers.Add(TEXT("add_anim_transition"), MakeShared<FAddAnimTransitionAction>());
    ActionHandlers.Add(TEXT("set_anim_transition_rule"), MakeShared<FSetAnimTransitionRuleAction>());
    ActionHandlers.Add(TEXT("set_anim_state_animation"), MakeShared<FSetAnimStateAnimationAction>());
}
```

### 3. 在 `RegisterDefaultActions` 中调用

建议放在 `RegisterNodeActions(ActionHandlers);` 之后：

```cpp
RegisterNodeActions(ActionHandlers);
RegisterAnimGraphActions(ActionHandlers);
RegisterProjectActions(ActionHandlers);
```

这样顺序上也符合心智模型：Blueprint 通用图命令之后，再注册 AnimGraph 专用命令。

## 建议的错误类型

为了和现有风格一致，建议新增以下 `error_type`：

- `invalid_blueprint_type`：目标 Blueprint 不是 AnimBlueprint
- `state_machine_not_found`
- `state_not_found`
- `transition_not_found`
- `duplicate_state`
- `duplicate_transition`
- `invalid_animation_asset`
- `variable_not_found`
- `rule_graph_invalid`
- `state_graph_invalid`

## 建议的实现顺序

建议按下面顺序开发，风险最低：

1. `list_anim_states`
2. `add_anim_state`
3. `add_anim_transition`
4. `set_anim_transition_rule`
5. `set_anim_state_animation`

原因：

- 前三个主要解决定位和拓扑改动
- 第四个和第五个才会进入 transition rule graph / state bound graph 的内部编辑
- 一旦前面三步跑通，后续调试会容易很多，因为图结构已经可视化了

## 对 Python / 调用层的建议

虽然这次重点是 C++ 插件设计，但从 agent 使用体验看，Python 层最好再包一个高层便捷函数，例如：

`add_crouch_state(anim_bp, state_machine, source_state, bool_var, crouch_anim)`

它内部顺序调用上述原子命令。这样 raw command 保持小而稳定，Python API 则承担场景级编排。

## 最终结论

这个需求的最小闭环不需要做通用 AnimGraph 编辑器，只需要补 5 个围绕状态机的原子命令，并复用现有的打开、编译、保存能力。

最核心的设计判断有两个：

1. transition 只做单向命令，双向靠调用两次完成
2. transition rule 只支持布尔变量模板，不在 MVP 阶段开放任意 rule graph 编辑

这样做的好处是实现面窄、验证路径短、和 ue-bridge 现有 action 架构高度一致，而且已经足够覆盖你要的 crouch 状态接入场景。
