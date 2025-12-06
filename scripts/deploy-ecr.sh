#!/bin/bash
# AWS ECR Deployment Script
# Pushes Docker images to AWS Elastic Container Registry

set -e

# Configuration
REGION="${AWS_REGION:-us-east-1}"
PROJECT_NAME="study-planning"

echo "=========================================="
echo "Pushing Images to AWS ECR"
echo "=========================================="
echo ""

# Get AWS account ID
echo "Getting AWS account ID..."
AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
ECR_REGISTRY="${AWS_ACCOUNT_ID}.dkr.ecr.${REGION}.amazonaws.com"

echo "AWS Account: $AWS_ACCOUNT_ID"
echo "ECR Registry: $ECR_REGISTRY"
echo "Region: $REGION"
echo ""

# Create ECR repositories if they don't exist
echo "Creating ECR repositories (if they don't exist)..."
for repo in frontend api mongodb ollama; do
    aws ecr describe-repositories --repository-names ${PROJECT_NAME}/${repo} --region $REGION 2>/dev/null || \
    aws ecr create-repository --repository-name ${PROJECT_NAME}/${repo} --region $REGION
done

echo ""
echo "Logging into ECR..."
aws ecr get-login-password --region $REGION | docker login --username AWS --password-stdin $ECR_REGISTRY

echo ""
echo "Building Docker images..."
docker compose -f docker-compose.prod.yml build

echo ""
echo "Tagging images for ECR..."
docker tag study-planning-frontend:latest $ECR_REGISTRY/${PROJECT_NAME}/frontend:latest
docker tag study-planning-api:latest $ECR_REGISTRY/${PROJECT_NAME}/api:latest
docker tag mongo:7.0 $ECR_REGISTRY/${PROJECT_NAME}/mongodb:latest
docker tag ollama/ollama:latest $ECR_REGISTRY/${PROJECT_NAME}/ollama:latest

echo ""
echo "Pushing images to ECR..."
echo "  - Pushing frontend..."
docker push $ECR_REGISTRY/${PROJECT_NAME}/frontend:latest

echo "  - Pushing api..."
docker push $ECR_REGISTRY/${PROJECT_NAME}/api:latest

echo "  - Pushing mongodb..."
docker push $ECR_REGISTRY/${PROJECT_NAME}/mongodb:latest

echo "  - Pushing ollama..."
docker push $ECR_REGISTRY/${PROJECT_NAME}/ollama:latest

echo ""
echo "=========================================="
echo "Images Pushed Successfully!"
echo "=========================================="
echo ""
echo "Image URIs:"
echo "  Frontend: $ECR_REGISTRY/${PROJECT_NAME}/frontend:latest"
echo "  API:      $ECR_REGISTRY/${PROJECT_NAME}/api:latest"
echo "  MongoDB:  $ECR_REGISTRY/${PROJECT_NAME}/mongodb:latest"
echo "  Ollama:   $ECR_REGISTRY/${PROJECT_NAME}/ollama:latest"
echo ""
echo "You can now use these images in ECS, Lightsail, or other AWS services."
echo ""
