# UE Bridge Editor RFC

## Purpose

This RFC records the current architecture direction for the Unreal Editor bridge after the de-MCP migration.

## Architectural Direction

### 1. Bridge-first, not MCP-first

The bridge is the core concept.

The system should be understood in terms of:

- bridge runtime
- command routing
- editor context
- validation host
- Python control surface

Any remaining MCP residue is legacy, not architecture.

### 2. Keep the current local transport

The system continues to use:

- local TCP
- length-prefixed JSON
- in-editor command handling

The current direction is to simplify naming and responsibilities around this transport, not replace it with HTTP/REST.

### 3. Separate layers clearly

The intended layering is:

1. **Packaging layer** — plugin/module/uplugin/host wiring
2. **Runtime transport layer** — socket, session, client handler, timeout, game-thread dispatch
3. **Command routing layer** — command dispatch, action registry, execution boundaries
4. **Editor capability layer** — Blueprint, graph, material, UMG, project, diagnostics actions
5. **Python/CLI layer** — human- and AI-facing control surface

### 4. Checked-in host is part of the architecture

`hosts/UEBridgeHost` is not just a convenience project. It is part of the bridge architecture because it provides:

- deterministic build validation
- deterministic automation validation
- deterministic integration validation

## Current Technical Decisions

### Accepted

- Keep local TCP transport.
- Keep `ue_bridge` as the canonical Python surface.
- Keep `ue-bridge doctor` / `verify` as the default validation path.
- Keep `UEBridgeHost` as the canonical checked-in validation host.
- Continue de-MCP work incrementally under test protection.

### Rejected for now

- Full HTTP/REST rewrite
- Rebuilding transport from scratch
- Requiring a large example project as the default host
- Unbounded refactors without automation coverage

## Coverage Gate for Structural Work

Structural work is allowed only because the repo now has meaningful guardrails:

- health suite
- blueprint create/compile representative test
- graph create/connect/delete representative test
- PIE smoke representative test
- Python integration flow
- raw socket representative case

This RFC assumes future architecture work keeps that discipline.

## Remaining RFC-Level Questions

1. Should any compatibility layer remain after the final usability trial?
2. How far should command diagnostics go before they become overdesigned?
3. Which oversized action files should be split first after the current module split?
4. What is the minimum test set required before deeper runtime restructuring?

## Next RFC Checkpoint

After the temporary-project usability trial, revisit:

- whether the docs still represent the shortest path
- whether diagnostics are specific enough
- whether more runtime restructuring is justified
