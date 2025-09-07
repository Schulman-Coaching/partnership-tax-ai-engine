#!/bin/bash
# Monitor Partnership Tax Logic Engine Deployment

echo "🔍 Monitoring Partnership Tax Logic Engine Deployment..."
echo "=================================================="

# Check ECS Services
echo "📋 ECS Services Status:"
aws ecs list-services --cluster partnership-tax-engine-cluster --region us-west-2 --query 'serviceArns' --output text
if [ $? -eq 0 ]; then
    aws ecs describe-services --cluster partnership-tax-engine-cluster --services partnership-tax-engine-backend partnership-tax-engine-frontend --region us-west-2 --query 'services[*].{Service:serviceName,Status:status,Running:runningCount,Desired:desiredCount}' --output table 2>/dev/null || echo "Services not created yet"
fi

echo ""
echo "🐳 Docker Images in ECR:"
echo "Backend images:"
aws ecr describe-images --repository-name partnership-tax-engine-backend --region us-west-2 --query 'imageDetails[*].{Tags:imageTags,Size:imageSizeInBytes,Pushed:imagePushedAt}' --output table 2>/dev/null || echo "No backend images found yet"

echo ""
echo "Frontend images:"
aws ecr describe-images --repository-name partnership-tax-engine-frontend --region us-west-2 --query 'imageDetails[*].{Tags:imageTags,Size:imageSizeInBytes,Pushed:imagePushedAt}' --output table 2>/dev/null || echo "No frontend images found yet"

echo ""
echo "🌐 Application Health Check:"
HEALTH_STATUS=$(curl -s -o /dev/null -w "%{http_code}" http://partnership-tax-engine-alb-281971340.us-west-2.elb.amazonaws.com/health 2>/dev/null)
if [ "$HEALTH_STATUS" = "200" ]; then
    echo "✅ Application is LIVE and healthy!"
    echo "🔗 Frontend: http://partnership-tax-engine-alb-281971340.us-west-2.elb.amazonaws.com"
    echo "🔗 API Docs: http://partnership-tax-engine-alb-281971340.us-west-2.elb.amazonaws.com/docs"
elif [ "$HEALTH_STATUS" = "000" ]; then
    echo "⏳ Application not yet available (still deploying)"
else
    echo "⚠️  Application returned HTTP $HEALTH_STATUS"
fi

echo ""
echo "📊 GitHub Actions: https://github.com/Schulman-Coaching/partnership-tax-ai-engine/actions"
echo "🔧 AWS Console: https://console.aws.amazon.com/ecs/v2/clusters/partnership-tax-engine-cluster/services"