# Deployment and Production Rehearsal

This runbook covers repeatable deployments, the deletion-safe `prodtest`
rehearsal, production integration requirements, validation, and teardown.

Direct production deployment is intentionally disabled in `scripts/deploy.sh`
and the public GitHub workflow. The SAM template additionally requires
`AcknowledgeIncompleteProduction=true` if a downstream fork deploys `prod`
directly. Do not enable it until every item under
[Production Release Gaps](#production-release-gaps) is resolved and reviewed.

## Public Repository Deployment Controls

The deployment workflow is manual, uses GitHub OIDC instead of stored AWS
access keys, and runs only from the `main` branch. Configure separate protected
GitHub environments for `dev`, `staging`, and `prodtest`.

For every AWS deployment role:

- Require the OIDC audience to equal `sts.amazonaws.com`.
- Require the subject to equal
  `repo:hk-775/trust-safety-orchestration-agent:environment:<environment>`.
- Do not trust organization-wide, repository-wide, branch, tag, or pull-request
  wildcard subjects.
- Scope the role permissions to the resources and operations required by the
  reviewed SAM deployment process; do not attach administrator access.
- Restrict the matching GitHub environment to `main`. Require independent
  approval for `prodtest` and prevent self-approval where the GitHub plan
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

## External Integration Contracts

Actual production requires three non-placeholder HTTPS base URLs:

| Variable | Current calls |
| --- | --- |
| `PLATFORM_USER_API_URL` | `GET /{userId}`, `GET /{userId}/reports`, `POST /{userId}/enforce`, `POST /{userId}/notifications` |
| `PLATFORM_MESSAGING_API_URL` | `GET /{userId}/messages?days=30` |
| `PARTNER_INTEL_API_URL` | `POST /intelligence/ingest` |

The user, messaging, and notification clients send an `X-Api-Key` header from
`PLATFORM_API_KEY`. The SAM template does not currently provision that value.
The partner intelligence publisher does not currently attach authentication.
Wire both integrations to an approved secret and authentication mechanism
before an actual production release.

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
4. Connect a real WebSocket client and trigger an immediate metrics broadcast.
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

## Production Release Gaps

Do not treat `prodtest` success as production approval. Before deploying
`prod`, address these known gaps:

- Provision and rotate authentication for all external integrations.
- Replace the sample's browser `sessionStorage` bearer-token handling with a
  reviewed production session design and corresponding CSRF/XSS controls.
- Add authorization to WebSocket `$connect`, `$disconnect`, and `$default`
  routes; they currently have no API Gateway authorizer.
- Decide whether health and operational metrics should remain public; protect
  or minimize them for the production threat model.
- Enable reviewed API Gateway and CloudFront access logging, request
  validation, throttling, and edge protection such as AWS WAF.
- Decide whether DynamoDB requires customer-managed KMS keys.
- Validate real upstream response schemas and failure behavior.
- Confirm the platform notification endpoint handles the `in_app` and `email`
  channel values carried in each queued message.
- Review NAT gateway, Redis, Kinesis, CloudWatch, and retained-storage costs.
- Replace the template acknowledgement gate and deployment-script refusal only
  after an independent security and operational review.
