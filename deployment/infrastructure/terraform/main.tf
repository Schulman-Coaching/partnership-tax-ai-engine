# Partnership Tax Logic Engine - AWS Infrastructure
# Terraform configuration for cloud deployment

terraform {
  required_version = ">= 1.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.1"
    }
  }
  
  backend "s3" {
    bucket = "partnership-tax-engine-terraform-state-111238651930"
    key    = "infrastructure/terraform.tfstate"
    region = "us-west-2"
  }
}

provider "aws" {
  region = var.aws_region
  
  default_tags {
    tags = {
      Environment = var.environment
      Project     = "partnership-tax-engine"
      ManagedBy   = "terraform"
    }
  }
}

# Variables
variable "aws_region" {
  description = "AWS region"
  type        = string
  default     = "us-west-2"
}

variable "environment" {
  description = "Environment name"
  type        = string
  default     = "production"
}

variable "domain_name" {
  description = "Domain name for the application"
  type        = string
  default     = "app.partnership-tax-engine.com"
}

variable "api_domain_name" {
  description = "API domain name"
  type        = string
  default     = "api.partnership-tax-engine.com"
}

# Data sources
data "aws_availability_zones" "available" {
  state = "available"
}

data "aws_caller_identity" "current" {}

# Random password for RDS
resource "random_password" "db_password" {
  length  = 32
  special = true
}

# VPC and Networking
resource "aws_vpc" "main" {
  cidr_block           = "10.0.0.0/16"
  enable_dns_hostnames = true
  enable_dns_support   = true
  
  tags = {
    Name = "partnership-tax-engine-vpc"
  }
}

resource "aws_internet_gateway" "main" {
  vpc_id = aws_vpc.main.id
  
  tags = {
    Name = "partnership-tax-engine-igw"
  }
}

# Public subnets
resource "aws_subnet" "public" {
  count = 2
  
  vpc_id                  = aws_vpc.main.id
  cidr_block              = "10.0.${count.index + 1}.0/24"
  availability_zone       = data.aws_availability_zones.available.names[count.index]
  map_public_ip_on_launch = true
  
  tags = {
    Name = "partnership-tax-engine-public-${count.index + 1}"
    Type = "public"
  }
}

# Private subnets
resource "aws_subnet" "private" {
  count = 2
  
  vpc_id            = aws_vpc.main.id
  cidr_block        = "10.0.${count.index + 10}.0/24"
  availability_zone = data.aws_availability_zones.available.names[count.index]
  
  tags = {
    Name = "partnership-tax-engine-private-${count.index + 1}"
    Type = "private"
  }
}

# NAT Gateway
resource "aws_eip" "nat" {
  domain = "vpc"
  
  tags = {
    Name = "partnership-tax-engine-nat-eip"
  }
}

resource "aws_nat_gateway" "main" {
  allocation_id = aws_eip.nat.id
  subnet_id     = aws_subnet.public[0].id
  
  tags = {
    Name = "partnership-tax-engine-nat"
  }
  
  depends_on = [aws_internet_gateway.main]
}

# Route tables
resource "aws_route_table" "public" {
  vpc_id = aws_vpc.main.id
  
  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.main.id
  }
  
  tags = {
    Name = "partnership-tax-engine-public-rt"
  }
}

resource "aws_route_table" "private" {
  vpc_id = aws_vpc.main.id
  
  route {
    cidr_block     = "0.0.0.0/0"
    nat_gateway_id = aws_nat_gateway.main.id
  }
  
  tags = {
    Name = "partnership-tax-engine-private-rt"
  }
}

# Route table associations
resource "aws_route_table_association" "public" {
  count = length(aws_subnet.public)
  
  subnet_id      = aws_subnet.public[count.index].id
  route_table_id = aws_route_table.public.id
}

resource "aws_route_table_association" "private" {
  count = length(aws_subnet.private)
  
  subnet_id      = aws_subnet.private[count.index].id
  route_table_id = aws_route_table.private.id
}

# Security Groups
resource "aws_security_group" "alb" {
  name_prefix = "partnership-tax-engine-alb-"
  vpc_id      = aws_vpc.main.id
  
  ingress {
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }
  
  ingress {
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }
  
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
  
  tags = {
    Name = "partnership-tax-engine-alb-sg"
  }
}

resource "aws_security_group" "ecs" {
  name_prefix = "partnership-tax-engine-ecs-"
  vpc_id      = aws_vpc.main.id
  
  ingress {
    from_port       = 0
    to_port         = 65535
    protocol        = "tcp"
    security_groups = [aws_security_group.alb.id]
  }
  
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
  
  tags = {
    Name = "partnership-tax-engine-ecs-sg"
  }
}

resource "aws_security_group" "rds" {
  name_prefix = "partnership-tax-engine-rds-"
  vpc_id      = aws_vpc.main.id
  
  ingress {
    from_port       = 5432
    to_port         = 5432
    protocol        = "tcp"
    security_groups = [aws_security_group.ecs.id]
  }
  
  tags = {
    Name = "partnership-tax-engine-rds-sg"
  }
}

# RDS Database
resource "aws_db_subnet_group" "main" {
  name       = "partnership-tax-engine-db-subnet-group"
  subnet_ids = aws_subnet.private[*].id
  
  tags = {
    Name = "partnership-tax-engine-db-subnet-group"
  }
}

resource "aws_db_instance" "postgres" {
  identifier = "partnership-tax-engine-db"
  
  engine         = "postgres"
  engine_version = "15.14"
  instance_class = "db.t3.medium"
  
  allocated_storage     = 100
  max_allocated_storage = 1000
  storage_encrypted     = true
  
  db_name  = "partnership_tax_db"
  username = "postgres"
  password = random_password.db_password.result
  
  vpc_security_group_ids = [aws_security_group.rds.id]
  db_subnet_group_name   = aws_db_subnet_group.main.name
  
  backup_retention_period = 7
  backup_window          = "03:00-04:00"
  maintenance_window     = "sun:04:00-sun:05:00"
  
  skip_final_snapshot = false
  final_snapshot_identifier = "partnership-tax-engine-db-final-snapshot"
  
  tags = {
    Name = "partnership-tax-engine-db"
  }
}

# ECS Cluster
resource "aws_ecs_cluster" "main" {
  name = "partnership-tax-engine-cluster"
  
  setting {
    name  = "containerInsights"
    value = "enabled"
  }
  
  tags = {
    Name = "partnership-tax-engine-cluster"
  }
}

resource "aws_ecs_cluster_capacity_providers" "main" {
  cluster_name = aws_ecs_cluster.main.name
  
  capacity_providers = ["FARGATE", "FARGATE_SPOT"]
  
  default_capacity_provider_strategy {
    base              = 1
    weight            = 100
    capacity_provider = "FARGATE"
  }
}

# Application Load Balancer
resource "aws_lb" "main" {
  name               = "partnership-tax-engine-alb"
  internal           = false
  load_balancer_type = "application"
  security_groups    = [aws_security_group.alb.id]
  subnets            = aws_subnet.public[*].id
  
  enable_deletion_protection = false
  
  tags = {
    Name = "partnership-tax-engine-alb"
  }
}

# S3 Buckets
resource "aws_s3_bucket" "documents" {
  bucket = "partnership-tax-engine-documents-${random_password.db_password.id}"
  
  tags = {
    Name        = "partnership-tax-engine-documents"
    Environment = var.environment
  }
}

resource "aws_s3_bucket_versioning" "documents" {
  bucket = aws_s3_bucket.documents.id
  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "documents" {
  bucket = aws_s3_bucket.documents.id
  
  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

resource "aws_s3_bucket_public_access_block" "documents" {
  bucket = aws_s3_bucket.documents.id
  
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# ElastiCache Redis
resource "aws_elasticache_subnet_group" "main" {
  name       = "partnership-tax-engine-cache-subnet"
  subnet_ids = aws_subnet.private[*].id
}

resource "aws_security_group" "redis" {
  name_prefix = "partnership-tax-engine-redis-"
  vpc_id      = aws_vpc.main.id
  
  ingress {
    from_port       = 6379
    to_port         = 6379
    protocol        = "tcp"
    security_groups = [aws_security_group.ecs.id]
  }
  
  tags = {
    Name = "partnership-tax-engine-redis-sg"
  }
}

resource "aws_elasticache_replication_group" "redis" {
  replication_group_id       = "partnership-tax-engine-redis"
  description                = "Redis cluster for Partnership Tax Engine"
  
  node_type            = "cache.t3.micro"
  port                 = 6379
  parameter_group_name = "default.redis7"
  
  num_cache_clusters = 2
  
  subnet_group_name  = aws_elasticache_subnet_group.main.name
  security_group_ids = [aws_security_group.redis.id]
  
  at_rest_encryption_enabled = true
  transit_encryption_enabled = true
  
  tags = {
    Name = "partnership-tax-engine-redis"
  }
}

# CloudWatch Log Groups
resource "aws_cloudwatch_log_group" "backend" {
  name              = "/ecs/partnership-tax-engine-backend"
  retention_in_days = 7
  
  tags = {
    Name = "partnership-tax-engine-backend-logs"
  }
}

resource "aws_cloudwatch_log_group" "frontend" {
  name              = "/ecs/partnership-tax-engine-frontend"
  retention_in_days = 7
  
  tags = {
    Name = "partnership-tax-engine-frontend-logs"
  }
}

# IAM Roles and Policies
resource "aws_iam_role" "ecs_task_execution" {
  name = "partnership-tax-engine-ecs-task-execution"
  
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "ecs-tasks.amazonaws.com"
        }
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "ecs_task_execution" {
  role       = aws_iam_role.ecs_task_execution.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
}

resource "aws_iam_role" "ecs_task" {
  name = "partnership-tax-engine-ecs-task"
  
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "ecs-tasks.amazonaws.com"
        }
      }
    ]
  })
}

resource "aws_iam_role_policy" "ecs_task_s3" {
  name = "partnership-tax-engine-ecs-task-s3"
  role = aws_iam_role.ecs_task.id
  
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "s3:GetObject",
          "s3:PutObject",
          "s3:DeleteObject"
        ]
        Resource = "${aws_s3_bucket.documents.arn}/*"
      },
      {
        Effect = "Allow"
        Action = [
          "s3:ListBucket"
        ]
        Resource = aws_s3_bucket.documents.arn
      }
    ]
  })
}

# Secrets Manager
resource "aws_secretsmanager_secret" "database_url" {
  name        = "partnership-tax-engine/database-url"
  description = "Database connection URL for Partnership Tax Engine"
  
  tags = {
    Environment = var.environment
    Application = "partnership-tax-engine"
  }
}

resource "aws_secretsmanager_secret_version" "database_url" {
  secret_id = aws_secretsmanager_secret.database_url.id
  secret_string = jsonencode({
    url = "postgresql://${aws_db_instance.postgres.username}:${random_password.db_password.result}@${aws_db_instance.postgres.endpoint}/${aws_db_instance.postgres.db_name}"
  })
}

resource "aws_secretsmanager_secret" "redis_url" {
  name        = "partnership-tax-engine/redis-url"
  description = "Redis connection URL for Partnership Tax Engine"
  
  tags = {
    Environment = var.environment
    Application = "partnership-tax-engine"
  }
}

resource "aws_secretsmanager_secret_version" "redis_url" {
  secret_id = aws_secretsmanager_secret.redis_url.id
  secret_string = jsonencode({
    url = "redis://${aws_elasticache_replication_group.redis.primary_endpoint_address}:6379"
  })
}

resource "random_password" "app_secret_key" {
  length  = 64
  special = true
}

resource "aws_secretsmanager_secret" "app_secret_key" {
  name        = "partnership-tax-engine/secret-key"
  description = "Application secret key for Partnership Tax Engine"
  
  tags = {
    Environment = var.environment
    Application = "partnership-tax-engine"
  }
}

resource "aws_secretsmanager_secret_version" "app_secret_key" {
  secret_id = aws_secretsmanager_secret.app_secret_key.id
  secret_string = jsonencode({
    key = random_password.app_secret_key.result
  })
}

resource "aws_secretsmanager_secret" "openai_api_key" {
  name        = "partnership-tax-engine/openai-api-key"
  description = "OpenAI API key for Partnership Tax Engine"
  
  tags = {
    Environment = var.environment
    Application = "partnership-tax-engine"
  }
}

resource "aws_secretsmanager_secret" "anthropic_api_key" {
  name        = "partnership-tax-engine/anthropic-api-key"
  description = "Anthropic API key for Partnership Tax Engine"
  
  tags = {
    Environment = var.environment
    Application = "partnership-tax-engine"
  }
}

resource "random_password" "jwt_secret" {
  length  = 64
  special = true
}

resource "aws_secretsmanager_secret" "jwt_secret" {
  name        = "partnership-tax-engine/jwt-secret"
  description = "JWT signing secret for Partnership Tax Engine"
  
  tags = {
    Environment = var.environment
    Application = "partnership-tax-engine"
  }
}

resource "aws_secretsmanager_secret_version" "jwt_secret" {
  secret_id = aws_secretsmanager_secret.jwt_secret.id
  secret_string = jsonencode({
    secret = random_password.jwt_secret.result
  })
}

resource "aws_iam_role_policy" "ecs_secrets_policy" {
  name = "partnership-tax-engine-ecs-secrets"
  role = aws_iam_role.ecs_task_execution.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "secretsmanager:GetSecretValue"
        ]
        Resource = [
          aws_secretsmanager_secret.database_url.arn,
          aws_secretsmanager_secret.redis_url.arn,
          aws_secretsmanager_secret.app_secret_key.arn,
          aws_secretsmanager_secret.openai_api_key.arn,
          aws_secretsmanager_secret.anthropic_api_key.arn,
          aws_secretsmanager_secret.jwt_secret.arn
        ]
      }
    ]
  })
}

# Outputs
output "vpc_id" {
  value = aws_vpc.main.id
}

output "database_endpoint" {
  value = aws_db_instance.postgres.endpoint
}

output "database_password" {
  value     = random_password.db_password.result
  sensitive = true
}

output "redis_endpoint" {
  value = aws_elasticache_replication_group.redis.primary_endpoint_address
}

output "s3_bucket_documents" {
  value = aws_s3_bucket.documents.bucket
}

output "load_balancer_dns" {
  value = aws_lb.main.dns_name
}

output "ecs_cluster_name" {
  value = aws_ecs_cluster.main.name
}