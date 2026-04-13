# UE 编辑器自动化 — 安装指南

## 前置条件

- macOS 或 Windows
- Unreal Engine 5.7+
- Python 3.10+
- UE Editor 运行中且 bridge 插件已启用

## 目录结构

```
ue_bridge_skill/
  plugin/           C++ UE 插件（复制到项目的 Plugins/ 下）
  python/           Python 库（pip install -e .）
  skills/           AI 使用文档（本文件）
  scripts/          平台相关安装辅助脚本
  hosts/            内置验证用宿主项目
```

## 安装步骤

### 第一步：安装 C++ 插件

**macOS** — 使用安装脚本：

```bash
cd ue_bridge_skill
./scripts/setup.sh /path/to/your/UE/project
```

脚本会把插件复制到项目的 `Plugins/` 目录、修补 macOS 兼容性的 RTTI 编译标志、用 UE 5.7 的构建工具编译插件。

如果脚本找不到 RunUBT，需要手动编译：

```bash
"/Users/Shared/Epic Games/UE_5.7/Engine/Build/BatchFiles/RunUBT.sh" \
  <项目名>Editor Mac Development \
  -Project="/path/to/your/project.uproject" \
  -TargetType=Editor
```

注意：`setup.sh` 使用 `rsync -a` 会保留源文件时间戳。如果 UE 认为代码没变而跳过编译，用 `touch` 更新源文件时间戳后重新编译。

**Windows** — 手动复制：

```
复制 ue_bridge_skill/plugin/ → <你的项目>/Plugins/UEBridgeEditor/
```

然后重启 UE Editor。

**关键**：`.uproject` 文件必须声明插件，否则 UE 不会启动 TCP 监听：

```json
{
    "Name": "UEBridgeEditor",
    "Enabled": true
}
```

### 第二步：安装 Python 库

```bash
cd ue_bridge_skill/python
pip install -e ".[dev]"
```

安装完成后可用：

- **Python 导入**：`from ue_bridge import UEBridge`
- **CLI 命令**：`ue-bridge`
- **模块调用**：`python3 -m ue_bridge`（规范路径）或 `python3 -m src`（兼容路径）

### 第三步：验证连接

```bash
ue-bridge doctor   # 结构化诊断：连接、编辑器上下文、就绪状态、日志
ue-bridge verify   # 严格就绪门槛，不通过则 exit code 非零
```

`verify` 通过即安装完成。

### 可选：使用内置宿主项目验证

如果想用最小化的维护项目而不是自己的项目来验证：

```bash
# 内置宿主项目
hosts/UEBridgeHost/UEBridgeHost.uproject

# 端到端验证流程
scripts/run_python_unreal_integration.sh hosts/UEBridgeHost/UEBridgeHost.uproject
```

## 常见问题

**"Cannot connect to Unreal Editor"**：UE Editor 没运行，或 bridge 插件未启用。检查 `.uproject` 是否声明了 `UEBridgeEditor` 插件。

**"Connection refused on port 55558"**：插件的 TCP 服务器可能还没启动。等编辑器完全加载后再试 `ue-bridge doctor`。

**`doctor` 通过但 `verify` 失败**：编辑器可达但 Asset Registry 还没加载完。等几秒再试。

**Python import 报错**：确认在 `python/` 目录执行了 `pip install -e .`。包名是 `ue-bridge`，规范导入路径是 `from ue_bridge import UEBridge`。

**macOS RTTI 编译错误**：安装脚本会自动修补 `bUseRTTI=false`。如果手动编译，需确保 `.Build.cs` 中有 `bUseRTTI = false`。

**编译后新功能不生效**：`setup.sh` 的 `rsync -a` 保留时间戳，UE 的增量编译会跳过"未修改"的文件。解决方法：`touch` 所有 `.cpp`/`.h` 文件后重新编译，或删除 `Intermediate/` 和 `Binaries/` 目录让 UE 强制全量重编。

**Windows 插件不加载**：确认插件目录在 `<项目>/Plugins/UEBridgeEditor/` 下，且重启了编辑器。
