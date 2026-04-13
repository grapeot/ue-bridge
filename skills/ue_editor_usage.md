# UE 编辑器自动化 — 使用指南

## 核心概念

`ue-bridge` 是一个通过 TCP（端口 55558）控制 Unreal Editor 的 Python 库。UE 内的 C++ 插件处理命令，Python 库负责发送。

两种使用方式：

- **CLI**（`ue-bridge <命令>`）— 适合单次操作：ping、查询 Actor、编译 Blueprint、生成 Actor
- **Python 库**（`from ue_bridge import UEBridge`）— 适合多步工作流：创建 Blueprint、连线节点、配置输入系统、批量操作

CLI 适合一条命令能搞定的事。需要流程控制、条件判断或依赖前序返回值时用 Python 库。

开始工作前先跑一次检查：

```bash
ue-bridge doctor   # 结构化诊断报告
ue-bridge verify   # 严格就绪检查，失败时 exit code 非零
```

## 文档索引

本指南按主题拆分为以下文件。AI agent 读完本页后，按需跳转到具体主题。

| 主题 | 文件 | 内容概要 |
|------|------|---------|
| API 速查 | [api_reference.md](ue_editor_usage/api_reference.md) | CLI 命令列表、Python API（连接、场景、Blueprint、输入、PIE、UMG、材质、Raw Commands） |
| Enhanced Input | [input_system.md](ue_editor_usage/input_system.md) | Input Action 创建、IMC 绑定、PlayerController 注册、SpectatorPawn 按键冲突 |
| 材质与纹理 | [materials_and_textures.md](ue_editor_usage/materials_and_textures.md) | 材质创建、纹理导入、Unlit 材质配方、自动曝光、截图调试 |
| 完整示例 | [examples.md](ue_editor_usage/examples.md) | 3 个端到端示例：蹲伏功能、纹理卡牌场景、Z/X 键卡牌切换 |
| 常用模式与踩坑记录 | [recipes_and_gotchas.md](ue_editor_usage/recipes_and_gotchas.md) | 工作原则、常用 Recipe、已知限制、全部踩坑记录 |

安装相关内容见 [安装指南](ue_editor_installation.md)。

## 快速上手路径

1. 按 [安装指南](ue_editor_installation.md) 完成插件安装和 Python 包安装
2. 运行 `ue-bridge doctor` 和 `ue-bridge verify` 确认就绪
3. 查阅 [API 速查](ue_editor_usage/api_reference.md) 了解可用命令
4. 参考 [完整示例](ue_editor_usage/examples.md) 理解端到端工作流
5. 遇到问题时查 [踩坑记录](ue_editor_usage/recipes_and_gotchas.md)

## 关键注意事项（必读）

以下是最容易踩的坑，在开始任何工作前请过一遍：

- **每批操作后调用 `ue.save_all()`**。API 修改只在内存中生效，UE 崩溃会丢失
- **Enhanced Input 必须连在 PlayerController 里**，不能放在 Pawn 的 EventGraph 中。SpectatorPawn 子类的 Enhanced Input 事件不会触发
- **`connect()` 必须传 `blueprint_name` 参数**，否则报 "Source or target node not found"
- **`spawn_blueprint_actor` 不应用 scale**，需要额外调用 `set_actor_transform()`
- **`new_level` 会覆盖同名关卡**（创建空白关卡），切换已有关卡用 `open_level`
- **自动曝光在暗场景中会把 Unlit Emissive 材质吹白**，需在 `DefaultEngine.ini` 中设 `r.DefaultFeature.AutoExposure=0` 并重启编辑器
- **纹理导入无 API**，需手动把 PNG 放到 `Content/` 下由 UE 自动检测导入
- **修改 C++ 插件后需要重启编辑器**，Python 侧改动不需要
