# Trading Agent Deployment Guide

This guide explains how to deploy the trading agent to AWS ECS Fargate.

## Prerequisites

1. AWS CLI installed and configured
2. Docker installed
3. AWS account with appropriate permissions
4. VPC and subnets in your AWS account

## Initial Setup

1. **Install AWS CLI** (if not already installed)
```bash
# For macOS
brew install awscli

# For Linux
curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
unzip awscliv2.zip
sudo ./aws/install
```

2. **Configure AWS CLI**
```bash
aws configure
```
Enter your:
- AWS Access Key ID
- AWS Secret Access Key
- Default region (e.g., us-west-2)
- Output format (json)

3. **Create ECR Repository**
```bash
aws ecr create-repository --repository-name trading-agent --region us-west-2

# Authenticate
aws ecr get-login-password | podman login --username AWS --password-stdin 998982002518.dkr.ecr.us-west-2.amazonaws.com
aws ecr get-login-password --region us-west-2 | podman login --username AWS --password-stdin 998982002518.dkr.ecr.us-west-2.amazonaws.com
# Tag and push
podman buildx build --platform linux/amd64 -t trading-agent . 
podman tag trading-agent 998982002518.dkr.ecr.us-west-2.amazonaws.com/trading-agent
podman push 998982002518.dkr.ecr.us-west-2.amazonaws.com/trading-agent
```

4. **Store Secrets in AWS Systems Manager Parameter Store**
```bash
aws ssm put-parameter --name "/trading-agent/alpaca-api-key" --value "" --type SecureString
aws ssm put-parameter --name "/trading-agent/alpaca-secret-key" --value "your-alpaca-secret-key" --type SecureString
aws ssm put-parameter --name "/trading-agent/anthropic-api-key" --value "your-anthropic-api-key" --type SecureString
aws ssm put-parameter --name "/trading-agent/google-api-key" --value "your-google-api-key" --type SecureString
```

## Deployment Steps

1. **Deploy Infrastructure**
```bash
# Replace VPC_ID and SUBNET_IDS with your values
aws cloudformation deploy \
  --template-file cloudformation.yml \
  --stack-name trading-agent \
  --parameter-overrides \
    VpcId=vpc-xxxxx \
    SubnetIds=subnet-xxxxx,subnet-yyyyy \
  --capabilities CAPABILITY_IAM
```

2. **Build and Deploy the Application**
```bash
# Make the deployment script executable
chmod +x deploy.sh

# Run the deployment script
./deploy.sh
```

## Monitoring

1. **View Logs**
```bash
aws logs get-log-events \
  --log-group-name /ecs/trading-agent \
  --log-stream-name ecs/trading-agent/latest
```

2. **Check Service Status**
```bash
aws ecs describe-services \
  --cluster trading-agent-cluster \
  --services trading-agent-service
```

## Maintenance

1. **Update Dependencies**
```bash
# Update requirements.txt
pip freeze > requirements.txt

# Rebuild and deploy
./deploy.sh
```

2. **Clean Up Old Images**
```bash
aws ecr list-images --repository-name trading-agent
aws ecr batch-delete-image --repository-name trading-agent --image-ids <image-ids>
```

## Troubleshooting

1. **Check Task Status**
```bash
aws ecs list-tasks --cluster trading-agent-cluster
aws ecs describe-tasks --cluster trading-agent-cluster --tasks <task-id>
```

2. **View Container Logs**
```bash
aws logs get-log-events \
  --log-group-name /ecs/trading-agent \
  --log-stream-name ecs/trading-agent/<task-id>
```

3. **Common Issues**
- If the task fails to start, check the CloudWatch logs
- If the task is stopping, check the container logs for errors
- If the task is not receiving environment variables, verify the SSM parameters exist

## Cost Estimation

- ECS Fargate: ~$20-30/month (256 CPU units, 512MB memory)
- CloudWatch Logs: ~$5-10/month
- ECR: ~$1-2/month
- Total: ~$30-50/month

## Security Notes

1. All API keys are stored in AWS Systems Manager Parameter Store
2. The ECS task role has minimal permissions
3. The security group only allows necessary inbound traffic
4. All sensitive data is encrypted at rest