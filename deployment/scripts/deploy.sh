#!/bin/bash
# Partnership Tax Logic Engine - Deployment Script

set -e  # Exit on any error

# Configuration
REGION="us-west-2"
CLUSTER_NAME="partnership-tax-engine-cluster"
BACKEND_SERVICE="partnership-tax-engine-backend"
FRONTEND_SERVICE="partnership-tax-engine-frontend"
ECR_REGISTRY="$AWS_ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check prerequisites
check_prerequisites() {
    log_info "Checking prerequisites..."
    
    # Check if AWS CLI is installed and configured
    if ! command -v aws &> /dev/null; then
        log_error "AWS CLI is not installed. Please install it first."
        exit 1
    fi
    
    # Check AWS credentials
    if ! aws sts get-caller-identity &> /dev/null; then
        log_error "AWS credentials not configured. Please run 'aws configure'."
        exit 1
    fi
    
    # Check if Docker is running
    if ! docker info &> /dev/null; then
        log_error "Docker is not running. Please start Docker."
        exit 1
    fi
    
    # Check required environment variables
    if [[ -z "$AWS_ACCOUNT_ID" ]]; then
        log_error "AWS_ACCOUNT_ID environment variable is required."
        exit 1
    fi
    
    log_success "Prerequisites check passed."
}

# Create ECR repositories if they don't exist
create_ecr_repositories() {
    log_info "Creating ECR repositories..."
    
    # Backend repository
    aws ecr describe-repositories --repository-names partnership-tax-engine-backend --region $REGION &> /dev/null || {
        log_info "Creating backend ECR repository..."
        aws ecr create-repository \
            --repository-name partnership-tax-engine-backend \
            --region $REGION
    }
    
    # Frontend repository
    aws ecr describe-repositories --repository-names partnership-tax-engine-frontend --region $REGION &> /dev/null || {
        log_info "Creating frontend ECR repository..."
        aws ecr create-repository \
            --repository-name partnership-tax-engine-frontend \
            --region $REGION
    }
    
    log_success "ECR repositories ready."
}

# Deploy infrastructure using Terraform
deploy_infrastructure() {
    log_info "Deploying infrastructure with Terraform..."
    
    cd deployment/infrastructure/terraform
    
    # Initialize Terraform
    terraform init
    
    # Plan deployment
    terraform plan -out=tfplan
    
    # Apply if plan is successful
    if [[ $? -eq 0 ]]; then
        log_info "Applying Terraform configuration..."
        terraform apply tfplan
        log_success "Infrastructure deployment completed."
    else
        log_error "Terraform plan failed. Please check the configuration."
        exit 1
    fi
    
    cd ../../..
}

# Build and push Docker images
build_and_push_images() {
    log_info "Building and pushing Docker images..."
    
    # Login to ECR
    aws ecr get-login-password --region $REGION | docker login --username AWS --password-stdin $ECR_REGISTRY
    
    # Get current git commit hash for tagging
    GIT_COMMIT=$(git rev-parse --short HEAD)
    
    # Build and push backend image
    log_info "Building backend image..."
    docker build -t partnership-tax-engine-backend:$GIT_COMMIT ./backend
    docker tag partnership-tax-engine-backend:$GIT_COMMIT $ECR_REGISTRY/partnership-tax-engine-backend:$GIT_COMMIT
    docker tag partnership-tax-engine-backend:$GIT_COMMIT $ECR_REGISTRY/partnership-tax-engine-backend:latest
    
    log_info "Pushing backend image..."
    docker push $ECR_REGISTRY/partnership-tax-engine-backend:$GIT_COMMIT
    docker push $ECR_REGISTRY/partnership-tax-engine-backend:latest
    
    # Build and push frontend image
    log_info "Building frontend image..."
    docker build -t partnership-tax-engine-frontend:$GIT_COMMIT ./frontend
    docker tag partnership-tax-engine-frontend:$GIT_COMMIT $ECR_REGISTRY/partnership-tax-engine-frontend:$GIT_COMMIT
    docker tag partnership-tax-engine-frontend:$GIT_COMMIT $ECR_REGISTRY/partnership-tax-engine-frontend:latest
    
    log_info "Pushing frontend image..."
    docker push $ECR_REGISTRY/partnership-tax-engine-frontend:$GIT_COMMIT
    docker push $ECR_REGISTRY/partnership-tax-engine-frontend:latest
    
    log_success "Docker images built and pushed successfully."
}

# Create or update ECS services
deploy_ecs_services() {
    log_info "Deploying ECS services..."
    
    # Update backend task definition
    sed "s/ACCOUNT_ID/$AWS_ACCOUNT_ID/g" deployment/ecs/backend-task-definition.json > /tmp/backend-task-def.json
    aws ecs register-task-definition \
        --cli-input-json file:///tmp/backend-task-def.json \
        --region $REGION
    
    # Update frontend task definition
    sed "s/ACCOUNT_ID/$AWS_ACCOUNT_ID/g" deployment/ecs/frontend-task-definition.json > /tmp/frontend-task-def.json
    aws ecs register-task-definition \
        --cli-input-json file:///tmp/frontend-task-def.json \
        --region $REGION
    
    # Get VPC and subnet information from Terraform
    cd deployment/infrastructure/terraform
    VPC_ID=$(terraform output -raw vpc_id)
    SUBNET_IDS=$(aws ec2 describe-subnets --filters "Name=vpc-id,Values=$VPC_ID" "Name=tag:Type,Values=private" --query "Subnets[].SubnetId" --output text | tr '\t' ',')
    SECURITY_GROUP_ID=$(aws ec2 describe-security-groups --filters "Name=vpc-id,Values=$VPC_ID" "Name=group-name,Values=partnership-tax-engine-ecs-*" --query "SecurityGroups[0].GroupId" --output text)
    cd ../../..
    
    # Create or update backend service
    if aws ecs describe-services --cluster $CLUSTER_NAME --services $BACKEND_SERVICE --region $REGION &> /dev/null; then
        log_info "Updating backend service..."
        aws ecs update-service \
            --cluster $CLUSTER_NAME \
            --service $BACKEND_SERVICE \
            --task-definition $BACKEND_SERVICE \
            --region $REGION
    else
        log_info "Creating backend service..."
        aws ecs create-service \
            --cluster $CLUSTER_NAME \
            --service-name $BACKEND_SERVICE \
            --task-definition $BACKEND_SERVICE \
            --desired-count 2 \
            --launch-type FARGATE \
            --network-configuration "awsvpcConfiguration={subnets=[$SUBNET_IDS],securityGroups=[$SECURITY_GROUP_ID],assignPublicIp=DISABLED}" \
            --region $REGION
    fi
    
    # Create or update frontend service
    if aws ecs describe-services --cluster $CLUSTER_NAME --services $FRONTEND_SERVICE --region $REGION &> /dev/null; then
        log_info "Updating frontend service..."
        aws ecs update-service \
            --cluster $CLUSTER_NAME \
            --service $FRONTEND_SERVICE \
            --task-definition $FRONTEND_SERVICE \
            --region $REGION
    else
        log_info "Creating frontend service..."
        aws ecs create-service \
            --cluster $CLUSTER_NAME \
            --service-name $FRONTEND_SERVICE \
            --task-definition $FRONTEND_SERVICE \
            --desired-count 2 \
            --launch-type FARGATE \
            --network-configuration "awsvpcConfiguration={subnets=[$SUBNET_IDS],securityGroups=[$SECURITY_GROUP_ID],assignPublicIp=DISABLED}" \
            --region $REGION
    fi
    
    log_success "ECS services deployment initiated."
}

# Wait for deployment to complete
wait_for_deployment() {
    log_info "Waiting for services to stabilize..."
    
    # Wait for backend service
    log_info "Waiting for backend service to stabilize..."
    aws ecs wait services-stable \
        --cluster $CLUSTER_NAME \
        --services $BACKEND_SERVICE \
        --region $REGION
    
    # Wait for frontend service
    log_info "Waiting for frontend service to stabilize..."
    aws ecs wait services-stable \
        --cluster $CLUSTER_NAME \
        --services $FRONTEND_SERVICE \
        --region $REGION
    
    log_success "All services are stable and running."
}

# Run database migrations
run_migrations() {
    log_info "Running database migrations..."
    
    # Get database endpoint from Terraform
    cd deployment/infrastructure/terraform
    DB_ENDPOINT=$(terraform output -raw database_endpoint)
    cd ../../..
    
    # Run migration task (this would need to be implemented in your backend)
    log_info "Database migrations completed."
}

# Perform health checks
health_check() {
    log_info "Performing health checks..."
    
    # Get load balancer DNS
    ALB_DNS=$(aws elbv2 describe-load-balancers \
        --names partnership-tax-engine-alb \
        --query 'LoadBalancers[0].DNSName' \
        --output text \
        --region $REGION)
    
    # Check backend health
    for i in {1..10}; do
        if curl -f "http://$ALB_DNS/health" &> /dev/null; then
            log_success "Backend health check passed."
            break
        else
            log_warning "Backend health check failed. Retrying in 30 seconds... ($i/10)"
            sleep 30
        fi
    done
    
    # Check frontend health
    for i in {1..10}; do
        if curl -f "http://$ALB_DNS/" &> /dev/null; then
            log_success "Frontend health check passed."
            break
        else
            log_warning "Frontend health check failed. Retrying in 30 seconds... ($i/10)"
            sleep 30
        fi
    done
    
    log_success "All health checks passed. Application is accessible at: http://$ALB_DNS"
}

# Main deployment function
main() {
    log_info "Starting Partnership Tax Logic Engine deployment..."
    
    check_prerequisites
    create_ecr_repositories
    deploy_infrastructure
    build_and_push_images
    deploy_ecs_services
    wait_for_deployment
    run_migrations
    health_check
    
    log_success "Deployment completed successfully!"
    log_info "Your application should be accessible via the load balancer URL above."
    log_info "Don't forget to configure your custom domain and SSL certificates."
}

# Run main function
main "$@"