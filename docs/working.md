# Working Log

## Changelog

### 2026-03-25

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
