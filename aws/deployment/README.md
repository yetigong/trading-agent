# AWS ECS Fargate Deployment

This directory contains the configuration files and scripts for deploying the trading agent to AWS ECS Fargate.

## Prerequisites

1. AWS CLI installed and configured with appropriate credentials
2. Podman installed (for container builds)
3. AWS ECS cluster created
4. VPC, subnets, and security groups configured
5. ECR repository created

## Files

- `task-definition.json`: Defines the ECS task configuration
- `service-definition.json`: Defines the ECS service configuration
- `deploy.sh`: Deployment script that automates the build and deployment process
- `cloudformation.yaml`: Infrastructure as Code template for AWS resources

## Deployment Options

### 1. Manual Deployment

1. Build and push the container:
   ```bash
   cd /Users/bopan/IdeaProjects/trading-agent
   podman build -t trading-agent .
   podman tag trading-agent:latest 998982002518.dkr.ecr.us-west-2.amazonaws.com/trading-agent:latest
   podman push 998982002518.dkr.ecr.us-west-2.amazonaws.com/trading-agent:latest
   ```

2. Register the task definition:
   ```bash
   aws ecs register-task-definition --cli-input-json file://task-definition.json
   ```

3. Update the service:
   ```bash
   aws ecs update-service --cluster trading-agent-cluster --service trading-agent-service --force-new-deployment
   ```

### 2. Automated Deployment

Use the deployment script:
```bash
./deploy.sh
```

### 3. Infrastructure as Code (CloudFormation)

Deploy all AWS resources using CloudFormation:
```bash
# ONE TIME ONLY - Infrastructure setup
aws cloudformation create-stack \
  --stack-name trading-agent-stack \
  --template-body file://cloudformation.yaml \
  --parameters \
    ParameterKey=VpcId,ParameterValue=vpc-xxxxx \
    ParameterKey=SubnetIds,ParameterValue=subnet-xxxxx,subnet-yyyyy

# FOR EACH CODE UPDATE - Use this
./deploy.sh
```

## Monitoring

- CloudWatch Logs: `/ecs/trading-agent`
- ECS Console: Check task status and service health
- CloudWatch Metrics: Monitor CPU, memory, and network usage

## Required IAM Permissions

The AWS user needs the following permissions:
- `ecr:GetAuthorizationToken`
- `ecr:BatchCheckLayerAvailability`
- `ecr:GetDownloadUrlForLayer`
- `ecr:BatchGetImage`
- `logs:CreateLogStream`
- `logs:PutLogEvents`
- `ecs:RegisterTaskDefinition`
- `ecs:UpdateService`
- `ecs:CreateService`
- `ecs:DescribeServices`
- `ecs:ListTasks`
- `ecs:DescribeTasks`
- `cloudformation:*` (if using CloudFormation)

## Notes

- The deployment uses Fargate (serverless) for cost efficiency
- CloudWatch logs are used for monitoring and debugging
- The service is configured to run in the specified VPC and subnets
- Security groups should allow necessary outbound traffic
- CloudFormation template can be used to recreate the entire infrastructure 

# Check the status of your service
aws ecs describe-services \
  --cluster trading-agent-cluster \
  --services trading-agent-service

# Check the logs
aws logs get-log-events \
  --log-group-name /ecs/trading-agent \
  --log-stream-name ecs/trading-agent/your-task-id 