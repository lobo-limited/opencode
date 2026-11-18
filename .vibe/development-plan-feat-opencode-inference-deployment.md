# Development Plan: Desktop (feat/opencode-inference-deployment branch)

*Generated on 2026-05-12 by Vibe Feature MCP*
*Workflow: [epcc](https://codemcp.github.io/workflows/workflows/epcc)*

## Goal
Standardize and validate inference service configurations for the fleet's OpenCode deployment — defining how OpenCode connects to self-hosted vLLM endpoints on supercat, tigerking, and whiskerhead nodes using the live model inventory verified against the gato-fleet proxy (supercat :8500).

## Key Decisions
- **Opencode CLI update (2026-08-05)**: Updated the opencode npm package in ~/.opencode to latest version (1.18.13) via npm update.
- **Model lists update (2026-08-05)**: Updated `opencode.fleet.json` to include models `saba-coder` (Qwen3-Coder-30B-A3B-NVFP4, 32k ctx) and `cortejo:latest` (Ornith-9B NVFP4, 65536 ctx). Verified saba-pwa `MODELS` array already reflects these models.
- **Client-side optimizations (2026-08-11)**: Applied `ControlPersist` 30m to `~/.ssh/config`, implemented a 300s-TTL model list cache in `saba-local` to reduce gateway hits, and added a `saba.env` lock file to pin routing to the supercat gateway.
- **Network/Firewall (2026-08-11)**: Whitelisted `192.168.6.142` in `fleet4` set on supercat. Switched node to static IP via `nmcli` to ensure whitelist persistence.
- **vLLM Optimizations (2026-08-05)**: Standardized `vllm-text` with `fp8_e4m3` KV cache, adjusted `vllm-ocr` utilization to 0.10, and applied exact `--kv-cache-memory=14546836194` budget to `vllm-coder`.
- **Commit-Phase doc correction (2026-11-18)**: `inference-config.schema.json` model examples no longer advertise the retired `qwen3-30b:32k`; they now list the verified live models (`cortejo:latest`, `saba-agent`, `bge-m3`). Plan Goal de-scoped from a single stale model to the gato-fleet-verified inventory. Rationale: the 2026-08-13 decision makes the proxy authoritative, so shipping docs must not contradict it.

## Notes
*Additional context and observations*

### Fleet Sync (2026-08-05)
Pulled latest fleet components from `supercat` to this machine (file-level rsync, since supercat repos have no git remote):
- `~/saba-shim` — Anthropic⇄OpenAI translator (incl. uncommitted working-tree changes; excludes `.env`/logs)
- `~/saba-pwa` — fleet chat PWA (excludes `saba_auth.db`, logs)
- `~/saba-ops` — ops playbook, healthcheck, selfheal
- `~/inference-api` — inference API + startup scripts (excludes `inference.db`)
- `~/saba-rag` — RAG service code only (excluded 130M `store.governance.json` vector store)
- Skipped: `saba-rag` data store; all secrets/databases/logs stay on supercat

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
- [x] Created `opencode.fleet.json` — OpenCode provider config pointing to **`aeson-7/gemma`** — Gemma SR is https://gemma.marginalia.services:1035 with `@anthropic/gm-sweden` (12B) with no 32k context. So **not** the 30B qwen3-30b:32k we trained on supercat.

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
- **Final Cleanup (2026-08-11)**: Verified no debug output, TODOs, or experimental code blocks remain in the deployment artifacts. All config files are production-ready and minimal.
- **Documentation Finalized (2026-08-11)**: Confirmed all configs match the `inference-config.schema.json` and are correctly represented in `services.json` and `opencode.fleet.json`.
- **Validation Complete (2026-08-11)**: Ran `scripts/validate-configs.sh` and confirmed 100% success for all fleet nodes.
- [x] Git: Committed 6 files (406 insertions) as `7917542` and pushed to `feat/opencode-inference-deployment` on origin.
- **Commit-Phase re-verification (2026-11-18)**: Re-ran all four Commit tasks against the final state. (1) Cleanup: no debug output, TODOs, or experimental code in any deployment artifact — the only `TODO`/`print` matches are the words inside this plan file. (2) Documentation: found and fixed the stale `qwen3-30b:32k` example in `inference-config.schema.json`; `DEPLOY.md`, `services.json`, and `opencode.fleet.json` otherwise match the three minimal config YAMLs and the 2026-08-13 inventory. (3) Validation: `scripts/validate-configs.sh` passes 3/3 configs against the schema; all three JSON artifacts parse cleanly. (4) Git: branch tracked in sync with `origin/feat/opencode-inference-deployment`; only log files (`logs/`) remain dirty and are intentionally excluded from feature commits.

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

## Rollout allspark + magic context to fleet saba
### Tasks
- [x] Add `agent.allspark` to supercat `~/.config/opencode/opencode.json`
- [x] Add `command.allspark` to supercat `~/.config/opencode/opencode.json`
- [x] Install `@cortexkit/opencode-magic-context@0.36.0` plugin on supercat
- [x] Add `agent.allspark` to tigerking `~/.config/opencode/opencode.json`
- [x] Add `command.allspark` to tigerking `~/.config/opencode/opencode.json`
- [x] Add `@cortexkit/opencode-magic-context@0.36.0` plugin to tigerking `~/.config/opencode/opencode.json`
- [x] Install `@cortexkit/opencode-magic-context@0.36.0` plugin on tigerking

### Completed
- [x] Verified supercat already has allspark agent, allspark command, and magic-context plugin entry; installed plugin package under `~/.config/opencode/node_modules`.
- [x] Updated tigerking `~/.config/opencode/opencode.json` with allspark agent (model `ollama/qwen2.5-coder:14b`), allspark command, and magic-context plugin.
- [x] Created remote backups: `~/.config/opencode/opencode.json.bak-allspark-20260811` on both nodes.
- [x] Verified JSON validity and that `~/bin/opencode --version` still loads successfully on tigerking and supercat.

### Key Decisions
- **Model choice (tigerking)**: Used `ollama/qwen2.5-coder:14b` for the allspark agent because it is the local coding-tuned model and avoids depending on the local saba-shim being up.
- **Plugin installation**: Installed `@cortexkit/opencode-magic-context@0.36.0` into `~/.config/opencode/node_modules` on both nodes so the plugin is resolvable without relying on auto-download.
- **Remote access**: tigerking was reached via `ssh -J supercat tigerking` because direct Tailscale path from chainbro was down; supercat could still route to tigerking.

## Complete
### Tasks
- [x] All rollout tasks finished; feature is production-ready.

### Completed
- [x] Verified allspark agent, allspark command, and magic-context plugin are configured and installed on both fleet nodes.

## Fleet Model Sync (2026-08-13)
### Tasks
- [x] Pull latest fleet model inventory from the gato-fleet proxy (supercat :8500)
- [x] Update `opencode.fleet.json` with live fleet models
- [x] Update per-node `config.yaml` model fields
- [x] Update `services.json` and `DEPLOY.md` to match
- [x] Re-run validation suite

### Completed
- [x] Inventory verified live: supercat serves chat (`cortejo:latest`, `saba-agent`, `cortejo-9b-v1` loaded; `saba-coder` :8019 configured-asleep); tigerking serves embed/voice (`bge-m3`, `bge-reranker-v2-m3`, `ctx-holder`, `kokoro`, `voice-loop`, `whisper-base`); whiskerhead is NOT in the live proxy (0 matches).
- [x] `opencode.fleet.json` now lists `cortejo:latest`, `saba-agent`, `saba-coder`, `cortejo-9b-v1` with verified context limits (64k/32k).
- [x] `supercat/config.yaml` → `cortejo:latest`; `tigerking/config.yaml` → `bge-m3`; `whiskerhead/config.yaml` → `cortejo:latest` (inactive node, retained for compatibility).
- [x] `services.json` regenerated with 2026-08-13 inventory + per-node descriptions; `DEPLOY.md` table + fleet model inventory section updated.
- [x] `scripts/validate-configs.sh` passes all 3 configs; both JSON artifacts valid.

### Key Decisions
- **Authoritative source**: The gato-fleet proxy (`supercat:8500`, `~/gato-fleet/proxy/`) is the source of truth for fleet model inventory, not the older `qwen3-30b:32k` naming — the fleet no longer serves that model.
- **whiskerhead**: Not advertising in the live proxy — entry retained (model set to shared `cortejo:latest`) rather than deleted, to preserve schema compatibility.
- **tigerking primary**: `bge-m3` reflects the always-hot embed/rerank role; chat is supercat-centric in the current deployment.

---
*This plan is maintained by the LLM. Tool responses provide guidance on which section to focus on and what tasks to work on.*