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

### Completed
- [x] Cleanup: No debug statements, TODOs, or experimental code found in new files. Config YAMLs are minimal and clean.
- [x] Documentation: DEPLOY.md, opencode.fleet.json, and services.json all match the actual config structure. Plan file updated with full task completion records.
- [x] Validation: `python3 -c jsonschema.validate` confirmed all 3 configs pass the schema. `scripts/validate-configs.sh` also passes for all configs.
- [x] Final state: Everything is ready for PR — schema, validator, registry, provider config, and deploy docs are coherent and cross-reference correctly.

---
*This plan is maintained by the LLM. Tool responses provide guidance on which section to focus on and what tasks to work on.*