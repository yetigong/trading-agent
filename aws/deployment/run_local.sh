#!/bin/bash

# Exit on error
set -e

# Get the project root directory (where this script is located)
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
DOCKERFILE_PATH="$SCRIPT_DIR/Dockerfile"

echo "Project root: $PROJECT_ROOT"
echo "Dockerfile path: $DOCKERFILE_PATH"

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