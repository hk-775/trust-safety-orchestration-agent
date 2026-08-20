# Deployment and Production Rehearsal

This runbook covers repeatable deployments, the deletion-safe `prodtest`
rehearsal, production integration requirements, validation, and teardown.

Production deployment is guarded by explicit confirmation, required
production topology, non-placeholder integration URLs, secret-backed
integration authentication, and an explicit Bedrock model. Complete
[Production Deployment Checklist](#production-deployment-checklist) before
using the `prod` profile.

## Public Repository Deployment Controls

The deployment workflow is manual, uses GitHub OIDC instead of stored AWS
access keys, and runs only from the `main` branch. Configure separate protected
GitHub environments for `dev`, `staging`, `prodtest`, and `prod`.

For every AWS deployment role:

- Require the OIDC audience to equal `sts.amazonaws.com`.
- Require the subject to equal
  `repo:hk-775/trust-safety-orchestration-agent:environment:<environment>`.
- Do not trust organization-wide, repository-wide, branch, tag, or pull-request
  wildcard subjects.
- Scope the role permissions to the resources and operations required by the
  reviewed SAM deployment process; do not attach administrator access.
- Restrict the matching GitHub environment to `main`. Require independent
  approval for `prodtest` and `prod`, and prevent self-approval where the GitHub plan
  supports it.

Environment variables and secrets must be configured on the environment, not
at repository or organization scope. Public fork pull requests run only the CI
workflow and receive neither the deployment environment nor AWS credentials.

## Environment Profiles

| Environment | Redis and VPC | Egress | Stateful resource deletion |
| --- | --- | --- | --- |
| `dev` | Disabled by default | Lambda service networking | Delete |
| `staging` | Optional | One shared NAT when Redis is enabled | Delete |
| `prodtest` | Required | One NAT gateway per Availability Zone | Delete |
| `prod` | Required | One NAT gateway per Availability Zone | Retain core data |

`prodtest` uses production-like logging, Kinesis sizing, Redis, and network
topology. It substitutes an in-stack API Gateway mock for the external platform
services and is intended for disposable infrastructure testing only.

Deploy at most one stack for a given environment in each account and region.
Globally scoped S3 and CloudFront resource names include the account and region,
so the same environment can be rehearsed independently in another region.

Redis-enabled functions run in two private subnets. The VPC provides:

- An S3 gateway endpoint.
- A DynamoDB gateway endpoint.
- NAT egress for Bedrock and external HTTPS APIs.
- Two NAT gateways for `prodtest` and `prod`; staging shares one NAT gateway.

The WebSocket handler intentionally runs outside the VPC. It does not use
Redis and needs direct access to the API Gateway Management API to call
`post_to_connection`. Its role can read metrics, cases, and the review queue,
manage connection records, and call `execute-api:ManageConnections`.

The dashboard obtains a single-use WebSocket ticket from the
Cognito-protected `/api/v1/auth/websocket-ticket` route. The ticket expires
after 60 seconds and is atomically deleted by the `$connect` Lambda authorizer.
The browser never places its Cognito token in the WebSocket URL.

## External Integration Contracts

Actual production requires three non-placeholder HTTPS base URLs:

| Variable | Current calls |
| --- | --- |
| `PLATFORM_USER_API_URL` | `GET /{userId}`, `GET /{userId}/reports`, `POST /{userId}/enforce`, `POST /{userId}/notifications` |
| `PLATFORM_MESSAGING_API_URL` | `GET /{userId}/messages?days=30` |
| `PARTNER_INTEL_API_URL` | `POST /intelligence/ingest` |

Each integration supports `api-key` or `bearer` authentication:

| Variable | Purpose |
| --- | --- |
| `PLATFORM_AUTH_MODE` | Authentication for user, messaging, enforcement, and notification calls |
| `PLATFORM_AUTH_SECRET_ARN` | Exact Secrets Manager ARN containing the platform credential as `SecretString` |
| `PLATFORM_AUTH_KMS_KEY_ARN` | Optional customer-managed KMS key ARN for the platform secret |
| `PARTNER_INTEL_AUTH_MODE` | Authentication for intelligence publishing |
| `PARTNER_INTEL_AUTH_SECRET_ARN` | Exact Secrets Manager ARN containing the partner credential as `SecretString` |
| `PARTNER_INTEL_AUTH_KMS_KEY_ARN` | Optional customer-managed KMS key ARN for the partner secret |

Both mode variables accept `api-key` or `bearer`. The template does not create
credential values. Provision and rotate the secrets through your approved
process, then provide only their ARNs. Lambda execution roles receive
`secretsmanager:GetSecretValue` only for their specific integration secret.
Warm functions refresh cached credentials after five minutes.

The runtime URL builder rejects non-HTTPS schemes, URL credentials, query
strings, and fragments in configured base URLs. User identifiers and query
values are percent-encoded before requests are sent.

The `prodtest` mock returns HTTP 200 with an empty JSON object for every route.
This verifies VPC/NAT egress and failure-tolerant application behavior; it does
not validate a real upstream schema or authentication flow.

## Bedrock

Dev and staging may omit `BEDROCK_MODEL_ID`; message analysis then uses only
the deterministic pattern checks. Production-like deployments require an
explicit model ID. An inference profile
such as `us.anthropic.claude-sonnet-4-6` may be used when it is enabled in the
target account and region.

The evidence assembler role allows:

- `bedrock:InvokeModel` on account inference profiles in the deployed region.
- `bedrock:InvokeModel` on the foundation models used by cross-region profiles.

Verify model availability and invoke access in the target account before
creating the stack.

## Preflight

Run the complete local validation before deployment:

```bash
make test
make lint
make build
make frontend-build
sam validate --lint --region us-east-1
npm --prefix frontend audit --omit=dev --audit-level=high
```

For production changes, also review the CloudFormation change set for
replacements, IAM expansion, networking changes, and retained resources before
execution.

## Deploy Prodtest

`prodtest` creates two NAT gateways, a Redis node, and a four-shard Kinesis
stream. These resources are billable until teardown completes.

```bash
BEDROCK_MODEL_ID=us.anthropic.claude-sonnet-4-6 \
  make deploy-prodtest \
  CONFIRM_PRODUCTION_DEPLOY=true \
  AWS_REGION=us-east-1
```

The deployment script:

1. Builds and deploys the SAM stack with rollback enabled.
2. Waits for the REST health endpoint.
3. Writes local and hosted frontend environment files from stack outputs.
4. Builds and uploads the frontend.
5. Invalidates CloudFront and verifies the hosted root page.

Prodtest does not seed demo data or create a Cognito user.

## Deploy Production

Production creates retained data resources and billable dual-NAT, Redis, and
Kinesis capacity. Use a protected `prod` GitHub environment with independent
approval, or provide the required values locally without putting credential
values in source control or shell history. The reserved example hostnames
below are deliberately rejected by the deployment script; replace them with
reviewed production endpoints:

```bash
export PLATFORM_USER_API_URL=https://users.example.org/v1
export PLATFORM_MESSAGING_API_URL=https://messages.example.org/v1
export PARTNER_INTEL_API_URL=https://intel.example.org/v1
export PLATFORM_AUTH_MODE=api-key
export PLATFORM_AUTH_SECRET_ARN=arn:aws:secretsmanager:REGION:ACCOUNT:secret:platform
export PARTNER_INTEL_AUTH_MODE=bearer
export PARTNER_INTEL_AUTH_SECRET_ARN=arn:aws:secretsmanager:REGION:ACCOUNT:secret:partner
# Set the matching *_KMS_KEY_ARN variables only for customer-managed keys.
export BEDROCK_MODEL_ID=your-enabled-model-or-inference-profile

make deploy-prod \
  CONFIRM_PRODUCTION_DEPLOY=true \
  AWS_REGION=us-east-1
```

Unset the deployment variables when the operation finishes. The secret values
themselves are resolved only by the authorized Lambda functions at runtime.

## Create an Operator Login

Create production-like users administratively. Keep passwords out of shell
history, source control, command output, and chat.

```bash
STACK_NAME=trust-safety-orch-prodtest
AWS_REGION=us-east-1
USER_POOL_ID="$(
  aws cloudformation describe-stacks \
    --stack-name "$STACK_NAME" \
    --region "$AWS_REGION" \
    --query 'Stacks[0].Outputs[?OutputKey==`CognitoUserPoolId`].OutputValue | [0]' \
    --output text
)"

read -r -s -p "New admin password: " ADMIN_PASSWORD
printf '\n'

aws cognito-idp admin-create-user \
  --user-pool-id "$USER_POOL_ID" \
  --username admin \
  --user-attributes Name=custom:role,Value=admin \
  --temporary-password "$ADMIN_PASSWORD" \
  --message-action SUPPRESS \
  --region "$AWS_REGION"

aws cognito-idp admin-set-user-password \
  --user-pool-id "$USER_POOL_ID" \
  --username admin \
  --password "$ADMIN_PASSWORD" \
  --permanent \
  --region "$AWS_REGION"

unset ADMIN_PASSWORD
```

For an existing user, run only `admin-set-user-password` with a new
in-memory password.

## Post-Deployment Validation

Validate the deployed environment, not only the local build:

1. Confirm the stack reaches `CREATE_COMPLETE` or `UPDATE_COMPLETE` with no
   failed CloudFormation events.
2. Verify `/api/v1/health` directly and through CloudFront. DynamoDB should be
   healthy; Redis should be healthy when enabled.
3. Load the frontend, sign in through Cognito, and verify same-origin REST
   requests.
4. Request a WebSocket ticket through the authenticated REST API, connect once,
   and verify that replaying the same ticket is denied.
5. Hold a connection through an EventBridge schedule boundary and verify the
   scheduled broadcast.
6. Invoke Bedrock with the configured model or inference profile from the
   deployed role.
7. Run a labeled, benign investigation through Step Functions and verify case,
   evidence, review queue, audit, and S3 records.
8. Replay the escalation input and verify it returns the same queue ID without
   increasing the review queue count.
9. Remove all labeled smoke records and S3 object versions.
10. Check relevant CloudWatch logs and alarms after the final test.

## Workflow Reliability Behavior

The production rehearsal established these runtime requirements:

- The evidence assembler needs read/write access to the cases table because it
  persists investigation state as well as reading the case.
- The escalation handler needs read/write access to the audit table in addition
  to the cases and review queue tables.
- Audit repository values are recursively converted from Python `float` to
  `Decimal` before DynamoDB writes.
- Escalation and crisis queue entries use deterministic SHA-256-derived IDs
  when a deduplication key is supplied.
- Conditional queue writes make Step Functions retries idempotent: a retry
  returns the existing queue ID instead of creating another review item.

## Teardown

Prodtest is deletion-safe. The teardown utility empties all versioned managed
buckets before deleting the stack:

```bash
make destroy \
  ENVIRONMENT=prodtest \
  STACK_NAME=trust-safety-orch-prodtest \
  AWS_REGION=us-east-1
```

The teardown utility retains production evidence, audit, configuration
backups, and core DynamoDB tables if a downstream fork created a production
stack. It does not remove CloudWatch log groups or credentials created outside
CloudFormation. Inventory and handle those resources separately.

## Production Deployment Checklist

Do not treat `prodtest` success as production approval. The repository
implements memory-only browser tokens, authenticated metrics, one-time
WebSocket authorization, minimal production health responses, and
secret-backed upstream authentication. Before deploying `prod`, complete
these environment-specific decisions:

- Define and test application role authorization and MFA requirements for your
  operator, reviewer, and administrator model.
- Configure API Gateway/CloudFront access logging, throttling, alarms, and edge
  protection such as AWS WAF according to organizational policy.
- Decide whether DynamoDB requires customer-managed KMS keys.
- Validate real upstream response schemas and failure behavior.
- Confirm the platform notification endpoint handles the `in_app` and `email`
  channel values carried in each queued message.
- Confirm secret rotation schedules and resource policies. Provide the
  matching KMS key ARN when an integration secret does not use the AWS managed
  key.
- Review NAT gateway, Redis, Kinesis, CloudWatch, and retained-storage costs.
- Review data retention, privacy, regional residency, incident response, and
  human-oversight requirements before processing real user data.
