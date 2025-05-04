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
podman push ${ECR_REPO}:latest

# Create CloudWatch log group if it doesn't exist
echo "📝 Setting up CloudWatch logs..."
aws logs create-log-group --log-group-name ${LOG_GROUP} --region ${AWS_REGION} || true

# Register task definition
echo "📋 Registering task definition..."
aws ecs register-task-definition --cli-input-json file://${SCRIPT_DIR}/task-definition.json

# Update service
echo "🔄 Updating ECS service..."
aws ecs update-service --cluster ${ECS_CLUSTER} --service ${ECS_SERVICE} --force-new-deployment

echo -e "${GREEN}✅ Deployment completed successfully!${NC}"
echo "📊 Check the CloudWatch logs for container output:"
echo "   https://${AWS_REGION}.console.aws.amazon.com/cloudwatch/home?region=${AWS_REGION}#logsV2:log-groups/log-group/${LOG_GROUP}" 