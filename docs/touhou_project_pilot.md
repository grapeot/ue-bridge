# 东方 Project 弹幕游戏 Pilot

## 目标

用 UE Bridge 让 AI 从头到尾构建一个可玩的弹幕射击游戏（东方 Project 风格），验证"AI 能否端到端参与游戏生产"这一命题。

这个 pilot 的核心价值不在游戏本身，而在于验证课程方法论：visibility、control、feedback loop 三个关键词在一个完整游戏项目中是否成立。如果 AI 能独立完成从蓝图搭建到运行验证的全链路，就证明了 UE Bridge 作为 AI skill 的产业可行性。

## 游戏范围

做一关，一个 Boss 战。

- 玩家角色：上下左右移动 + 射击 + 低速模式（缩小碰撞判定框）+ Bomb
- 敌人：一个 Boss，2-3 个弹幕 phase
- 弹幕 pattern：扇形弹、环形弹、螺旋弹（纯逻辑，每帧计算位置）
- HUD：分数、残机数、Bomb 数、Boss 血条
- 贴图：占位符或 Gemini 生成

不做的事：多关卡、道具掉落系统、排行榜、音效同步。

## 技术路线决策

### 弹幕实现：Actor-based，不用 Niagara

弹幕用单独的 Actor（或 Blueprint）实现，每颗子弹一个实例。理由：

- 当前 UE Bridge API 完全支持 `spawn_actor` / `set_actor_transform` / `delete_actor`，不需要新增任何命令
- 一关 demo 级别的弹幕量（几百颗同屏）对 UE 来说不是性能问题
- Niagara 的 API 面非常大，加进来工作量与收益不成比例
- 东方原作的弹幕逻辑本质就是每帧计算位置，Actor-based 方案更贴近原始设计思路

如果后续需要上千颗弹幕同屏的视觉效果，Niagara 支持可以作为独立 RFC 推进，不阻塞本 pilot。

### 弹幕动画：Tick + 变量，不用 Timeline

弹幕轨迹用 EventTick + 速度/角度变量计算，不依赖 Timeline。理由：

- 弹幕的运动是确定性的数学计算（极坐标展开、角速度叠加），用 Tick 里的简单数学表达比 Timeline 的曲线编辑更自然
- 当前 Bridge 已有完整的 Blueprint 节点操作能力（`add_event_node("Tick")`、`add_variable`、`add_function_node`、`connect`），可以直接构建这类逻辑
- 省掉 Timeline 支持的开发量，聚焦在更关键的 gap 上

Boss 出场演出、phase 切换等如果需要缓动效果，可以在 Blueprint 里用 FInterp 系列函数 + Tick 实现，不需要 Timeline 节点。

### 需要新增的 Bridge 能力

#### 1. PIE 控制命令（最高优先级）

这是 feedback loop 的核心。没有 PIE 控制，AI 搭完蓝图后无法自行验证游戏行为是否正确，整个闭环就断了。

需要新增的命令：

| 命令 | 用途 |
|------|------|
| `start_pie` | 启动 Play In Editor |
| `stop_pie` | 停止 PIE |
| `is_pie_running` | 查询 PIE 状态 |
| `get_pie_actors` | 获取运行时 Actor 列表及状态 |
| `get_pie_actor_property` | 读取运行时 Actor 的属性值 |
| `execute_console_command` | 在 PIE 会话中执行控制台命令 |

实现路径：C++ 侧通过 `GEditor->RequestPlaySession()` / `GEditor->RequestEndPlayMap()` 控制 PIE 生命周期，通过 `GEditor->GetPIEWorldContext()` 获取运行时 World，在运行时 World 中查询 Actor 和属性。这些都是 UE Editor API 的标准能力，实现模式与现有 Action 一致。

PIE 控制对于课程的方法论意义：它直接体现了"AI 需要 visibility 才能有效工作"这一核心论点。在蹲下功能的案例中，AI 改错 Blueprint 的根因就是缺乏运行时验证手段。PIE 控制命令补上了这个缺口——AI 不仅能操作编辑器，还能启动游戏、观察结果、诊断问题。

#### 2. HUD / UMG Widget 支持（高优先级）

弹幕游戏至少需要显示分数、残机、Bomb 数和 Boss 血条。当前 Bridge 没有任何 Widget 相关命令。

需要新增的命令：

| 命令 | 用途 |
|------|------|
| `create_widget_blueprint` | 创建 Widget Blueprint |
| `add_widget_component` | 添加 Widget 组件（TextBlock, ProgressBar, Image, CanvasPanel 等） |
| `set_widget_property` | 设置 Widget 组件属性（文字内容、颜色、锚点、位置、大小等） |
| `bind_widget_to_variable` | 将 Widget 组件绑定到 Blueprint 变量（用于运行时数据驱动） |
| `add_widget_to_viewport` | 在 Blueprint 中添加"创建 Widget 并加到 Viewport"的节点逻辑 |

实现路径：UMG 底层是 UObject 体系，`UWidgetBlueprint` 继承自 `UBlueprint`，Widget 组件（`UWidget` 子类）可以通过 `UWidgetTree` 添加。属性设置走现有的 `FProperty` 反射路径。整体模式与现有的 Blueprint Action 一致，不需要新架构。

## 已知挑战（不属于 Bridge Gap，但需要 AI Skill 层面应对）

以下两个问题不需要新增 Bridge 命令，但会显著影响 AI 构建弹幕游戏的效率，需要在 AI skill 文档中给出指导。

### 对象池（Object Pool）

弹幕游戏的子弹频繁 spawn/destroy，如果每颗子弹都走 `spawn_actor` / `delete_actor`，GC 压力会比较大。标准做法是对象池：预先 spawn 一批子弹 Actor，用时 Activate + 设位置，回收时 Deactivate。

这个逻辑可以完全在 Blueprint 内实现（TArray 变量 + Branch + SetActorHiddenInGame + SetActorEnableCollision），现有 Bridge API 已经能搭建这样的 Blueprint 图。挑战在于：这是一个相对复杂的 Blueprint 结构（~15-20 个节点 + 连线），AI 需要能可靠地规划节点布局和连接顺序。这属于 AI skill 的工作流设计问题，不属于 Bridge 能力 gap。

建议：在 skill 文档中提供一个对象池的 Blueprint 构建 recipe（节点清单 + 连接顺序），让 AI 可以按模板执行。

### 碰撞配置（Collision Channel / Profile）

弹幕游戏需要精确的碰撞分层：玩家子弹只碰敌人、敌人子弹只碰玩家、子弹之间互相忽略。UE 的碰撞系统通过 Collision Channel 和 Collision Response 配置，属性路径比较深（`CollisionComponent.BodyInstance.CollisionResponses.ResponsesArray`）。

当前 Bridge 的 `set_component_property` 支持嵌套属性路径，理论上可以设置碰撞配置，但需要实际测试确认路径是否正确解析。如果现有反射路径走不通，可能需要新增一个专门的 `set_collision_response` 命令，但这属于发现问题后的修补，不需要预先规划。

建议：先用现有 API 尝试设置碰撞属性，如果碰到问题再针对性扩展。在 skill 文档中记录验证过的属性路径。

## 实现计划

### Phase 0：Bridge 扩展

1. 实现 PIE 控制命令（C++ Action + Python wrapper + 单元测试）
2. 实现 UMG Widget 命令（C++ Action + Python wrapper + 单元测试）
3. 更新 skill 文档，补充新命令的使用说明

### Phase 1：游戏骨架

用 UE Bridge 自动化构建：

1. 创建玩家角色 Blueprint（Character 子类），添加碰撞体和 Sprite/Mesh 组件
2. 配置 Enhanced Input：方向移动、射击、低速模式、Bomb
3. 创建子弹 Blueprint，配置碰撞和移动逻辑
4. 创建 Boss Blueprint，配置基本 AI 状态机（Phase 切换）
5. **PIE 验证**：启动游戏，确认玩家可以移动和射击

### Phase 2：弹幕系统

1. 在 Boss Blueprint 中搭建弹幕 Spawner 逻辑（Tick + 极坐标计算）
2. 实现 2-3 个弹幕 pattern（扇形、环形、螺旋）
3. 实现子弹对象池
4. 配置碰撞层（玩家 vs 敌弹、敌人 vs 玩家弹）
5. **PIE 验证**：启动游戏，确认弹幕正确生成和碰撞

### Phase 3：HUD 和收尾

1. 创建 HUD Widget Blueprint（分数、残机、Bomb、Boss 血条）
2. 绑定数据到 Game State
3. 实现死亡 / 复活 / Game Over 流程
4. 贴图替换（占位符 → Gemini 生成）
5. **最终 PIE 验证**：完整一局游戏流程

## 执行中发现的问题

### Bug: add_spawn_actor_from_class_node 导致 editor 崩溃

**现象**：传入合法的 Blueprint 类名（如 "BP_Bullet"）创建 SpawnActorFromClass 节点时，editor 直接 crash，没有错误返回。

**已修复部分（PR #30）**：当 Blueprint 或 Graph 为 null 时，新增 null check 返回错误而不是崩溃。传入不存在的类名现在能正确返回 "Class not found" 错误。

**未修复部分**：传入存在的 Blueprint 类名时，class 查找成功，但 `UK2Node_SpawnActorFromClass` 的 `SpawnNode<>` 或 `ReconstructNode()` 内部仍然崩溃。这是 UE 引擎层面的问题，需要更深入的调查。

**当前 workaround**：Boss 的 timer 逻辑通过 bridge 自动搭建，但 SpawnActorFromClass 节点需要人手动在 Blueprint 编辑器中添加并连接。

**课程价值**：这恰好是课程方法论的一个真实案例——AI 在操作编辑器时遇到了 control 层面的边界，需要人工介入。记录这个 gap 本身就是有价值的教学材料。

### Discovery: UE 5.7 数学函数命名变化

UE 5.7 将 Blueprint 数学函数从 Float 改为 Double：`Add_FloatFloat` → `Add_DoubleDouble`，`Multiply_FloatFloat` → `Multiply_DoubleDouble`。AI 在首次调用时会失败，但通过错误信息可以自我修正。这是 feedback loop 有效性的一个小例证。

### Discovery: Blueprint Pin 命名约定

- EventTick 输出 pin 是 `then` 不是 `execute`
- Branch 输出 pin 是 `then`/`else` 不是 `True`/`False`
- CustomEvent 只有输出 pin，没有输入 execute pin（它是事件源）

这些命名差异在首次使用时会导致连接失败，但错误信息会列出可用 pin，AI 可以据此修正。

## 成功标准

1. AI 通过 UE Bridge 独立完成 Phase 1-3，人工干预仅限关键审美判断（第四层）和已知 bug workaround
2. 最终产物是一个可玩的一关弹幕 demo：玩家能移动、射击、躲避弹幕、打败 Boss
3. 构建过程中，AI 能通过 PIE 控制命令自行发现和修复至少一个运行时 bug（验证 feedback loop 有效性）
4. 整个过程可作为课程案例，展示 visibility / control / feedback loop 方法论的实际应用
