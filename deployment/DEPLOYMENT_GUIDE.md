# Partnership Tax Logic Engine - Cloud Deployment Guide

## 🚀 Overview

This guide walks you through deploying the Partnership Tax Logic Engine MVP to AWS cloud infrastructure using Terraform, Docker, and GitHub Actions CI/CD.

## 📋 Prerequisites

### Required Tools
- AWS CLI v2.x
- Terraform >= 1.0
- Docker Desktop
- Git
- Node.js 18+
- Python 3.11+

### AWS Account Setup
1. **AWS Account**: Active AWS account with admin privileges
2. **AWS CLI Configuration**:
   ```bash
   aws configure
   # Enter your Access Key ID, Secret Access Key, and default region (us-west-2)
   ```

3. **Required Permissions**:
   - EC2 (VPC, Security Groups, Load Balancers)
   - ECS (Clusters, Services, Task Definitions)
   - RDS (Database instances)
   - ElastiCache (Redis clusters)
   - S3 (Buckets and objects)
   - IAM (Roles and policies)
   - CloudWatch (Logs and metrics)
   - Route 53 (DNS management)
   - Certificate Manager (SSL certificates)

## 🏗️ Infrastructure Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        Internet                              │
└─────────────────────┬───────────────────────────────────────┘
                      │
┌─────────────────────▼───────────────────────────────────────┐
│                 Route 53 DNS                                │
└─────────────────────┬───────────────────────────────────────┘
                      │
┌─────────────────────▼───────────────────────────────────────┐
│            Application Load Balancer (ALB)                  │
│                 SSL Termination                             │
└─────────────────────┬───────────────────────────────────────┘
                      │
┌─────────────────────▼───────────────────────────────────────┐
│                    ECS Fargate                              │
│  ┌─────────────────┐           ┌─────────────────────────┐  │
│  │ Frontend Tasks  │           │   Backend Tasks         │  │
│  │ (Next.js)       │           │   (FastAPI + Python)   │  │
│  └─────────────────┘           └─────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
                      │
        ┌─────────────┼─────────────┐
        │             │             │
┌───────▼────┐  ┌─────▼────┐  ┌─────▼─────┐
│ PostgreSQL │  │  Redis   │  │ S3 Bucket │
│    RDS     │  │ElastiCache│  │Documents │
└────────────┘  └──────────┘  └───────────┘
```

## 🔧 Step-by-Step Deployment

### Step 1: Environment Setup

1. **Clone Repository**:
   ```bash
   git clone <your-repo-url>
   cd partnership-tax-ai-engine
   ```

2. **Set Environment Variables**:
   ```bash
   export AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
   export AWS_REGION="us-west-2"
   ```

3. **Create S3 Bucket for Terraform State**:
   ```bash
   aws s3 mb s3://partnership-tax-engine-terraform-state-$AWS_ACCOUNT_ID --region $AWS_REGION
   aws s3api put-bucket-versioning --bucket partnership-tax-engine-terraform-state-$AWS_ACCOUNT_ID --versioning-configuration Status=Enabled
   ```

### Step 2: Infrastructure Deployment

1. **Initialize Terraform**:
   ```bash
   cd deployment/infrastructure/terraform
   terraform init
   ```

2. **Create Terraform Variables**:
   ```bash
   cat > terraform.tfvars << EOF
   aws_region = "us-west-2"
   environment = "production"
   domain_name = "app.partnership-tax-engine.com"
   api_domain_name = "api.partnership-tax-engine.com"
   EOF
   ```

3. **Plan and Apply Infrastructure**:
   ```bash
   terraform plan
   terraform apply
   ```

### Step 3: Configure Secrets

1. **Set API Keys in AWS Secrets Manager**:
   ```bash
   # OpenAI API Key
   aws secretsmanager update-secret \
     --secret-id "partnership-tax-engine/openai-api-key" \
     --secret-string '{"key":"your-openai-api-key-here"}'
   
   # Anthropic API Key (optional)
   aws secretsmanager update-secret \
     --secret-id "partnership-tax-engine/anthropic-api-key" \
     --secret-string '{"key":"your-anthropic-api-key-here"}'
   ```

### Step 4: Build and Deploy Applications

1. **Run Automated Deployment**:
   ```bash
   cd ../../..
   ./deployment/scripts/deploy.sh
   ```

   This script will:
   - Create ECR repositories
   - Build Docker images
   - Push images to ECR
   - Deploy ECS services
   - Run health checks

### Step 5: Domain and SSL Configuration

1. **Purchase Domain** (if needed):
   - Register domain through Route 53 or external provider
   - Update nameservers to Route 53 if external

2. **Create DNS Records**:
   ```bash
   # Get ALB DNS name
   ALB_DNS=$(aws elbv2 describe-load-balancers \
     --names partnership-tax-engine-alb \
     --query 'LoadBalancers[0].DNSName' \
     --output text)
   
   # Create DNS records pointing to ALB
   aws route53 change-resource-record-sets \
     --hosted-zone-id YOUR_HOSTED_ZONE_ID \
     --change-batch file://dns-records.json
   ```

3. **SSL Certificate**:
   - Certificate will be automatically created via ACM
   - DNS validation required
   - ALB will be updated to use HTTPS

### Step 6: GitHub Actions CI/CD Setup

1. **Configure Repository Secrets**:
   Go to GitHub repository → Settings → Secrets and add:
   - `AWS_ACCESS_KEY_ID`
   - `AWS_SECRET_ACCESS_KEY`
   - `AWS_ACCOUNT_ID`
   - `OPENAI_API_KEY`
   - `SLACK_WEBHOOK` (optional)

2. **Enable GitHub Actions**:
   - Push to `main` branch triggers production deployment
   - Push to `develop` branch triggers staging deployment
   - Pull requests trigger testing only

## 🔒 Security Configuration

### Network Security
- VPC with private subnets for databases
- Security groups with minimal required access
- NAT Gateway for outbound internet access from private subnets

### Data Security
- Database encryption at rest and in transit
- S3 bucket encryption and access controls
- Secrets stored in AWS Secrets Manager
- Container images scanned for vulnerabilities

### Application Security
- JWT authentication for API access
- CORS configuration for frontend security
- Rate limiting on API endpoints
- Input validation and sanitization

## 📊 Monitoring and Logging

### CloudWatch Dashboards
- ECS service metrics (CPU, memory, task count)
- ALB metrics (request count, response times, error rates)
- RDS metrics (connections, CPU, storage)
- Custom application metrics

### Log Aggregation
- Application logs centralized in CloudWatch
- Structured logging with correlation IDs
- Log retention policies configured
- Error alerting via SNS

### Health Checks
- ALB health checks for service availability
- Application-level health endpoints
- Database connectivity monitoring
- Automated rollback on health check failures

## 🚨 Troubleshooting

### Common Issues

1. **Deployment Fails**:
   ```bash
   # Check ECS service events
   aws ecs describe-services --cluster partnership-tax-engine-cluster --services partnership-tax-engine-backend
   
   # Check task logs
   aws logs get-log-events --log-group-name /ecs/partnership-tax-engine-backend --log-stream-name <stream-name>
   ```

2. **Database Connection Issues**:
   ```bash
   # Test database connectivity
   aws rds describe-db-instances --db-instance-identifier partnership-tax-engine-db
   
   # Check security group rules
   aws ec2 describe-security-groups --filters "Name=group-name,Values=partnership-tax-engine-rds-*"
   ```

3. **SSL Certificate Issues**:
   ```bash
   # Check certificate status
   aws acm list-certificates --certificate-statuses ISSUED,PENDING_VALIDATION
   
   # Check DNS validation records
   aws route53 list-resource-record-sets --hosted-zone-id YOUR_ZONE_ID
   ```

### Performance Optimization

1. **Scaling Configuration**:
   - ECS service auto-scaling based on CPU/memory
   - ALB target group health checks
   - RDS read replicas for read-heavy workloads

2. **Cost Optimization**:
   - Use Fargate Spot for non-critical workloads
   - Implement S3 lifecycle policies
   - Monitor and optimize RDS instance sizes

## 📈 Post-Deployment Tasks

### 1. Verify Deployment
- [ ] Application accessible via domain
- [ ] SSL certificate valid and working
- [ ] API endpoints responding correctly
- [ ] Database connections successful
- [ ] File uploads working (S3 integration)

### 2. Configure Monitoring Alerts
- [ ] Set up CloudWatch alarms for critical metrics
- [ ] Configure SNS notifications for alerts
- [ ] Test alert delivery and escalation

### 3. Backup and Disaster Recovery
- [ ] Verify RDS automated backups
- [ ] Test database restore procedure
- [ ] Document recovery procedures
- [ ] Set up cross-region backup if needed

### 4. Security Hardening
- [ ] Review and minimize IAM permissions
- [ ] Enable AWS Config for compliance monitoring
- [ ] Set up AWS GuardDuty for threat detection
- [ ] Configure AWS WAF rules if needed

### 5. Performance Monitoring
- [ ] Establish baseline metrics
- [ ] Set up application performance monitoring
- [ ] Configure log analysis and alerting
- [ ] Plan capacity scaling strategies

## 💰 Cost Estimation

### Monthly AWS Costs (Estimated)
- **ECS Fargate**: $150-300 (based on usage)
- **RDS PostgreSQL**: $100-200 (db.t3.medium)
- **ElastiCache Redis**: $50-100 (cache.t3.micro cluster)
- **Application Load Balancer**: $25
- **S3 Storage**: $10-50 (based on document volume)
- **CloudWatch**: $20-50 (logs and metrics)
- **Data Transfer**: $20-100 (based on traffic)

**Total Estimated Monthly Cost**: $375-925

### Cost Optimization Tips
- Use Reserved Instances for predictable workloads
- Implement auto-scaling to match demand
- Archive old documents to S3 Glacier
- Monitor and adjust resource allocation regularly

## 🔄 Maintenance and Updates

### Regular Maintenance Tasks
- **Weekly**: Review CloudWatch metrics and logs
- **Monthly**: Update dependencies and security patches
- **Quarterly**: Review and optimize costs
- **Annually**: Security audit and compliance review

### Update Procedures
1. Test updates in staging environment
2. Use rolling deployments for zero downtime
3. Monitor health checks during deployments
4. Maintain rollback procedures

## 📞 Support and Resources

### Documentation
- [AWS ECS Documentation](https://docs.aws.amazon.com/ecs/)
- [Terraform AWS Provider](https://registry.terraform.io/providers/hashicorp/aws/latest/docs)
- [Docker Best Practices](https://docs.docker.com/develop/dev-best-practices/)

### Monitoring and Alerts
- CloudWatch Dashboard: https://console.aws.amazon.com/cloudwatch/
- Application URL: https://app.partnership-tax-engine.com
- API Health: https://api.partnership-tax-engine.com/health

---

**Deployment Status**: ✅ Ready for Production  
**Last Updated**: December 2024  
**Version**: MVP 1.0