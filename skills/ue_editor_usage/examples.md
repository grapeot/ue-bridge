← [返回总览](../ue_editor_usage.md)

# 完整示例

以下三个示例覆盖了 ue-bridge 的核心使用场景：输入绑定与蓝图逻辑编排、材质与场景搭建、以及带状态管理的交互循环。每个示例都是可直接运行的完整脚本。

## 示例一：为角色添加蹲伏功能

演示能力：修改继承组件属性、创建 Enhanced Input Action 并绑定按键、在蓝图中添加函数节点并连线、编译验证。

```python
from ue_bridge import UEBridge

with UEBridge() as ue:
    bp = "BP_ThirdPersonCharacter"

    # 1. 启用继承的 CharacterMovement 组件上的蹲伏属性
    ue.raw_command("set_inherited_component_property", {
        "blueprint_name": bp,
        "component_name": "CharMoveComp",
        "property_name": "NavAgentProps.bCanCrouch",
        "property_value": True,
    })

    # 2. 创建输入动作（自动添加 Pressed+Released 触发器）
    ue.create_input_action("IA_Crouch", value_type="Digital")

    # 3. 将 C 键绑定到输入映射上下文
    ue.add_key_mapping("IMC_Default", "IA_Crouch", "C")

    # 4. 添加蓝图节点
    input_node = ue.add_enhanced_input_action_node(bp, "IA_Crouch", position=(-400, 1200))
    crouch_node = ue.add_function_node(bp, "Crouch", position=(0, 1100))
    uncrouch_node = ue.add_function_node(bp, "UnCrouch", position=(0, 1300))

    # 5. 连线：按下时蹲伏，松开时站起
    ue.connect(input_node, "Started", crouch_node, "execute")
    ue.connect(input_node, "Completed", uncrouch_node, "execute")

    # 6. 编译并保存
    ue.compile(bp)
    ue.save_all()

    # 7. 验证输入映射是否正确写入
    imc = ue.raw_command("read_imc", {"context_name": "IMC_Default"})
    for m in imc["mappings"]:
        if m["action_name"] == "IA_Crouch":
            print(f'Verified: {m["action_name"]} -> {m["key"]} triggers={m["action_triggers"]}')
```

## 示例二：纹理卡牌展示场景

演示能力：创建关卡、创建 Unlit 材质并连接纹理节点、创建带网格和材质的 Actor 蓝图、生成 Actor 并设置变换、配置 SpectatorPawn 游戏模式实现自由飞行摄像机。

```python
from ue_bridge import UEBridge

with UEBridge() as ue:
    # 1. 创建空关卡
    ue.raw_command("new_level", {
        "level_name": "CardShowcase",
        "path": "/Game/Maps",
        "template": "Empty",
    })

    # 2. 创建 Unlit 材质并连接纹理
    #    （纹理需先导入，UE 会自动识别 Content/ 目录下的 PNG 文件）
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

    # 3. 创建卡牌蓝图，添加网格组件并赋予材质
    bp = "BP_Card"
    ue.create_blueprint(bp, parent_class="Actor", path="/Game/Cards")
    ue.add_component(bp, "StaticMeshComponent", "CardMesh")
    ue.set_static_mesh_properties(bp, "CardMesh",
        static_mesh="/Engine/BasicShapes/Cube.Cube",
        materials=[f"/Game/Materials/{mat}.{mat}"])
    ue.compile(bp)

    # 4. 生成卡牌并调整变换
    #    Scale (0.7, 0.03, 1.0) = 宽度, 极薄厚度, 高度（竖向卡牌）
    #    Yaw=90 让卡面朝向 -X 方向的摄像机
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

    # 5. 配置 SpectatorPawn 游戏模式（自由飞行摄像机，无重力）
    gm = "BP_ShowcaseGameMode"
    ue.create_blueprint(gm, parent_class="GameModeBase", path="/Game/Showcase")
    ue.set_blueprint_property(gm, "DefaultPawnClass", "/Script/Engine.SpectatorPawn")
    ue.compile(gm)
    ue.set_actor_property("WorldSettings", "DefaultGameMode",
        "/Game/Showcase/BP_ShowcaseGameMode.BP_ShowcaseGameMode_C")

    ue.save_all()
```

## 示例三：Z/X 键循环切换卡牌选中状态

演示能力：蓝图变量的创建与读写、数学运算节点（加法、取模）的组合、"先全部重置再高亮选中项"的模式（规避 Branch 合并问题）、多输入动作的批量创建与绑定。

Z 键向左切换，X 键向右切换。选中的卡牌放大显示，其余恢复原始尺寸。

```python
from ue_bridge import UEBridge

with UEBridge() as ue:
    bp = "BP_ThirdPersonPlayerController"  # Enhanced Input 必须绑定在 Controller 上，不能放在 Pawn
    SELECTED = "0.9, 0.04, 1.3"
    NORMAL = "0.7, 0.03, 1.0"
    card_classes = [
        "/Game/Cards/BP_Card_0.BP_Card_0_C",
        "/Game/Cards/BP_Card_1.BP_Card_1_C",
        "/Game/Cards/BP_Card_2.BP_Card_2_C",
    ]

    # 创建整数变量追踪当前选中索引
    ue.add_variable(bp, "CurrentCard", "int", default_value=0)

    # 创建输入动作：Z=上一张，X=下一张（避免 Q/E，SpectatorPawn 已占用）
    for ia, key in [("IA_PrevCard", "Z"), ("IA_NextCard", "X")]:
        ue.create_input_action(ia, value_type="Digital")
        ue.add_key_mapping("IMC_Default", ia, key)

    def build_chain(ia_name, delta, y_base):
        # 输入 -> 计算 (CurrentCard + delta) % 3 -> 写入变量
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

        # 第一轮：将所有卡牌重置为普通尺寸
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

        # 第二轮：逐张判断——如果 CurrentCard==i，则放大该卡牌
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
            prev, pin = br, "else"  # 通过 False 路径串联下一个 Branch

    build_chain("IA_PrevCard", len(card_classes) - 1, 2000)  # Z = 向左（上一张）
    build_chain("IA_NextCard", 1, 4000)                      # X = 向右（下一张）
    ue.compile(bp)
    ue.save_all()
```
