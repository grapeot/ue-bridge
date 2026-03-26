# UE Bridge Editor PRD

## Product Goal

Build an AI-first Unreal Editor bridge that lets an AI agent install, verify, diagnose, and use Unreal Editor automation without depending on manual GUI-first workflows.

The product is not an MCP product. It is a local editor bridge with:

- a repo-contained validation host
- a Python control surface
- a local command server inside Unreal Editor
- AI-facing docs and skills

## Primary User

The primary user is **an AI agent**, not a human operator.

Humans still need to understand the system, but the default path must optimize for:

- machine-verifiable checks
- low-ambiguity command surfaces
- short feedback loops
- explicit failure categorization

## Core Jobs To Be Done

1. Install the bridge into a UE project.
2. Verify that Unreal Editor is loaded, reachable, and ready.
3. Use CLI or Python to automate editor work.
4. Recover when installation or execution fails.
5. Evolve the plugin safely under automation coverage.

## Product Surface

### 1. Checked-in validation host

`hosts/UEBridgeHost/UEBridgeHost.uproject`

This is the default automation host for deterministic validation.

### 2. Python package

`python/ue_bridge`

This is the canonical control surface.

### 3. CLI

`ue-bridge`

This is the thin surface for one-off tasks and structured verification.

### 4. Local command server in Unreal Editor

This is the in-editor bridge runtime. It should be treated as a bridge command runtime, not as an MCP product.

### 5. AI-facing docs and skills

- `README.md`
- `skills/ue_editor_installation.md`
- `skills/ue_editor_usage.md`

These are part of the product surface, not just developer notes.

## Default User Journey

1. Start from the checked-in host or a target UE project.
2. Install the plugin.
3. Run `ue-bridge doctor`.
4. Run `ue-bridge verify`.
5. Run `scripts/run_python_unreal_integration.sh` for repo-contained validation when appropriate.
6. Use CLI for simple tasks.
7. Use Python for multi-step workflows.

## Success Criteria

The product is successful if an AI can:

1. infer the shortest correct path from the docs
2. verify readiness without manual GUI inspection
3. execute basic editor automation without guesswork
4. recover from common failures with structured signals
5. rely on checked-in validation infrastructure during development

## Non-Goals

- Rewriting the local TCP transport into HTTP/REST purely for aesthetics
- Requiring a large example game project as the default host
- Treating raw command access as the primary UX
- Treating GUI inspection as the primary validation path

## Current Gaps

1. Health and diagnostics can still be more structured.
2. Unreal automation coverage is meaningful but still not broad enough.
3. Several large action files remain hotspot candidates.
4. A real end-to-end usability trial on a fresh temporary project is still needed.

## Product Constraints

- Keep the system simple and reliable over theoretically cleaner but riskier rewrites.
- Preserve machine-verifiable validation as the default path.
- Keep the checked-in host as the canonical automation baseline.
- Continue using tests as the guardrail for structural refactors.
