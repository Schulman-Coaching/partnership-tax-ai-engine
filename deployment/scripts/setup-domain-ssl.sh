#!/bin/bash
# Partnership Tax Logic Engine - Domain and SSL Setup Script

set -e

# Configuration
REGION="us-west-2"
DOMAIN_NAME="${DOMAIN_NAME:-partnership-tax-engine.com}"
API_SUBDOMAIN="${API_SUBDOMAIN:-api.$DOMAIN_NAME}"
APP_SUBDOMAIN="${APP_SUBDOMAIN:-app.$DOMAIN_NAME}"

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

# Check if domain is provided
check_domain() {
    if [[ -z "$DOMAIN_NAME" ]]; then
        log_error "DOMAIN_NAME environment variable is required."
        log_info "Usage: DOMAIN_NAME=yourdomain.com ./setup-domain-ssl.sh"
        exit 1
    fi
    
    log_info "Setting up domain: $DOMAIN_NAME"
    log_info "API subdomain: $API_SUBDOMAIN"
    log_info "App subdomain: $APP_SUBDOMAIN"
}

# Create or get hosted zone
setup_hosted_zone() {
    log_info "Setting up Route 53 hosted zone..."
    
    # Check if hosted zone already exists
    HOSTED_ZONE_ID=$(aws route53 list-hosted-zones-by-name --dns-name "$DOMAIN_NAME" --query "HostedZones[?Name=='$DOMAIN_NAME.'].Id" --output text | cut -d'/' -f3)
    
    if [[ -n "$HOSTED_ZONE_ID" && "$HOSTED_ZONE_ID" != "None" ]]; then
        log_success "Hosted zone already exists: $HOSTED_ZONE_ID"
    else
        log_info "Creating hosted zone for $DOMAIN_NAME..."
        HOSTED_ZONE_ID=$(aws route53 create-hosted-zone \
            --name "$DOMAIN_NAME" \
            --caller-reference "$(date +%s)" \
            --hosted-zone-config Comment="Partnership Tax Engine hosted zone" \
            --query 'HostedZone.Id' \
            --output text | cut -d'/' -f3)
        
        log_success "Created hosted zone: $HOSTED_ZONE_ID"
    fi
    
    # Get name servers
    NAME_SERVERS=$(aws route53 get-hosted-zone --id "$HOSTED_ZONE_ID" --query 'DelegationSet.NameServers' --output table)
    
    log_info "Configure your domain registrar with these name servers:"
    echo "$NAME_SERVERS"
}

# Request SSL certificates
request_ssl_certificates() {
    log_info "Requesting SSL certificates..."
    
    # Request certificate for main domain and subdomains
    CERT_ARN=$(aws acm request-certificate \
        --domain-name "$DOMAIN_NAME" \
        --subject-alternative-names "$API_SUBDOMAIN" "$APP_SUBDOMAIN" "www.$DOMAIN_NAME" \
        --validation-method DNS \
        --region $REGION \
        --query 'CertificateArn' \
        --output text)
    
    log_success "SSL certificate requested: $CERT_ARN"
    
    # Wait for certificate validation records
    log_info "Waiting for certificate validation records..."
    sleep 10
    
    # Get validation records
    VALIDATION_RECORDS=$(aws acm describe-certificate \
        --certificate-arn "$CERT_ARN" \
        --region $REGION \
        --query 'Certificate.DomainValidationOptions[].ResourceRecord' \
        --output json)
    
    log_info "Creating DNS validation records..."
    
    # Create validation records in Route 53
    echo "$VALIDATION_RECORDS" | jq -r '.[] | @base64' | while read -r record; do
        DECODED_RECORD=$(echo "$record" | base64 --decode)
        RECORD_NAME=$(echo "$DECODED_RECORD" | jq -r '.Name')
        RECORD_VALUE=$(echo "$DECODED_RECORD" | jq -r '.Value')
        
        # Create change batch
        cat > /tmp/validation-record.json << EOF
{
    "Changes": [{
        "Action": "CREATE",
        "ResourceRecordSet": {
            "Name": "$RECORD_NAME",
            "Type": "CNAME",
            "TTL": 300,
            "ResourceRecords": [{
                "Value": "$RECORD_VALUE"
            }]
        }
    }]
}
EOF
        
        aws route53 change-resource-record-sets \
            --hosted-zone-id "$HOSTED_ZONE_ID" \
            --change-batch file:///tmp/validation-record.json > /dev/null
        
        log_success "Created validation record for $RECORD_NAME"
    done
    
    log_info "Waiting for SSL certificate validation..."
    aws acm wait certificate-validated --certificate-arn "$CERT_ARN" --region $REGION
    log_success "SSL certificate validated successfully"
}

# Create DNS records for application
create_dns_records() {
    log_info "Creating DNS records for application..."
    
    # Get load balancer DNS name
    ALB_DNS=$(aws elbv2 describe-load-balancers \
        --names partnership-tax-engine-alb \
        --query 'LoadBalancers[0].DNSName' \
        --output text \
        --region $REGION)
    
    ALB_ZONE_ID=$(aws elbv2 describe-load-balancers \
        --names partnership-tax-engine-alb \
        --query 'LoadBalancers[0].CanonicalHostedZoneId' \
        --output text \
        --region $REGION)
    
    # Create A record for main domain
    cat > /tmp/main-domain-record.json << EOF
{
    "Changes": [{
        "Action": "UPSERT",
        "ResourceRecordSet": {
            "Name": "$DOMAIN_NAME",
            "Type": "A",
            "AliasTarget": {
                "DNSName": "$ALB_DNS",
                "EvaluateTargetHealth": false,
                "HostedZoneId": "$ALB_ZONE_ID"
            }
        }
    }]
}
EOF
    
    aws route53 change-resource-record-sets \
        --hosted-zone-id "$HOSTED_ZONE_ID" \
        --change-batch file:///tmp/main-domain-record.json > /dev/null
    
    # Create A record for app subdomain
    cat > /tmp/app-domain-record.json << EOF
{
    "Changes": [{
        "Action": "UPSERT",
        "ResourceRecordSet": {
            "Name": "$APP_SUBDOMAIN",
            "Type": "A",
            "AliasTarget": {
                "DNSName": "$ALB_DNS",
                "EvaluateTargetHealth": false,
                "HostedZoneId": "$ALB_ZONE_ID"
            }
        }
    }]
}
EOF
    
    aws route53 change-resource-record-sets \
        --hosted-zone-id "$HOSTED_ZONE_ID" \
        --change-batch file:///tmp/app-domain-record.json > /dev/null
    
    # Create A record for API subdomain
    cat > /tmp/api-domain-record.json << EOF
{
    "Changes": [{
        "Action": "UPSERT",
        "ResourceRecordSet": {
            "Name": "$API_SUBDOMAIN",
            "Type": "A",
            "AliasTarget": {
                "DNSName": "$ALB_DNS",
                "EvaluateTargetHealth": false,
                "HostedZoneId": "$ALB_ZONE_ID"
            }
        }
    }]
}
EOF
    
    aws route53 change-resource-record-sets \
        --hosted-zone-id "$HOSTED_ZONE_ID" \
        --change-batch file:///tmp/api-domain-record.json > /dev/null
    
    # Create CNAME for www
    cat > /tmp/www-domain-record.json << EOF
{
    "Changes": [{
        "Action": "UPSERT",
        "ResourceRecordSet": {
            "Name": "www.$DOMAIN_NAME",
            "Type": "CNAME",
            "TTL": 300,
            "ResourceRecords": [{
                "Value": "$DOMAIN_NAME"
            }]
        }
    }]
}
EOF
    
    aws route53 change-resource-record-sets \
        --hosted-zone-id "$HOSTED_ZONE_ID" \
        --change-batch file:///tmp/www-domain-record.json > /dev/null
    
    log_success "DNS records created successfully"
}

# Update load balancer with SSL certificate
update_load_balancer_ssl() {
    log_info "Updating load balancer with SSL certificate..."
    
    # Get load balancer ARN
    ALB_ARN=$(aws elbv2 describe-load-balancers \
        --names partnership-tax-engine-alb \
        --query 'LoadBalancers[0].LoadBalancerArn' \
        --output text \
        --region $REGION)
    
    # Create HTTPS listener
    aws elbv2 create-listener \
        --load-balancer-arn "$ALB_ARN" \
        --protocol HTTPS \
        --port 443 \
        --certificates CertificateArn="$CERT_ARN" \
        --default-actions Type=forward,TargetGroupArn="$(aws elbv2 describe-target-groups --names partnership-tax-engine-frontend-tg --query 'TargetGroups[0].TargetGroupArn' --output text --region $REGION)" \
        --region $REGION > /dev/null || log_warning "HTTPS listener may already exist"
    
    # Update HTTP listener to redirect to HTTPS
    HTTP_LISTENER_ARN=$(aws elbv2 describe-listeners \
        --load-balancer-arn "$ALB_ARN" \
        --query 'Listeners[?Port==`80`].ListenerArn' \
        --output text \
        --region $REGION)
    
    if [[ -n "$HTTP_LISTENER_ARN" ]]; then
        aws elbv2 modify-listener \
            --listener-arn "$HTTP_LISTENER_ARN" \
            --default-actions Type=redirect,RedirectConfig="{Protocol=HTTPS,Port=443,StatusCode=HTTP_301}" \
            --region $REGION > /dev/null
        
        log_success "HTTP to HTTPS redirect configured"
    fi
    
    log_success "Load balancer SSL configuration completed"
}

# Test domain and SSL setup
test_setup() {
    log_info "Testing domain and SSL setup..."
    
    # Wait for DNS propagation
    log_info "Waiting for DNS propagation (this may take a few minutes)..."
    sleep 60
    
    # Test HTTPS access
    for domain in "$DOMAIN_NAME" "$APP_SUBDOMAIN" "$API_SUBDOMAIN"; do
        log_info "Testing HTTPS access for $domain..."
        
        for i in {1..5}; do
            if curl -f -s --max-time 10 "https://$domain/" > /dev/null 2>&1; then
                log_success "$domain is accessible via HTTPS"
                break
            else
                if [[ $i -eq 5 ]]; then
                    log_warning "$domain may not be accessible yet (DNS propagation can take up to 48 hours)"
                else
                    log_info "Retrying $domain in 30 seconds... ($i/5)"
                    sleep 30
                fi
            fi
        done
    done
}

# Generate setup summary
generate_summary() {
    log_info "Generating domain and SSL setup summary..."
    
    SUMMARY_FILE="/tmp/partnership-tax-engine-domain-ssl-summary.txt"
    
    cat > $SUMMARY_FILE << EOF
Partnership Tax Logic Engine - Domain and SSL Setup Summary
Generated: $(date)

DOMAIN CONFIGURATION:
- Primary Domain: $DOMAIN_NAME
- App Subdomain: $APP_SUBDOMAIN  
- API Subdomain: $API_SUBDOMAIN
- WWW Subdomain: www.$DOMAIN_NAME

ROUTE 53:
- Hosted Zone ID: $HOSTED_ZONE_ID
- Name Servers: (see output above)

SSL CERTIFICATE:
- Certificate ARN: $CERT_ARN
- Status: Validated
- Domains: $DOMAIN_NAME, $API_SUBDOMAIN, $APP_SUBDOMAIN, www.$DOMAIN_NAME

LOAD BALANCER:
- HTTPS Listener: Port 443 (SSL enabled)
- HTTP Redirect: Port 80 → 443

APPLICATION URLS:
- Frontend: https://$APP_SUBDOMAIN
- API: https://$API_SUBDOMAIN  
- Main Site: https://$DOMAIN_NAME

NEXT STEPS:
1. Verify DNS propagation (can take up to 48 hours)
2. Test all application functionality via HTTPS
3. Update application environment variables to use HTTPS URLs
4. Configure CDN (CloudFront) if needed for global performance

TROUBLESHOOTING:
- If domains are not accessible, verify name servers are configured correctly at your registrar
- DNS propagation can take 24-48 hours for full global availability
- Use 'dig $DOMAIN_NAME' or 'nslookup $DOMAIN_NAME' to check DNS resolution
EOF

    log_success "Domain and SSL setup summary generated: $SUMMARY_FILE"
    cat $SUMMARY_FILE
}

# Main setup function
main() {
    log_info "Starting Partnership Tax Logic Engine domain and SSL setup..."
    
    check_domain
    setup_hosted_zone
    request_ssl_certificates
    create_dns_records
    update_load_balancer_ssl
    test_setup
    generate_summary
    
    log_success "Domain and SSL setup completed successfully!"
    log_info "Your application will be accessible at https://$APP_SUBDOMAIN once DNS propagates."
}

# Run main function
main "$@"