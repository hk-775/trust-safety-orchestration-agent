# Trust & Safety Orchestration Agent

An event-driven AWS sample for detecting, investigating, and resolving policy
violations with automated enforcement and human review.

> [!IMPORTANT]
> This is reference/sample code, not a production-ready moderation system.
> Do not process real user data with it. Direct `prod` deployment is disabled
> until the security gaps in [the deployment runbook](docs/deployment.md#production-release-gaps)
> are resolved.

## Architecture

[Open the editable architecture diagram](docs/architecture.drawio).

The processing flow is **Detection > Investigation > Decision > Enforcement**:

1. Kinesis events are scored for anomalous behavior.
2. Step Functions coordinates evidence gathering and policy evaluation.
3. High-confidence cases are enforced automatically; sensitive or uncertain
   cases enter a review queue.
4. DynamoDB and S3 preserve operational state, evidence, and audit records.
5. CloudFront serves the React dashboard and proxies REST requests; the
   dashboard connects directly to the WebSocket API.

The stack uses Lambda, API Gateway, Step Functions, DynamoDB, S3, Cognito,
Kinesis, SQS, SNS, EventBridge, CloudFront, and optional ElastiCache Redis.

## Prerequisites

- AWS CLI v2 with active credentials
- AWS SAM CLI
- `uv`
- Node.js `20.19+`, `22.12+`, or a newer major release; Node 22 is recommended
- npm

Install dependencies and validate both build artifacts:

```bash
git clone https://github.com/hk-775/trust-safety-orchestration-agent.git
cd trust-safety-orchestration-agent
./setup.sh
```

## Local Demo

The frontend uses mock data when `frontend/.env.local` is absent:

```bash
cd frontend
npm ci
npm run dev
```

Open `http://localhost:3000`.

## Deployment Profiles

| Profile | Redis/VPC | Network egress | Data deletion |
| --- | --- | --- | --- |
| `dev` | Disabled by default | Lambda public service networking | Deleted with stack |
| `staging` | Configurable | One shared NAT when Redis is enabled | Deleted with stack |
| `prodtest` | Required | One NAT gateway per Availability Zone | Deleted with stack |
| `prod` | Required | One NAT gateway per Availability Zone | Core data retained |

When Redis is disabled, Redis-dependent features are disabled and the health
endpoint reports Redis as `disabled`. When Redis is enabled, VPC-attached
functions use S3/DynamoDB gateway endpoints and NAT for AWS and external APIs.

### Seeded Development Deployment

> [!WARNING]
> Deployment creates billable AWS resources. Review the template and your AWS
> budget first, and run the documented teardown when testing is complete.

```bash
read -r -s -p "Demo admin password: " DEMO_ADMIN_PASSWORD
printf '\n'
export DEMO_ADMIN_PASSWORD
make quickstart
unset DEMO_ADMIN_PASSWORD
```

This installs dependencies, deploys `trust-safety-orch-dev` without Redis,
checks `/api/v1/health`, creates the demo Cognito user and data, builds the
frontend, uploads it to S3, invalidates CloudFront, and prints the live URL.

### Standard Deployments

```bash
# Lightweight dev
make deploy-lite

# Staging, backend and frontend
make deploy \
  ENVIRONMENT=staging \
  STACK_NAME=trust-safety-orch-staging \
  USE_REDIS=false

# Backend only
make deploy-backend \
  ENVIRONMENT=staging \
  STACK_NAME=trust-safety-orch-staging
```

The deployment writes `frontend/.env.local` from CloudFormation outputs, so
`make dev` connects to the deployed backend rather than mock data.

### Production Rehearsal

The public deployment path intentionally supports `dev`, `staging`, and
`prodtest`, but not `prod`. The template also requires
`AcknowledgeIncompleteProduction=true` for a direct production deployment.
That acknowledgement is not a substitute for implementing the documented
authentication, authorization, logging, encryption, schema-validation, and
cost controls.

For a deletion-safe production-topology rehearsal, deploy `prodtest`. It uses
the production Redis, dual-NAT, logging, and stream sizing while keeping
stateful resources removable. An in-stack API Gateway mock replaces the three
external platform integrations, so only an enabled Bedrock model is required:

> [!WARNING]
> `prodtest` creates two NAT gateways, a Redis node, and a four-shard Kinesis
> stream. These resources incur charges until the stack is deleted.

```bash
BEDROCK_MODEL_ID=us.anthropic.claude-sonnet-4-6 \
  make deploy-prodtest CONFIRM_PRODUCTION_DEPLOY=true
```

See [Deployment and Production Rehearsal](docs/deployment.md) for the external
API contracts, Cognito user bootstrap, validation checklist, reliability
behavior, production release gaps, and teardown details.

## Frontend Configuration

For direct API Gateway access, the REST URL must include `/api/v1`:

```dotenv
VITE_API_BASE_URL=https://<api-id>.execute-api.<region>.amazonaws.com/<env>/api/v1
VITE_WS_URL=wss://<api-id>.execute-api.<region>.amazonaws.com/<env>
```

The hosted build uses `/api/v1` as a same-origin CloudFront path and the direct
WebSocket endpoint for real-time updates.

## GitHub Deployment

`.github/workflows/deploy.yml` provides a manual OIDC-based deployment.
Create protected GitHub environments named `dev`, `staging`, and `prodtest`,
then configure:

- Environment variable `AWS_DEPLOY_ROLE_ARN`
- Environment variable `AWS_ACCOUNT_ID`
- Environment variable `BEDROCK_MODEL_ID` for `prodtest`
- Optional environment variable `ALLOWED_CORS_ORIGIN` for direct browser access
- Optional non-production secret `DEMO_ADMIN_PASSWORD`

The IAM role must trust GitHub's OIDC provider only when the token audience is
`sts.amazonaws.com` and the token subject exactly identifies this repository
and the selected environment, for example
`repo:hk-775/trust-safety-orchestration-agent:environment:prodtest`. Do not use
an organization-wide or repository-wide wildcard subject. Restrict each
environment to the `main` branch, add required reviewers to `prodtest`, and
grant the deployment role only the permissions required by the reviewed SAM
change set. The workflow refuses deployment runs from other branches.

CI runs Python lint/tests, SAM validation/build, frontend tests, and the
production frontend build using Node 22.

## Operations

```bash
make test
make lint
make audit
make build
make frontend-build
make seed ENVIRONMENT=dev STACK_NAME=trust-safety-orch-dev
make simulate ENVIRONMENT=dev AWS_REGION=us-east-1
```

Delete a non-production stack and empty all managed buckets first:

```bash
make destroy ENVIRONMENT=dev STACK_NAME=trust-safety-orch-dev

make destroy \
  ENVIRONMENT=prodtest \
  STACK_NAME=trust-safety-orch-prodtest
```

The teardown utility retains production data if a downstream fork has created
a production stack with its own reviewed deployment process.

## Project Structure

```text
template.yaml                 SAM infrastructure
samconfig.toml                Safe default SAM configuration
statemachines/                Step Functions definitions
lambdas/handlers/             API handlers
lambdas/processors/           Stream and event processors
lambdas/services/             Business logic
lambdas/repositories/         Persistence adapters
lambdas/tests/                Backend tests
frontend/                     React and Vite dashboard
scripts/deploy.sh             Repeatable backend/frontend deployment
scripts/delete_stack.py       Bucket-aware stack teardown
scripts/seed_demo_data.py     Non-production demo seeding
scripts/live_simulator.py     Non-production activity simulator
docs/deployment.md            Deployment, validation, and teardown runbook
docs/open-source-publication.md Final repository publication checklist
SECURITY.md                   Private vulnerability reporting process
SUPPORT.md                    Community support expectations
```

## Security

- REST API routes use Cognito authorization except explicitly public auth,
  health, and metrics routes. Reassess those public telemetry routes before
  production use.
- The browser sample stores only the Cognito ID token in `sessionStorage`; it
  does not return or persist Cognito access or refresh tokens.
- WebSocket routes are currently unauthenticated; production must add an
  authorizer before release.
- External integration URLs are required to use HTTPS and path/query values
  are encoded before requests are sent.
- CloudFront adds CSP, HSTS, clickjacking, MIME-sniffing, referrer, and browser
  permissions headers.
- S3 public access is blocked and CloudFront uses origin access control.
- S3 server access logs are retained in a dedicated private bucket for 90 days.
- DynamoDB and S3 encrypt data at rest.
- Lambda tracing is enabled and IAM policies are scoped by workload.
- Production core data uses retention policies.
- Audit logging is part of enforcement workflows.

See [SECURITY.md](SECURITY.md) for private vulnerability reporting and
[SUPPORT.md](SUPPORT.md) for support expectations.

## License

This project is licensed under the MIT-0 License. See [LICENSE](LICENSE).

This repository is derived from the public
[`aws-samples/sample-trust-safety-orchestration-agent`](https://github.com/aws-samples/sample-trust-safety-orchestration-agent)
sample. The bundled narration assets are unchanged from that MIT-0-licensed
upstream source.
