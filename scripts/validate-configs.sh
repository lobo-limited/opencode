#!/usr/bin/env bash
#
# validate-configs.sh — Validate all inference service YAML configs
# against the JSON Schema.
#
# Usage:
#   ./scripts/validate-configs.sh              # validate all */config.yaml
#   ./scripts/validate-configs.sh <file> ...    # validate specific files
#
# Requires: python3 with PyYAML (yaml) or python3-yaml system package.
# Falls back to a basic structural check if python3 is unavailable.
#
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
SCHEMA="$REPO_DIR/inference-config.schema.json"
EXIT_CODE=0

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

pass()  { echo -e "  ${GREEN}✓${NC} $1"; }
fail()  { echo -e "  ${RED}✗${NC} $1"; EXIT_CODE=1; }
warn()  { echo -e "  ${YELLOW}⚠${NC} $1"; }

# --- Collect config files ------------------------------------------------
if [ $# -gt 0 ]; then
    CONFIG_FILES=("$@")
else
    # Find all */config.yaml (one dir deep)
    mapfile -t CONFIG_FILES < <(find "$REPO_DIR" -maxdepth 2 -name 'config.yaml' \
        -not -path '*/.git/*' -not -path '*/.vibe/*' -not -path '*/node_modules/*' \
        -not -path '*/scripts/*' | sort)
fi

if [ ${#CONFIG_FILES[@]} -eq 0 ]; then
    echo -e "${YELLOW}No config.yaml files found to validate.${NC}"
    exit 0
fi

echo "=== OpenCode Inference Config Validator ==="
echo "Schema: $SCHEMA"
echo "Configs: ${#CONFIG_FILES[@]} found"
echo ""

# --- Check schema exists -------------------------------------------------
if [ ! -f "$SCHEMA" ]; then
    fail "Schema file not found: $SCHEMA"
    exit 1
fi

# --- Check dependencies --------------------------------------------------
USE_PYTHON=false
if command -v python3 &>/dev/null; then
    if python3 -c "import yaml, json, jsonschema, sys; sys.exit(0)" 2>/dev/null; then
        USE_PYTHON=true
    elif python3 -c "import yaml, json; sys.exit(0)" 2>/dev/null; then
        warn "jsonschema package not installed — falling back to structural validation"
        warn "Install: pip install jsonschema"
    else
        warn "PyYAML not installed — falling back to basic structural validation"
        warn "Install: pip install pyyaml jsonschema"
    fi
else
    warn "python3 not available — falling back to basic structural validation"
fi

# --- Validate each config ------------------------------------------------
for config in "${CONFIG_FILES[@]}"; do
    rel="${config#$REPO_DIR/}"
    echo "Checking: $rel"

    if $USE_PYTHON; then
        # Full schema validation
        if python3 -c "
import yaml, json, jsonschema, sys

with open('$config') as f:
    data = yaml.safe_load(f)

with open('$SCHEMA') as f:
    schema = json.load(f)

try:
    jsonschema.validate(instance=data, schema=schema)
    sys.exit(0)
except jsonschema.exceptions.ValidationError as e:
    print(f'  {e.message}')
    sys.exit(1)
"; then
            pass "Validates against schema"
        else
            fail "Schema validation failed"
        fi
    else
        # Basic structural validation
        errors=0

        # Check it's a file
        if [ ! -f "$config" ]; then
            fail "File not found"
            continue
        fi

        # Parse using simple grep-based checks
        for field in service inference_endpoint model api_key_env; do
            if ! grep -q "^${field}:" "$config" 2>/dev/null; then
                fail "Missing required field: $field"
                ((errors++))
            fi
        done

        # Check non-empty values for required fields
        for field in service inference_endpoint model api_key_env; do
            val=$(grep "^${field}:" "$config" 2>/dev/null | sed 's/^[^:]*:[[:space:]]*//')
            if [ -z "$val" ]; then
                fail "Empty value for required field: $field"
                ((errors++))
            fi
        done

        if [ "$errors" -eq 0 ]; then
            pass "Basic structure valid"
        fi
    fi

    # --- Cross-checks (always done) --------------------------------------
    svc=$(grep "^service:" "$config" 2>/dev/null | sed 's/^[^:]*:[[:space:]]*//')
    dir_name=$(basename "$(dirname "$config")")
    if [ -n "$svc" ] && [ "$svc" != "$dir_name" ]; then
        warn "service name '$svc' differs from directory name '$dir_name'"
    fi

    echo ""
done

# --- Summary -------------------------------------------------------------
if [ "$EXIT_CODE" -eq 0 ]; then
    echo -e "${GREEN}All configs validated successfully.${NC}"
else
    echo -e "${RED}Some configs failed validation.${NC}"
fi
exit "$EXIT_CODE"
