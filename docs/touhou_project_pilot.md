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

## 执行中发现的问题和教训

以下按类别整理了整个 pilot 过程中发现的所有 bug、feature gap、和关键 discovery。每一条都是课程教学素材的候选，标注了对方法论的意义。

### 1. Crash 和稳定性

#### 1.1 UK2Node_SpawnActorFromClass 在 macOS 上必崩

**现象**：通过 bridge 创建 SpawnActorFromClass 节点，无论传入 native class 还是 Blueprint class，editor 都会 crash（access violation in SpawnNode 或 ReconstructNode）。

**修复历程**：
- PR #30：加了 null check，修复了传入无效 class 名时的崩溃
- PR #34：实现了 macOS signal-based crash protection（sigsetjmp/siglongjmp），捕获 SIGSEGV/SIGBUS/SIGABRT。崩溃不再杀死 editor，而是返回 "CRASH PREVENTED" 错误

**最终 workaround**：用 `BeginDeferredActorSpawnFromClass` + `FinishSpawningActor`（普通函数调用节点）替代。这两个是 GameplayStatics 的标准函数，通过 `add_function_node` 创建，完全不触发崩溃。

**课程价值**：展示了 AI 遇到 control 边界时的三层应对策略：(1) 修 bug，(2) 加 crash protection 兜底，(3) 找替代方案绕过。

#### 1.2 同 session 修改 Blueprint 后 PIE 必崩

**现象**：在同一个 editor session 内通过 bridge 修改 Blueprint（编译保存后），立即启动 PIE 会 crash。重启 editor 后 PIE 正常。

**根因**：可能是 Blueprint 的 CDO（Class Default Object）在 hot reload 后状态不一致。

**workaround**：修改 BP 后必须 save → 重启 editor → 再 PIE。AI 工作流已适配：每次修改后自动重启。

**课程价值**：这是 feedback loop 的核心约束——AI 不能"改完立刻验"，必须经过一个 restart 周期。

#### 1.3 focus_viewport 导致 editor crash

**现象**：调用 `focus_viewport` 时 editor crash。

**workaround**：避免使用，用 `set_viewport_transform` 代替（虽然效果有时也不生效）。

#### 1.4 set_actor_property 设 DefaultGameMode 导致 PIE crash

**现象**：通过 `set_actor_property("WorldSettings", "DefaultGameMode", class_path)` 设置后，PIE 启动即 crash。

**根因**：`set_actor_property` 设置 TSubclassOf 属性的方式在运行时可能不兼容。

**workaround**：通过修改 `DefaultEngine.ini` 的 `GlobalDefaultGameMode` 设置。重启后生效，PIE 正常。

**课程价值**：同一个功能通过不同路径实现，一个崩溃一个正常——体现了 UE 内部不同 API 路径的差异。

### 2. Observability（可见性）

#### 2.1 editor world vs PIE world 的隔离

**现象**：`get_actors`、`get_actor_properties`、`take_screenshot` 只能访问 editor world。PIE 运行时 spawn 的 actor（子弹等）在 editor world 中不可见。

**修复**：新增了 `get_pie_actors` 和 `get_pie_actor_property` 命令（PR #35），直接遍历 PIE world 的 `TActorIterator`。

**课程价值**：这是 visibility 方法论的核心挑战——AI 操作的世界和运行时的世界是两个不同的 world context，必须有对应的 API 才能观察运行时状态。

#### 2.2 take_screenshot 只抓 editor viewport

**现象**：`take_screenshot` 抓的是 editor viewport（3D 编辑器视角），不是 PIE 的 game viewport（玩家相机视角）。PIE 期间 game viewport 的 ReadPixels 会导致 crash。

**当前状态**：editor viewport 截图可用于观察编辑器状态，但无法看到玩家视角。

**课程价值**：即使有截图能力，"看到什么"取决于截图来源。真正的 game feel 验证仍然需要人。

#### 2.3 AI 自动重启 UE Editor

**实现**：`pkill -f UnrealEditor && sleep 3 && /path/to/UnrealEditor project.uproject &`，然后 poll `ue-bridge ping` 等待就绪。约 12 秒恢复。

**发现**：`open .uproject` 在 macOS 上不可靠，直接调 UnrealEditor binary 更稳定。

**课程价值**：crash recovery 是 AI 自主工作的基础能力。没有自动重启，每次 crash 都需要人介入。

### 3. UE 5.7 / Enhanced Input 特性

#### 3.1 数学函数用 Double 不用 Float

UE 5.7 的 Blueprint 数学函数改名了：`Add_FloatFloat` → `Add_DoubleDouble`，`Multiply_FloatFloat` → `Multiply_DoubleDouble`，`GreaterEqual_FloatFloat` → `GreaterEqual_DoubleDouble`。

AI 在首次调用时失败，但错误信息 "Function not found" 引导 AI 尝试替代名称并自我修正。这是 feedback loop 的一个小而完美的例证。

#### 3.2 Blueprint Pin 命名不符合直觉

- EventTick 输出 pin 是 `then` 不是 `execute`
- Branch 输出 pin 是 `then`/`else` 不是 `True`/`False`
- CustomEvent 只有输出 pin（事件源），没有输入 execute pin

错误信息会列出所有可用 pin，AI 可以据此修正。

#### 3.3 Enhanced Input Axis2D 需要 Swizzle/Negate 修饰符

WASD 映射到 Axis2D 时，每个键需要不同的 modifier：
- W: Swizzle(YXZ) — 把 1D 值映射到 Y 轴
- S: Negate + Swizzle — Y 轴负方向
- A: Negate — X 轴负方向
- D: 无 modifier — X 轴正方向

不加 modifier 时所有键发送相同的原始值，导致移动完全无效。Bridge 的 `add_key_mapping` 已支持 `modifiers` 参数。

#### 3.4 GetWorldDeltaSeconds 在 Enhanced Input 回调中返回 0

**现象**：Player 移动逻辑完全正确（graph describe 验证了全部连接），但 player 不动。

**根因**：移动链中用了 `GetWorldDeltaSeconds` 乘以速度，但在 Enhanced Input 的 `Triggered` 事件回调中，`GetWorldDeltaSeconds` 返回 0。

**修复**：去掉 DeltaSeconds 乘法。Enhanced Input 的 `Triggered` 事件在按键 held 时每帧触发，不需要手动乘 dt。

**课程价值**：这是 feedback loop 最有力的案例之一——AI 通过 `describe_graph` 分析全部连接（确认正确），推理出 DeltaSeconds 可能为零（数据问题而非连接问题），修改后验证通过。整个诊断过程无人工参与。

### 4. World Partition 和关卡管理

#### 4.1 Open World 模板的 World Partition 导致 actor 丢失

**现象**：通过 `spawn_blueprint_actor` 创建的 actor 在 editor 重启后消失。

**根因**：Open World 模板使用 World Partition streaming 系统，动态 spawn 的 actor 没有被正确持久化到 streaming cell。

**修复**：用 `new_level` 创建无 World Partition 的空关卡。设置 `DefaultEngine.ini` 的 `EditorStartupMap` 和 `GameDefaultMap` 确保重启后加载正确关卡。

#### 4.2 spawn_actor 不支持所有 actor 类

`PlayerStart`、`SkyLight` 等类无法通过 `spawn_actor` 创建（"Unknown actor type"）。支持的类型有限（StaticMeshActor、DirectionalLight、PointLight、SpotLight、CameraActor 等）。

**workaround**：不 spawn PlayerStart，GameMode 会在原点 (0,0,0) spawn pawn。

### 5. 新增的基础设施

以下是在 pilot 过程中为了解决问题而新增的 bridge 能力：

| 命令 | PR | 用途 |
|------|-----|------|
| `start_pie` / `stop_pie` / `get_pie_state` | #26 | PIE 生命周期控制 |
| UMG Widget 24 个方法 | #27 | HUD 构建 |
| `take_screenshot` | #32 | Editor viewport 截图 |
| `new_level` | 直接 push | 创建空关卡 |
| macOS crash protection | #34 | 信号级崩溃捕获 |
| `execute_console_command` | #35 | PIE 控制台命令 |
| `get_pie_actors` | #35 | PIE world actor 查询 |
| `get_pie_actor_property` | #35 | PIE world actor 属性读取 |
| `simulate_key` | #35 | Slate 级键盘模拟 |

## 成功标准

1. AI 通过 UE Bridge 独立完成 Phase 1-3，人工干预仅限关键审美判断（第四层）和已知 bug workaround
2. 最终产物是一个可玩的一关弹幕 demo：玩家能移动、射击、躲避弹幕、打败 Boss
3. 构建过程中，AI 能通过 PIE 控制命令自行发现和修复至少一个运行时 bug（验证 feedback loop 有效性）——**已达成：DeltaSeconds 为零的 bug 完全由 AI 通过 graph describe + 推理 + 修复 + 验证闭环解决**
4. 整个过程可作为课程案例，展示 visibility / control / feedback loop 方法论的实际应用
