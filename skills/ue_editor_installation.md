# Skill: UE Editor 自动化 — 安装

## 前置条件

- macOS 或 Windows
- Unreal Engine 5.7+，已安装 UEEditorMCP 插件并编译通过（见 `docs/ue_editor_mcp_mac_setup.md`）
- Python 3.9+
- UE Editor 正在运行，插件已 Enabled

## 安装 ue_bridge

ue_bridge 是一个纯 Python 库，位于 `combat_game/tools/ue_editor/`。不需要 pip install，直接用路径引用。

### 在脚本中使用

```python
import sys
sys.path.insert(0, "/path/to/combat_game/tools/ue_editor")

from src import UEBridge

ue = UEBridge()
print(ue.ping())  # True
ue.close()
```

### CLI 使用

```bash
cd /path/to/combat_game/tools/ue_editor
python3 -m src ping
python3 -m src get-actors
python3 -m src compile --blueprint BP_PlatformingCharacter
```

### 运行测试

```bash
cd /path/to/combat_game/tools/ue_editor

# 单元测试（不需要 UE）
python3 -m pytest tests/ -v -k "not integration"

# 集成测试（需要 UE 运行）
python3 -m pytest tests/test_integration.py -v -m integration
```

## 确认安装成功

```bash
cd /path/to/combat_game/tools/ue_editor
python3 -m src ping
```

返回 `{"pong": true}` 即表示 Python -> TCP -> UE Plugin 全链路通了。

## 故障排查

**"Cannot connect to Unreal Editor"**：UE Editor 没开或者 UEEditorMCP 插件没加载。检查 Edit > Plugins 里 UEEditorMCP 是否 Enabled。

**"Connection refused on port 55558"**：插件可能没启动 TCP server。在 UE 的 Output Log 里搜 "MCP" 看有没有启动日志。

**Python import 报错**：确认 sys.path 里加了 `tools/ue_editor` 目录，且 `src/__init__.py` 存在。
