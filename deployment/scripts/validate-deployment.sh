#!/bin/bash
# Partnership Tax Logic Engine - Deployment Validation Script

set -e

# Configuration
REGION="us-west-2"
CLUSTER_NAME="partnership-tax-engine-cluster"
BACKEND_SERVICE="partnership-tax-engine-backend"
FRONTEND_SERVICE="partnership-tax-engine-frontend"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

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

# Validate AWS Infrastructure
validate_infrastructure() {
    log_info "Validating AWS infrastructure..."
    
    # Check VPC
    VPC_ID=$(aws ec2 describe-vpcs --filters "Name=tag:Name,Values=partnership-tax-engine-vpc" --query 'Vpcs[0].VpcId' --output text --region $REGION)
    if [[ "$VPC_ID" != "null" && "$VPC_ID" != "" ]]; then
        log_success "VPC exists: $VPC_ID"
    else
        log_error "VPC not found"
        exit 1
    fi
    
    # Check RDS instance
    DB_STATUS=$(aws rds describe-db-instances --db-instance-identifier partnership-tax-engine-db --query 'DBInstances[0].DBInstanceStatus' --output text --region $REGION 2>/dev/null || echo "not-found")
    if [[ "$DB_STATUS" == "available" ]]; then
        log_success "Database is available"
    else
        log_error "Database not available. Status: $DB_STATUS"
        exit 1
    fi
    
    # Check ElastiCache
    REDIS_STATUS=$(aws elasticache describe-replication-groups --replication-group-id partnership-tax-engine-redis --query 'ReplicationGroups[0].Status' --output text --region $REGION 2>/dev/null || echo "not-found")
    if [[ "$REDIS_STATUS" == "available" ]]; then
        log_success "Redis cluster is available"
    else
        log_error "Redis cluster not available. Status: $REDIS_STATUS"
        exit 1
    fi
    
    # Check Load Balancer
    ALB_STATE=$(aws elbv2 describe-load-balancers --names partnership-tax-engine-alb --query 'LoadBalancers[0].State.Code' --output text --region $REGION 2>/dev/null || echo "not-found")
    if [[ "$ALB_STATE" == "active" ]]; then
        log_success "Application Load Balancer is active"
    else
        log_error "Load Balancer not active. State: $ALB_STATE"
        exit 1
    fi
}

# Validate ECS Services
validate_ecs_services() {
    log_info "Validating ECS services..."
    
    # Check ECS Cluster
    CLUSTER_STATUS=$(aws ecs describe-clusters --clusters $CLUSTER_NAME --query 'clusters[0].status' --output text --region $REGION)
    if [[ "$CLUSTER_STATUS" == "ACTIVE" ]]; then
        log_success "ECS Cluster is active"
    else
        log_error "ECS Cluster not active. Status: $CLUSTER_STATUS"
        exit 1
    fi
    
    # Check Backend Service
    BACKEND_STATUS=$(aws ecs describe-services --cluster $CLUSTER_NAME --services $BACKEND_SERVICE --query 'services[0].status' --output text --region $REGION)
    BACKEND_RUNNING=$(aws ecs describe-services --cluster $CLUSTER_NAME --services $BACKEND_SERVICE --query 'services[0].runningCount' --output text --region $REGION)
    BACKEND_DESIRED=$(aws ecs describe-services --cluster $CLUSTER_NAME --services $BACKEND_SERVICE --query 'services[0].desiredCount' --output text --region $REGION)
    
    if [[ "$BACKEND_STATUS" == "ACTIVE" && "$BACKEND_RUNNING" -eq "$BACKEND_DESIRED" ]]; then
        log_success "Backend service is running ($BACKEND_RUNNING/$BACKEND_DESIRED tasks)"
    else
        log_error "Backend service issues. Status: $BACKEND_STATUS, Running: $BACKEND_RUNNING, Desired: $BACKEND_DESIRED"
        exit 1
    fi
    
    # Check Frontend Service
    FRONTEND_STATUS=$(aws ecs describe-services --cluster $CLUSTER_NAME --services $FRONTEND_SERVICE --query 'services[0].status' --output text --region $REGION)
    FRONTEND_RUNNING=$(aws ecs describe-services --cluster $CLUSTER_NAME --services $FRONTEND_SERVICE --query 'services[0].runningCount' --output text --region $REGION)
    FRONTEND_DESIRED=$(aws ecs describe-services --cluster $CLUSTER_NAME --services $FRONTEND_SERVICE --query 'services[0].desiredCount' --output text --region $REGION)
    
    if [[ "$FRONTEND_STATUS" == "ACTIVE" && "$FRONTEND_RUNNING" -eq "$FRONTEND_DESIRED" ]]; then
        log_success "Frontend service is running ($FRONTEND_RUNNING/$FRONTEND_DESIRED tasks)"
    else
        log_error "Frontend service issues. Status: $FRONTEND_STATUS, Running: $FRONTEND_RUNNING, Desired: $FRONTEND_DESIRED"
        exit 1
    fi
}

# Validate Application Health
validate_application_health() {
    log_info "Validating application health..."
    
    # Get Load Balancer DNS
    ALB_DNS=$(aws elbv2 describe-load-balancers --names partnership-tax-engine-alb --query 'LoadBalancers[0].DNSName' --output text --region $REGION)
    
    # Test Backend Health Endpoint
    log_info "Testing backend health endpoint..."
    for i in {1..5}; do
        if curl -f -s "http://$ALB_DNS/health" > /dev/null; then
            HEALTH_RESPONSE=$(curl -s "http://$ALB_DNS/health")
            log_success "Backend health check passed: $HEALTH_RESPONSE"
            break
        else
            if [[ $i -eq 5 ]]; then
                log_error "Backend health check failed after 5 attempts"
                exit 1
            else
                log_warning "Backend health check failed. Retrying in 10 seconds... ($i/5)"
                sleep 10
            fi
        fi
    done
    
    # Test Frontend
    log_info "Testing frontend availability..."
    for i in {1..5}; do
        if curl -f -s "http://$ALB_DNS/" > /dev/null; then
            log_success "Frontend is accessible"
            break
        else
            if [[ $i -eq 5 ]]; then
                log_error "Frontend accessibility test failed after 5 attempts"
                exit 1
            else
                log_warning "Frontend test failed. Retrying in 10 seconds... ($i/5)"
                sleep 10
            fi
        fi
    done
    
    # Test API Endpoints
    log_info "Testing core API endpoints..."
    
    # Test partnerships endpoint
    if curl -f -s "http://$ALB_DNS/api/partnerships" > /dev/null; then
        log_success "Partnerships API endpoint is accessible"
    else
        log_warning "Partnerships API endpoint may not be accessible"
    fi
    
    # Test documents endpoint  
    if curl -f -s "http://$ALB_DNS/api/documents" > /dev/null; then
        log_success "Documents API endpoint is accessible"
    else
        log_warning "Documents API endpoint may not be accessible"
    fi
}

# Validate Security Configuration
validate_security() {
    log_info "Validating security configuration..."
    
    # Check Secrets Manager
    SECRETS=$(aws secretsmanager list-secrets --query 'SecretList[?contains(Name, `partnership-tax-engine`)].Name' --output text --region $REGION)
    SECRET_COUNT=$(echo "$SECRETS" | wc -w)
    
    if [[ $SECRET_COUNT -ge 5 ]]; then
        log_success "Required secrets are configured ($SECRET_COUNT secrets found)"
    else
        log_warning "Some secrets may be missing. Found $SECRET_COUNT secrets"
    fi
    
    # Check security groups
    SG_COUNT=$(aws ec2 describe-security-groups --filters "Name=tag:Application,Values=partnership-tax-engine" --query 'length(SecurityGroups)' --output text --region $REGION)
    
    if [[ $SG_COUNT -gt 0 ]]; then
        log_success "Security groups are configured ($SG_COUNT groups)"
    else
        log_error "No security groups found"
        exit 1
    fi
}

# Validate Monitoring
validate_monitoring() {
    log_info "Validating monitoring configuration..."
    
    # Check CloudWatch Log Groups
    LOG_GROUPS=$(aws logs describe-log-groups --log-group-name-prefix "/ecs/partnership-tax-engine" --query 'length(logGroups)' --output text --region $REGION)
    
    if [[ $LOG_GROUPS -gt 0 ]]; then
        log_success "CloudWatch log groups are configured ($LOG_GROUPS groups)"
    else
        log_warning "CloudWatch log groups may not be configured"
    fi
    
    # Check if dashboard exists (this would need to be implemented)
    log_info "CloudWatch dashboard should be manually verified"
}

# Generate deployment report
generate_report() {
    log_info "Generating deployment validation report..."
    
    REPORT_FILE="/tmp/partnership-tax-engine-validation-report.txt"
    
    cat > $REPORT_FILE << EOF
Partnership Tax Logic Engine - Deployment Validation Report
Generated: $(date)
Region: $REGION

INFRASTRUCTURE STATUS:
- VPC: $VPC_ID
- Database: $DB_STATUS
- Redis: $REDIS_STATUS
- Load Balancer: $ALB_STATE

ECS SERVICES:
- Cluster: $CLUSTER_STATUS
- Backend Service: $BACKEND_STATUS ($BACKEND_RUNNING/$BACKEND_DESIRED tasks)
- Frontend Service: $FRONTEND_STATUS ($FRONTEND_RUNNING/$FRONTEND_DESIRED tasks)

APPLICATION ACCESS:
- Load Balancer DNS: $ALB_DNS
- Application URL: http://$ALB_DNS
- API Health: http://$ALB_DNS/health

SECURITY:
- Secrets configured: $SECRET_COUNT
- Security groups: $SG_COUNT

MONITORING:
- Log groups: $LOG_GROUPS

NEXT STEPS:
1. Configure custom domain and SSL certificate
2. Set up CloudWatch alarms
3. Perform load testing
4. Configure backup procedures
EOF

    log_success "Validation report generated: $REPORT_FILE"
    cat $REPORT_FILE
}

# Main validation function
main() {
    log_info "Starting Partnership Tax Logic Engine deployment validation..."
    
    validate_infrastructure
    validate_ecs_services
    validate_application_health
    validate_security
    validate_monitoring
    generate_report
    
    log_success "Deployment validation completed successfully!"
    log_info "Application is ready for production use."
}

# Run main function
main "$@"