#!/bin/bash

# Exit on error
set -e

# Configuration
AWS_REGION="us-west-2"
ECR_REPO="998982002518.dkr.ecr.us-west-2.amazonaws.com/trading-agent"
ECS_CLUSTER="trading-agent-cluster"
ECS_SERVICE="trading-agent-service"
LOG_GROUP="/ecs/trading-agent"
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
ROOT_DIR="$( cd "$SCRIPT_DIR/../.." && pwd )"

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Check if .env file exists
if [ ! -f "$ROOT_DIR/.env" ]; then
    echo -e "${RED}Error: .env file not found at $ROOT_DIR/.env${NC}"
    exit 1
fi

# Load environment variables
source "$ROOT_DIR/.env"

echo "🚀 Starting deployment process..."

# Build the image
echo "📦 Building container image..."
cd "$ROOT_DIR"
podman build -t trading-agent -f aws/deployment/Dockerfile .

# Tag the image
echo "🏷️  Tagging image..."
podman tag trading-agent:latest ${ECR_REPO}:latest

# Push to ECR
echo "⬆️  Pushing to ECR..."
aws ecr get-login-password --region us-west-2 | podman login --username AWS --password-stdin 998982002518.dkr.ecr.us-west-2.amazonaws.com
podman push ${ECR_REPO}:latest

# Create CloudWatch log group if it doesn't exist
echo "📝 Setting up CloudWatch logs..."
aws logs create-log-group --log-group-name ${LOG_GROUP} --region ${AWS_REGION} || true

# Create temporary task definition with actual values
echo "📋 Preparing task definition..."
TEMP_TASK_DEF="/tmp/task-definition-$(date +%s).json"
cat "${SCRIPT_DIR}/task-definition.json" | \
    sed "s/{{OPENAI_API_KEY}}/${OPENAI_API_KEY}/g" | \
    sed "s/{{GOOGLE_API_KEY}}/${GOOGLE_API_KEY}/g" | \
    sed "s/{{ANTHROPIC_API_KEY}}/${ANTHROPIC_API_KEY}/g" | \
    sed "s/{{ALPACA_API_KEY}}/${ALPACA_API_KEY}/g" | \
    sed "s/{{ALPACA_SECRET_KEY}}/${ALPACA_SECRET_KEY}/g" > "${TEMP_TASK_DEF}"

# Register task definition
echo "📋 Registering task definition..."
aws ecs register-task-definition --cli-input-json "file://${TEMP_TASK_DEF}"

# Clean up temporary file
rm "${TEMP_TASK_DEF}"

# Update service
echo "🔄 Updating ECS service..."
aws ecs update-service --cluster ${ECS_CLUSTER} --service ${ECS_SERVICE} --force-new-deployment

echo -e "${GREEN}✅ Deployment completed successfully!${NC}"
echo "📊 Check the CloudWatch logs for container output:"
echo "   https://${AWS_REGION}.console.aws.amazon.com/cloudwatch/home?region=${AWS_REGION}#logsV2:log-groups/log-group/${LOG_GROUP}" 