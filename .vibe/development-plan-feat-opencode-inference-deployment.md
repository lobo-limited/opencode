# Development Plan: Desktop (feat/opencode-inference-deployment branch)

*Generated on 2026-05-12 by Vibe Feature MCP*
*Workflow: [epcc](https://codemcp.github.io/workflows/workflows/epcc)*

## Goal
Standardize and validate inference service configurations for the fleet's OpenCode deployment — defining how OpenCode connects to self-hosted vLLM endpoints on supercat, tigerking, and whiskerhead nodes using the qwen3-30b:32k model.

## Key Decisions
- **Config format**: YAML with fields `service`, `inference_endpoint`, `model`, `api_key_env` — simple key-value pairs sufficient for fleet registration without JSON complexity
- **Validation**: JSON Schema (`inference-config.schema.json`) validates every `*/config.yaml` — single source of truth, no per-service boilerplate
- **Registry**: `services.json` aggregates all individual configs into a single deploy-time manifest for tooling to consume
- **OpenCode integration**: Fleet inference endpoints are OpenAI-compatible (vLLM `/v1/...`), so OpenCode can connect via any OpenAI-compatible provider config using `@ai-sdk/openai-compatible`
- **No live secrets**: Configs reference API keys via env-var names (`api_key_env`), not literal values
- **Repository**: This is a configuration tracking repo (not the OpenCode app source). The GitHub repo must exist before PR creation.

## Notes
*Additional context and observations*

## Explore
### Tasks
- [x] Identify fleet nodes requiring inference configs (supercat, tigerking, whiskerhead)
- [x] Research OpenCode config format and provider model
- [x] Locate and read Saba PWA documentation for context on fleet architecture

### Completed
- [x] Created development plan file
- [x] Explored fleet architecture — supercat is vLLM inference hub, tigerking is dual-GPU native vLLM + LiteLLM, whiskerhead is third node
- [x] Researched OpenCode — uses `opencode.json` with provider definitions supporting OpenAI-compatible endpoints via `@ai-sdk/openai-compatible`
- [x] Located Saba as the fleet chat PWA on supercat (fronts vLLM fleet)

## Plan
### Tasks
- [ ] *To be added when this phase becomes active*

### Completed
*None yet*

## Code
### Tasks
- [x] Create JSON Schema (`inference-config.schema.json`) for config validation
- [x] Create config validator script (`scripts/validate-configs.sh`)
- [x] Create aggregated service registry (`services.json`)
- [x] Create deploy docs and OpenCode provider configuration guide

### Completed
- [x] Created `inference-config.schema.json` — draft-07 JSON Schema validating required fields (service, inference_endpoint, model, api_key_env) with patterns, examples, and descriptions
- [x] Created `scripts/validate-configs.sh` — Python/fallback validator against the schema; validates all `*/config.yaml` files; cross-checks service name vs directory name
- [x] Validated all 3 existing configs (supercat, tigerking, whiskerhead) — all pass
- [x] Created `services.json` — aggregated service registry with per-node descriptions
- [x] Created `opencode.fleet.json` — ready-to-use OpenCode V2 provider config for connecting to the fleet
- [x] Created `DEPLOY.md` — deployment documentation with architecture diagram, quick-start, and per-node configuration guide

## Commit
### Tasks
- [x] Code cleanup — verify no debug output, TODOs, or experimental code remains
- [x] Documentation review — ensure docs reflect final implementation state
- [x] Final validation — run config validation suite to confirm nothing broke
- [x] Commit and push changes to remote

### Completed
- [x] Cleanup: No debug statements, TODOs, or experimental code found in new files. Config YAMLs are minimal and clean.
- [x] Documentation: DEPLOY.md, opencode.fleet.json, and services.json all match the actual config structure. Plan file updated with full task completion records.
- [x] Validation: `python3 -c jsonschema.validate` confirmed all 3 configs pass the schema. `scripts/validate-configs.sh` also passes for all configs.
- [x] Final state: Everything is ready for PR — schema, validator, registry, provider config, and deploy docs are coherent and cross-reference correctly.
- [x] Git: Committed 6 files (406 insertions) as `7917542` and pushed to `feat/opencode-inference-deployment` on origin.

## Saba CLI Launcher
### Tasks
- [x] Create `saba` script — fleet-native coding assistant launcher
- [x] Fix saba-shim long-context routing (`SABA_LONG_CTX_URL` → vLLM at 8500)
- [x] Test full chain: claude binary → SSH tunnel → saba-shim → vLLM → cortejo:latest

### Completed
- [x] Created `~/.local/bin/saba` — shell script that sets `ANTHROPIC_BASE_URL` and `ANTHROPIC_API_KEY` to route the `claude` binary through saba-shim on supercat
- [x] Fixed saba-shim env: added `SABA_LONG_CTX_URL=http://127.0.0.1:8500/v1/chat/completions` (was defaulting to port 8099 which isn't running)
- [x] Tested: `saba "say hello"` returns Saba persona response from cortejo:latest on supercat vLLM
- [x] Commands: `saba` (TUI), `saba "prompt"` (one-shot), `saba status`, `saba models`
- [x] Auth bypass: `ANTHROPIC_API_KEY=local` + `ANTHROPIC_BASE_URL` pointing to saba-shim satisfies claude binary's auth check

### Key Decisions
- **Engine choice**: Uses `claude` binary as TUI frontend — provides Claude Code UX while routing through saba-shim to local vLLM. Alternative was opencode TUI, but 32k context limit causes system prompt overflow.
- **Shim fix**: `SABA_LONG_CTX_URL` env var was missing, causing shim to try port 8099. Added explicit URL pointing to vLLM at 8500.
- **No auth cloud calls**: `ANTHROPIC_API_KEY=local` prevents claude binary from contacting Anthropic servers. All traffic routes through local saba-shim.

---
*This plan is maintained by the LLM. Tool responses provide guidance on which section to focus on and what tasks to work on.*