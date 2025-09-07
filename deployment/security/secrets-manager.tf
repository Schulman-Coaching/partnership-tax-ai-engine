# AWS Secrets Manager configuration for secure credential storage

# Database connection string
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

# Redis connection string
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

# Application secret key
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

# OpenAI API Key (to be set manually)
resource "aws_secretsmanager_secret" "openai_api_key" {
  name        = "partnership-tax-engine/openai-api-key"
  description = "OpenAI API key for Partnership Tax Engine"
  
  tags = {
    Environment = var.environment
    Application = "partnership-tax-engine"
  }
}

# Anthropic API Key (to be set manually)
resource "aws_secretsmanager_secret" "anthropic_api_key" {
  name        = "partnership-tax-engine/anthropic-api-key"
  description = "Anthropic API key for Partnership Tax Engine"
  
  tags = {
    Environment = var.environment
    Application = "partnership-tax-engine"
  }
}

# JWT signing keys
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

# IAM policy for ECS tasks to access secrets
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