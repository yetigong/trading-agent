#!/bin/bash

# Exit on error
set -e

# Get the project root directory (where this script is located)
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
DOCKERFILE_PATH="$SCRIPT_DIR/Dockerfile"

echo "Project root: $PROJECT_ROOT"
echo "Dockerfile path: $DOCKERFILE_PATH"

# Check if .env file exists
if [ ! -f "$PROJECT_ROOT/.env" ]; then
    echo "Error: .env file not found at $PROJECT_ROOT/.env"
    echo "Please create a .env file with your API keys and configuration."
    echo "Required environment variables:"
    echo "  OPENAI_API_KEY=your_openai_api_key"
    echo "  GOOGLE_API_KEY=your_google_api_key"
    echo "  ANTHROPIC_API_KEY=your_anthropic_api_key"
    echo "  ALPACA_API_KEY=your_alpaca_api_key"
    echo "  ALPACA_SECRET_KEY=your_alpaca_secret_key"
    echo "  ALPACA_ENDPOINT=https://paper-api.alpaca.markets"
    echo "  TRADING_CYCLE_INTERVAL=30"
    echo "  LOG_LEVEL=INFO"
    exit 1
fi

# Build the container
echo "Building container..."
cd "$PROJECT_ROOT" && podman build -t trading-agent:local -f "$DOCKERFILE_PATH" .

# Run the container
echo "Running container..."
podman run -it \
    --name trading-agent \
    --rm \
    -v "$PROJECT_ROOT/.env:/app/.env:ro" \
    trading-agent:local 