# OpenCode Fleet Inference Deployment

This repository defines the standardized inference service configuration for connecting
[OpenCode](https://opencode.ai) to the self-hosted vLLM fleet.

## Fleet Nodes

| Service      | Inference Endpoint           | Model        | API Key Env                   |
| ------------ | ---------------------------- | ------------ | ----------------------------- |
| supercat     | `http://inference.supercat`  | qwen3-30b:32k | `INFERENCE_SUPERCAT_API_KEY`  |
| tigerking    | `http://inference.tigerking` | qwen3-30b:32k | `INFERENCE_TIGERKING_API_KEY` |
| whiskerhead  | `http://inference.whiskerhead` | qwen3-30b:32k | `INFERENCE_WHISKERHEAD_API_KEY` |

## Configuration Format

Each fleet node has a `config.yaml` with four required fields:

```yaml
service: <node-name>
inference_endpoint: <http://endpoint>
model: <model-id>
api_key_env: <ENV_VAR_NAME>
```

The schema is defined in [`inference-config.schema.json`](./inference-config.schema.json).

## Adding a New Node

1. Create `<node-name>/config.yaml` following the schema
2. Run `./scripts/validate-configs.sh <node-name>/config.yaml` to validate
3. Add the API key environment variable to your OpenCode runtime
4. Update [`services.json`](./services.json) with the new entry

## Connecting OpenCode to the Fleet

OpenCode connects to any OpenAI-compatible endpoint using the `@opencode-ai/ai/providers/openai-compatible`
package. An example config is in [`opencode.fleet.json`](./opencode.fleet.json).

### Quick Start

1. Set the API key:
   ```bash
   export INFERENCE_SUPERCAT_API_KEY="your-api-key-here"
   ```

2. Copy or reference the provider config from `opencode.fleet.json` into your
   `opencode.json` (global at `~/.config/opencode/opencode.json` or per-project).

3. Run OpenCode and select the model:
   ```bash
   opencode
   /models
   # Select "fleet/qwen3-30b-32k"
   ```

### Per-Node Configuration

To target a specific fleet node instead of the default (`supercat`), override `baseURL`:

```json
{
  "providers": {
    "fleet": {
      "settings": {
        "baseURL": "http://inference.tigerking"
      }
    }
  }
}
```

## Validation

```bash
# Validate all configs
./scripts/validate-configs.sh

# Validate a specific config
./scripts/validate-configs.sh tigerking/config.yaml
```

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                      OpenCode                            │
│              (opencode.json provider config)              │
└────────────┬──────────────────────────┬─────────────────┘
             │                          │
     ┌───────▼──────────┐     ┌────────▼────────┐
     │  Fleet Provider   │     │  Other Providers │
     │  (self-hosted)    │     │  (OpenAI, etc)   │
     └───────┬──────────┘     └─────────────────┘
             │
   ┌─────────┼─────────────────┐
   │         │                 │
   ▼         ▼                 ▼
supercat  tigerking       whiskerhead
(vLLM)    (vLLM+LiteLLM)   (vLLM)
```

All fleet nodes expose an OpenAI-compatible API (`/v1/chat/completions`, `/v1/models`,
`/v1/embeddings`) via vLLM. OpenCode connects using the standard compatible provider package.
