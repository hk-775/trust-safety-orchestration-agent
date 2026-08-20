#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

export AWS_PAGER=""
export SAM_CLI_TELEMETRY=0

ENVIRONMENT="${ENVIRONMENT:-dev}"
AWS_REGION="${AWS_REGION:-${AWS_DEFAULT_REGION:-us-east-1}}"
STACK_NAME="${STACK_NAME:-trust-safety-orch-${ENVIRONMENT}}"
DEPLOY_FRONTEND="${DEPLOY_FRONTEND:-true}"
SEED_DEMO_DATA="${SEED_DEMO_DATA:-false}"
CONFIRM_PRODUCTION_DEPLOY="${CONFIRM_PRODUCTION_DEPLOY:-false}"

if [[ -z "${USE_REDIS:-}" ]]; then
    if [[ "$ENVIRONMENT" == "prod" || "$ENVIRONMENT" == "prodtest" ]]; then
        USE_REDIS="true"
    else
        USE_REDIS="false"
    fi
fi

normalize_bool() {
    local name="$1"
    local value="$2"

    case "$value" in
        true|TRUE|True|1|yes|YES|Yes)
            printf 'true'
            ;;
        false|FALSE|False|0|no|NO|No)
            printf 'false'
            ;;
        *)
            echo "ERROR: ${name} must be true or false (received: ${value})." >&2
            return 1
            ;;
    esac
}

USE_REDIS="$(normalize_bool USE_REDIS "$USE_REDIS")"
DEPLOY_FRONTEND="$(normalize_bool DEPLOY_FRONTEND "$DEPLOY_FRONTEND")"
SEED_DEMO_DATA="$(normalize_bool SEED_DEMO_DATA "$SEED_DEMO_DATA")"
CONFIRM_PRODUCTION_DEPLOY="$(
    normalize_bool CONFIRM_PRODUCTION_DEPLOY "$CONFIRM_PRODUCTION_DEPLOY"
)"

case "$ENVIRONMENT" in
    dev|staging|prodtest|prod) ;;
    *)
        echo "ERROR: ENVIRONMENT must be dev, staging, prodtest, or prod." >&2
        exit 1
        ;;
esac

if [[ "$ENVIRONMENT" == "prod" ]]; then
    echo "ERROR: Direct production deployment is disabled in this sample." >&2
    echo "Use prodtest for topology validation and complete the production release gaps first." >&2
    exit 1
fi

for command_name in aws sam curl; do
    if ! command -v "$command_name" >/dev/null 2>&1; then
        echo "ERROR: Required command not found: ${command_name}" >&2
        exit 1
    fi
done

if [[ "$DEPLOY_FRONTEND" == "true" ]]; then
    for command_name in node npm; do
        if ! command -v "$command_name" >/dev/null 2>&1; then
            echo "ERROR: Required frontend command not found: ${command_name}" >&2
            exit 1
        fi
    done

    if ! node -e '
        const [major, minor] = process.versions.node.split(".").map(Number);
        const supported = major === 20 ? minor >= 19 : major === 22 ? minor >= 12 : major > 22;
        process.exit(supported ? 0 : 1);
    '; then
        echo "ERROR: Frontend deployment requires Node.js 20.19+, 22.12+, or a newer major release." >&2
        exit 1
    fi
fi

if [[ "$SEED_DEMO_DATA" == "true" ]] && ! command -v uv >/dev/null 2>&1; then
    echo "ERROR: uv is required when SEED_DEMO_DATA=true." >&2
    exit 1
fi

if [[ "$SEED_DEMO_DATA" == "true" && -z "${DEMO_ADMIN_PASSWORD:-}" ]]; then
    echo "ERROR: DEMO_ADMIN_PASSWORD is required when SEED_DEMO_DATA=true." >&2
    exit 1
fi

if [[ "$ENVIRONMENT" == "prodtest" ]]; then
    if [[ "$CONFIRM_PRODUCTION_DEPLOY" != "true" ]]; then
        echo "ERROR: Set CONFIRM_PRODUCTION_DEPLOY=true for a production-like deployment." >&2
        exit 1
    fi
    if [[ "$USE_REDIS" != "true" ]]; then
        echo "ERROR: Production-like deployments require USE_REDIS=true." >&2
        exit 1
    fi
    if [[ "$SEED_DEMO_DATA" == "true" ]]; then
        echo "ERROR: Demo data seeding is disabled for production-like deployments." >&2
        exit 1
    fi
fi

PLATFORM_USER_API_URL="${PLATFORM_USER_API_URL:-}"
PLATFORM_MESSAGING_API_URL="${PLATFORM_MESSAGING_API_URL:-}"
PARTNER_INTEL_API_URL="${PARTNER_INTEL_API_URL:-}"
BEDROCK_MODEL_ID="${BEDROCK_MODEL_ID:-}"
ALLOWED_CORS_ORIGIN="${ALLOWED_CORS_ORIGIN:-http://localhost:3000}"

if [[ "$ENVIRONMENT" == "prodtest" ]]; then
    if [[ -z "$BEDROCK_MODEL_ID" ]]; then
        echo "ERROR: BEDROCK_MODEL_ID must be set for a production-like deployment." >&2
        exit 1
    fi
fi

echo "Deploying stack"
echo "  Environment: ${ENVIRONMENT}"
echo "  Stack:       ${STACK_NAME}"
echo "  Region:      ${AWS_REGION}"
echo "  Redis:       ${USE_REDIS}"
echo "  Frontend:    ${DEPLOY_FRONTEND}"

aws sts get-caller-identity --region "$AWS_REGION" >/dev/null

parameter_overrides=(
    "Environment=${ENVIRONMENT}"
    "UseRedis=${USE_REDIS}"
    "AllowedCorsOrigin=${ALLOWED_CORS_ORIGIN}"
)

if [[ -n "$PLATFORM_USER_API_URL" ]]; then
    parameter_overrides+=("PlatformUserApiUrl=${PLATFORM_USER_API_URL}")
fi
if [[ -n "$PLATFORM_MESSAGING_API_URL" ]]; then
    parameter_overrides+=("PlatformMessagingApiUrl=${PLATFORM_MESSAGING_API_URL}")
fi
if [[ -n "$PARTNER_INTEL_API_URL" ]]; then
    parameter_overrides+=("PartnerIntelApiUrl=${PARTNER_INTEL_API_URL}")
fi
if [[ -n "$BEDROCK_MODEL_ID" ]]; then
    parameter_overrides+=("BedrockModelId=${BEDROCK_MODEL_ID}")
fi

if [[ -n "${VPC_CIDR:-}" ]]; then
    parameter_overrides+=("VpcCidr=${VPC_CIDR}")
fi
if [[ -n "${PRIVATE_SUBNET_1_CIDR:-}" ]]; then
    parameter_overrides+=("PrivateSubnet1Cidr=${PRIVATE_SUBNET_1_CIDR}")
fi
if [[ -n "${PRIVATE_SUBNET_2_CIDR:-}" ]]; then
    parameter_overrides+=("PrivateSubnet2Cidr=${PRIVATE_SUBNET_2_CIDR}")
fi
if [[ -n "${PUBLIC_SUBNET_1_CIDR:-}" ]]; then
    parameter_overrides+=("PublicSubnet1Cidr=${PUBLIC_SUBNET_1_CIDR}")
fi
if [[ -n "${PUBLIC_SUBNET_2_CIDR:-}" ]]; then
    parameter_overrides+=("PublicSubnet2Cidr=${PUBLIC_SUBNET_2_CIDR}")
fi
if [[ -n "${REDIS_NODE_TYPE:-}" ]]; then
    parameter_overrides+=("RedisNodeType=${REDIS_NODE_TYPE}")
fi

sam build --parallel
sam deploy \
    --stack-name "$STACK_NAME" \
    --region "$AWS_REGION" \
    --resolve-s3 \
    --capabilities CAPABILITY_IAM CAPABILITY_AUTO_EXPAND \
    --no-confirm-changeset \
    --no-fail-on-empty-changeset \
    --parameter-overrides "${parameter_overrides[@]}" \
    --tags \
        "Project=TrustSafetyOrchestration" \
        "Team=TrustAndSafety" \
        "Environment=${ENVIRONMENT}"

stack_output() {
    local output_key="$1"
    local output_value

    output_value="$(
        aws cloudformation describe-stacks \
            --stack-name "$STACK_NAME" \
            --region "$AWS_REGION" \
            --query "Stacks[0].Outputs[?OutputKey=='${output_key}'].OutputValue | [0]" \
            --output text
    )"

    if [[ -z "$output_value" || "$output_value" == "None" ]]; then
        echo "ERROR: Stack output ${output_key} is missing." >&2
        exit 1
    fi

    printf '%s' "$output_value"
}

REST_API_URL="$(stack_output RestApiUrl)"
WEBSOCKET_URL="$(stack_output WebSocketUrl)"
FRONTEND_BUCKET="$(stack_output FrontendBucketName)"
CLOUDFRONT_DISTRIBUTION_ID="$(stack_output CloudFrontDistributionId)"
CLOUDFRONT_DOMAIN="$(stack_output CloudFrontDomainName)"

printf 'VITE_API_BASE_URL=%s/api/v1\nVITE_WS_URL=%s\n' \
    "$REST_API_URL" \
    "$WEBSOCKET_URL" \
    > frontend/.env.local

HEALTH_URL="${REST_API_URL}/api/v1/health"
health_ready="false"
for attempt in 1 2 3 4 5 6 7 8 9 10 11 12; do
    if curl --fail --silent --show-error "$HEALTH_URL" >/dev/null; then
        health_ready="true"
        break
    fi
    echo "Waiting for API health check (${attempt}/12)..."
    sleep 5
done

if [[ "$health_ready" != "true" ]]; then
    echo "ERROR: API health check did not become ready: ${HEALTH_URL}" >&2
    exit 1
fi

if [[ "$SEED_DEMO_DATA" == "true" ]]; then
    uv run python scripts/seed_demo_data.py \
        --env "$ENVIRONMENT" \
        --region "$AWS_REGION" \
        --stack-name "$STACK_NAME"
fi

if [[ "$DEPLOY_FRONTEND" == "true" ]]; then
    printf 'VITE_API_BASE_URL=/api/v1\nVITE_WS_URL=%s\n' \
        "$WEBSOCKET_URL" \
        > frontend/.env.production

    (
        cd frontend
        npm ci --silent
        npm run build
    )

    aws s3 sync frontend/dist/ "s3://${FRONTEND_BUCKET}/" --delete
    invalidation_id="$(
        aws cloudfront create-invalidation \
            --distribution-id "$CLOUDFRONT_DISTRIBUTION_ID" \
            --paths "/*" \
            --query "Invalidation.Id" \
            --output text
    )"
    aws cloudfront wait invalidation-completed \
        --distribution-id "$CLOUDFRONT_DISTRIBUTION_ID" \
        --id "$invalidation_id"

    curl --fail --silent --show-error "https://${CLOUDFRONT_DOMAIN}/" >/dev/null
fi

echo
echo "Deployment complete"
echo "  API:       ${REST_API_URL}/api/v1"
echo "  WebSocket: ${WEBSOCKET_URL}"
if [[ "$DEPLOY_FRONTEND" == "true" ]]; then
    echo "  Frontend:  https://${CLOUDFRONT_DOMAIN}"
else
    echo "  Local UI:  cd frontend && npm run dev"
fi
