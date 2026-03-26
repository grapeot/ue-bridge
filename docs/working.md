# Working Log

## Changelog

### 2026-03-25

- Replaced the hottest direct-field `FMCPEditorContext` usages with explicit API methods for last-created node and material-session state access
- Added `FMCPEditorContext` helpers for current material access, registered material node lookup/removal, and last-node tracking so actions stop reaching into context internals as freely
- Verified the `MCPContext` API refactor is behavior-preserving: Workflow A health, Blueprint create/compile, and graph create/connect/delete all still pass in the checked-in `UEBridgeHost`
- Added the first graph/node workflow automation test: `UEEditorMCP.Graph.WorkflowA.CreateConnectDelete`
- Verified the node workflow passes in the checked-in `hosts/UEBridgeHost` host: create blueprint, add nodes, inspect pins, connect, delete, and confirm missing-node failure shape
- Confirmed the coverage net now protects not only host health and Blueprint compile, but also the first high-value node add/delete/connect path that future graph refactors will depend on
- Moved `UEBridgeHost` into `ue_bridge_skill/hosts/UEBridgeHost`, so the repository now contains a checked-in self-contained automation host instead of depending on an external sibling project
- Repointed the in-repo host's `Plugins/UEEditorMCP` symlink to the maintained repo-local `plugin/` directory and verified the host still builds as `UEBridgeHostEditor`
- Added `python/tests/test_integration_workflow_a.py` as a host-agnostic Python ↔ Unreal integration suite covering `doctor`, `verify`, `get_context`, `create_blueprint`, and `compile`
- Added `scripts/run_python_unreal_integration.sh` to build a host, launch Unreal, wait for `ue-bridge verify`, and run the Workflow A Python integration suite end-to-end
- Verified the checked-in `hosts/UEBridgeHost/UEBridgeHost.uproject` can run the integration flow successfully from the repo: 4 Python integration tests passed end-to-end
- Extracted the monolithic `UMCPBridge::RegisterActions()` body into a dedicated `FUEEditorActionRegistry` composition layer (`ActionRegistry.h/.cpp`)
- Verified the `ActionRegistry` refactor is behavior-preserving: `UEBridgeHost` still passes the 6-test Workflow A suite and the `UEEditorMCP.Blueprint.WorkflowA.CreateAndCompile` contract test with exit code 0
- Confirmed the first structural de-MCP step can proceed under existing coverage without changing transport or public command semantics
- Expanded the Unreal Automation baseline from 4 tests to 6 deterministic Workflow A tests across both `UEBridgeHost` and `CharacterActionRoom`
- Added `UEEditorMCP.Health.WorkflowA.GetPIEStateStopped` and `UEEditorMCP.Health.WorkflowA.LogControlSurface`
- Verified the expanded Workflow A batch passes in both hosts: 6 passed, 0 failed, exit code 0
- Added the first Blueprint-heavy representative test: `UEEditorMCP.Blueprint.WorkflowA.CreateAndCompile`
- Verified `CreateAndCompile` passes cleanly in both `UEBridgeHost` and `CharacterActionRoom`: 1 passed, 0 failed, 0 warnings
- Confirmed the current Unreal test matrix now protects the most important pre-refactor seams: module load, bridge availability, readiness, logs, PIE baseline state, and Blueprint create/compile
- Created the smallest reusable automation host project at `self_learning/ue_bridge_host/UEBridgeHost` from the UE 5.7 `TP_Blank` template
- Renamed the template module/target from `TP_Blank` to `UEBridgeHost`, set `EngineAssociation` to `5.7`, and symlinked `Plugins/UEEditorMCP` to the maintained `ue_bridge_skill/plugin`
- Built `UEBridgeHostEditor` successfully and verified the same `UEEditorMCP.Health` suite passes in the smallest host project: 4 passed, 0 failed, exit code 0
- Confirmed we now have two useful host tiers: `UEBridgeHost` for stable automation baseline and `CharacterActionRoom` for higher-noise smoke/integration coverage
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
- For a smallest reproducible host on macOS installed builds, copying `TP_Blank` was more reliable than trying to synthesize a project from scratch or using a content-only template. The extra C++ module/targets were worth it because they made command-line builds and automation runs straightforward
- A two-host strategy is now justified: one tiny host for deterministic automation, one real example project for smoke coverage. That should remain the testing architecture unless Unreal CI requirements force a different split
- Build and automation execution for the same host must be serialized, not parallelized. Running the editor before the project plugin dylib is deployed can produce false "module could not be found" failures that look like product bugs but are really orchestration mistakes
- For Blueprint contract tests, a unique per-run asset name is safer than create-then-delete on the same static path. Immediate deletion caused noisy AssetRegistry warnings; unique names kept the test signal clean enough for automation
- The right first refactor target was not `MCPServer`, but the oversized `RegisterActions()` composition point. Extracting registration into a dedicated registry improved maintainability without reopening transport risk or forcing a naming migration too early
- After `ActionRegistry`, the next safe de-MCP step was not a transport rewrite but shrinking direct state reach-through in `MCPContext`. Replacing field pokes with explicit context methods gave us a cleaner boundary without triggering a semantic migration
- A self-contained host only becomes real when it is versioned inside the plugin repo and the integration script can launch it from a clean shell. Creating a smallest host outside the repo was a useful proof, but checking it into `hosts/UEBridgeHost` was the point where it became a maintainable product asset
- Host-agnostic Python integration tests are a better long-term base than project-specific ones. They let us verify the core Workflow A contract without depending on arbitrary gameplay assets from a larger example project
- The first graph/node test should stay workflow-shaped instead of node-taxonomy-shaped. A single create→inspect→connect→delete scenario gave much better signal than trying to enumerate every node class up front
