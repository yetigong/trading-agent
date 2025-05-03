#!/bin/bash

# Configuration
AWS_REGION="us-west-2"
ECR_REPOSITORY="trading-agent"
ECS_CLUSTER="trading-agent-cluster"
ECS_SERVICE="trading-agent-service"

# Get AWS account ID
AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)

# Login to ECR
aws ecr get-login-password --region $AWS_REGION | docker login --username AWS --password-stdin $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com

# Build and tag the Docker image
docker build -t $ECR_REPOSITORY .
docker tag $ECR_REPOSITORY:latest $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/$ECR_REPOSITORY:latest

# Push the image to ECR
docker push $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/$ECR_REPOSITORY:latest

# Update the task definition
sed -i "s/<YOUR_ACCOUNT_ID>/$AWS_ACCOUNT_ID/g" task-definition.json
sed -i "s/<REGION>/$AWS_REGION/g" task-definition.json

# Register the new task definition
TASK_DEFINITION=$(aws ecs register-task-definition --cli-input-json file://task-definition.json)
TASK_REVISION=$(echo $TASK_DEFINITION | jq -r '.taskDefinition.revision')

# Update the service
aws ecs update-service --cluster $ECS_CLUSTER --service $ECS_SERVICE --task-definition $ECR_REPOSITORY:$TASK_REVISION --force-new-deployment

echo "Deployment completed successfully!" 