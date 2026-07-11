#!/bin/bash
# Sync API keys from local .env into AWS SSM Parameter Store for ECS.
set -euo pipefail

AWS_REGION="${AWS_REGION:-us-west-2}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"
ENV_FILE="${ENV_FILE:-$ROOT_DIR/.env}"

if [ ! -f "$ENV_FILE" ]; then
  echo "Error: .env file not found at $ENV_FILE"
  exit 1
fi

load_env() {
  while IFS= read -r line || [[ -n "$line" ]]; do
    [[ "$line" =~ ^[[:space:]]*# ]] && continue
    [[ -z "${line// }" ]] && continue
    line="${line%%#*}"
    line="${line%"${line##*[![:space:]]}"}"
    line="${line#"${line%%[![:space:]]*}"}"
    if [[ "$line" =~ ^([A-Za-z_][A-Za-z0-9_]*)=(.*)$ ]]; then
      export "${BASH_REMATCH[1]}=${BASH_REMATCH[2]}"
    fi
  done < "$ENV_FILE"
}

put_param() {
  local name="$1"
  local value="$2"
  if [ -z "$value" ]; then
    echo "Skipping empty value for $name"
    return 0
  fi
  echo "Updating $name"
  aws ssm put-parameter \
    --name "$name" \
    --value "$value" \
    --type SecureString \
    --overwrite \
    --region "$AWS_REGION" \
    --output text >/dev/null
}

load_env

echo "Syncing trading-agent secrets to SSM (${AWS_REGION})..."
put_param /trading-agent/alpaca-api-key "${ALPACA_API_KEY:-}"
put_param /trading-agent/alpaca-secret-key "${ALPACA_SECRET_KEY:-}"
put_param /trading-agent/google-api-key "${GOOGLE_API_KEY:-}"
put_param /trading-agent/anthropic-api-key "${ANTHROPIC_API_KEY:-}"
put_param /trading-agent/openai-api-key "${OPENAI_API_KEY:-}"
put_param /trading-agent/huggingface-api-key "${HUGGINGFACE_API_KEY:-}"
put_param /trading-agent/finnhub-api-key "${FINNHUB_API_KEY:-}"
put_param /trading-agent/fmp-api-key "${FMP_API_KEY:-}"

echo "Done. Parameters are stored under /trading-agent/* in SSM."
