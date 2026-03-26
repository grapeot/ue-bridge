# Working Log

## Changelog

### 2026-03-25

- Added the first Unreal Automation Tests for Workflow A health checks in `plugin/Source/UEEditorMCP/Private/Tests/WorkflowAHealthTests.cpp`
- Pointed `CharacterActionRoom/Plugins/UEEditorMCP` at the maintained `ue_bridge_skill/plugin` via symlink so the host project runs the real plugin under development
- Built `CharacterActionRoomEditor` with the symlinked project plugin to ensure `UEEditorMCP` was discoverable as a project plugin module
- Ran Unreal Automation Tests successfully against `CharacterActionRoom.uproject` with `UEEditorMCP.Health` filter: 4 passed, 0 failed, exit code 0
- Verified the first Automation batch covers module load, bridge subsystem availability, `is_ready` success shape, `get_editor_logs` success shape, and safe unknown-command failure handling
- Started Workflow A on branch `workflow-a-doctor-verify`
- Added Python bridge wrappers for `is_ready`, `get_editor_logs`, `get_unreal_logs`, plus aggregated `doctor()` and `verify_installation()` helpers
- Added CLI commands for `is-ready`, `get-editor-logs`, `get-unreal-logs`, `doctor`, and `verify`
- Added unit coverage for Workflow A bridge aggregation and CLI behavior, including non-zero exit on failed verification
- Ran local fast suite successfully after Workflow A changes: 70 passed, 8 deselected
- Started Phase 2/3 contract-hardening branch after merging Phase 1 into master
- Added canonical `python/ue_bridge/` package surface while keeping `python/src/` as a compatibility layer
- Updated `pyproject.toml` so the `ue-bridge` console script points at `ue_bridge.cli:main` and editable installs include both `ue_bridge*` and `src*`
- Expanded the CLI for the primary one-off workflow: get-context, find-actors, create-blueprint, spawn-blueprint-actor, create-input-mapping-context, auto-layout
- Added contract tests for canonical imports, legacy import compatibility, CLI parser coverage, CLI runtime behavior, and additional bridge/connection parameter paths
- Ran local unit suite successfully: 56 passed, 8 deselected
- Added `.github/workflows/ci.yml` to run the non-integration contract suite on push and pull request
- Verified editable install + canonical entrypoint smoke test: `from ue_bridge import UEBridge` and `python -m ue_bridge ping`
- Phase 1 kickoff: AI-first documentation surface — docs-only changes, no code changes, non-breaking
- Rewrote README.md: replaced combat_game-centric README with a standalone project README covering architecture, quick start, key features, project structure, test instructions, and credits
- Rewrote skills/ue_editor_installation.md: self-contained installation guide with repo layout, 4-step setup (plugin install, verify, Python install, ping), and troubleshooting section. Removed all `combat_game/tools/ue_editor` paths and `sys.path.insert` hacks
- Rewrote skills/ue_editor_usage.md: full usage guide with CLI quick reference, Python API quick reference (connection, scene, Blueprint nodes, input system, materials, raw commands), known limitations (inherited components, IMC read/cleanup, error handling), working principles, and a complete crouch example. Removed outdated path references
- Created docs/working.md (this file)
- Updated README.md to make the CLI/library split explicit and added docs/working.md to the project structure
- Marked plugin/setup_mcp.bat and plugin/setup_mcp.ps1 as legacy MCP helpers so they no longer generate outdated `ue_editor_mcp.server_*` config for the current ue-bridge workflow

## Lessons Learned

- The original skill docs assumed you were working from within the combat_game project and used `sys.path.insert(0, "tools/ue_editor")` to import the library. After extracting ue_bridge into its own directory, all path guidance needed rewriting to be self-contained (`cd ue_bridge_skill/python && pip install -e .`)
- AI-facing docs (skills/) should be structured for the AI's workflow: prerequisites first, then step-by-step installation, then usage patterns with copy-pasteable code blocks. Avoid narrative — use headings and code fences as the primary navigation surface
- Phase 1 (docs-only) is a safe first step because it changes zero runtime behavior. This lets us validate the directory structure and documentation quality before touching code or build scripts in later phases
- A compatibility shim is much cheaper than a full package rename when the repo is still young. Adding a canonical `ue_bridge` package while preserving `src` lets us stabilize the public contract without forcing an all-at-once migration
- For this repo, the right testing bar is contract coverage, not UE-heavy end-to-end coverage. The local fast suite is what should drive GitHub Actions, while UE integration remains opt-in
- The correct CI scope for this repo is the Python contract surface, not Unreal-dependent integration flows. Shipping a small reliable workflow now is better than waiting for a full UE-capable pipeline
- Workflow A should aggregate existing Unreal primitives before inventing new ones. This repo already had `ping`, `get_context`, `is_ready`, and log actions in C++; the missing layer was the Python/CLI contract that turns them into a usable install/verify/diagnose workflow
- For Unreal Automation Tests, the first real blocker was not test code but host-project plugin loading. Pointing the host project at the maintained plugin and explicitly building the editor target before running tests was necessary to get stable results
- The safest first Unreal test batch is editor-only health checks executed through `UMCPBridge::ExecuteCommand`, not socket-level or asset-heavy scenarios. That keeps failures attributable to plugin bootstrap and command contracts rather than project content noise
