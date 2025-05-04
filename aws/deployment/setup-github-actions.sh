#!/bin/bash

# Create the IAM role policy
aws iam create-policy \
    --policy-name GitHubActionsPolicy \
    --policy-document file://github-actions-role.json

# Create the trust policy for GitHub Actions
cat > trust-policy.json << EOF
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Principal": {
                "Federated": "arn:aws:iam::$(aws sts get-caller-identity --query Account --output text):oidc-provider/token.actions.githubusercontent.com"
            },
            "Action": "sts:AssumeRoleWithWebIdentity",
            "Condition": {
                "StringLike": {
                    "token.actions.githubusercontent.com:sub": "repo:yetigong/trading-agent:*"
                }
            }
        }
    ]
}
EOF

# Create the IAM role
aws iam create-role \
    --role-name GitHubActionsRole \
    --assume-role-policy-document file://trust-policy.json

# Attach the policy to the role
aws iam attach-role-policy \
    --role-name GitHubActionsRole \
    --policy-arn arn:aws:iam::$(aws sts get-caller-identity --query Account --output text):policy/GitHubActionsPolicy

# Get the role ARN
ROLE_ARN=$(aws iam get-role --role-name GitHubActionsRole --query 'Role.Arn' --output text)
echo "Role ARN: $ROLE_ARN"
echo "Add this ARN as AWS_ROLE_ARN in your GitHub repository secrets" 