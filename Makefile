SHELL := /bin/bash

ENVIRONMENT ?= dev
AWS_REGION ?= us-east-1
STACK_NAME ?= trust-safety-orch-$(ENVIRONMENT)
USE_REDIS ?= $(if $(filter prod prodtest,$(ENVIRONMENT)),true,false)
DEPLOY_FRONTEND ?= true
SEED_DEMO_DATA ?= false
CONFIRM_PRODUCTION_DEPLOY ?= false
ALLOW_PRODUCTION_DESTROY ?= false

.PHONY: setup audit build check-node frontend-build deploy deploy-backend deploy-lite deploy-prodtest deploy-quick dev clean test seed simulate help quickstart destroy lint

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-15s\033[0m %s\n", $$1, $$2}'

quickstart: setup ## Deploy a seeded dev stack and publish the frontend
	ENVIRONMENT=dev AWS_REGION=$(AWS_REGION) STACK_NAME=trust-safety-orch-dev \
		USE_REDIS=false DEPLOY_FRONTEND=true SEED_DEMO_DATA=true \
		./scripts/deploy.sh

setup: ## Install all dependencies (backend + frontend)
	./setup.sh

check-node:
	@command -v node >/dev/null 2>&1 || { echo "ERROR: Node.js is required." >&2; exit 1; }
	@node -e 'const [major, minor] = process.versions.node.split(".").map(Number); const supported = major === 20 ? minor >= 19 : major === 22 ? minor >= 12 : major > 22; process.exit(supported ? 0 : 1)' \
		|| { echo "ERROR: Node.js 20.19+, 22.12+, or a newer major release is required." >&2; exit 1; }

build: ## Build the SAM application
	sam build --parallel

audit: check-node ## Audit Python and frontend dependencies and Python security findings
	uv run pip-audit -r lambdas/requirements.txt --require-hashes --disable-pip
	uv run bandit -q -r lambdas -x lambdas/tests -ll
	cd frontend && npm audit --audit-level=high

frontend-build: check-node ## Build the production frontend
	cd frontend && npm run build

deploy: ## Deploy the selected environment and frontend
	ENVIRONMENT=$(ENVIRONMENT) AWS_REGION=$(AWS_REGION) STACK_NAME=$(STACK_NAME) \
		USE_REDIS=$(USE_REDIS) DEPLOY_FRONTEND=$(DEPLOY_FRONTEND) \
		SEED_DEMO_DATA=$(SEED_DEMO_DATA) \
		CONFIRM_PRODUCTION_DEPLOY=$(CONFIRM_PRODUCTION_DEPLOY) \
		./scripts/deploy.sh

deploy-backend: ## Deploy backend only for the selected environment
	$(MAKE) deploy DEPLOY_FRONTEND=false

deploy-lite: ## Deploy a lightweight dev stack without VPC/Redis
	$(MAKE) deploy ENVIRONMENT=dev STACK_NAME=trust-safety-orch-dev USE_REDIS=false

deploy-prodtest: ## Deploy a deletion-safe production-topology rehearsal
	$(MAKE) deploy ENVIRONMENT=prodtest STACK_NAME=trust-safety-orch-prodtest USE_REDIS=true

deploy-quick: deploy-lite ## Backward-compatible alias for the dev deployment

dev: check-node ## Start frontend (mock mode unless frontend/.env.local exists)
	cd frontend && npm run dev

test: check-node ## Run backend and frontend tests
	uv run pytest lambdas/tests/ -v
	cd frontend && npm test

lint: check-node ## Lint backend, deployment utilities, and frontend
	uv run ruff check lambdas/ scripts/delete_stack.py scripts/live_simulator.py scripts/seed_demo_data.py
	cd frontend && npm run lint

seed: ## Seed demo data into DynamoDB tables
	uv run python scripts/seed_demo_data.py \
		--env $(ENVIRONMENT) \
		--region $(AWS_REGION) \
		--stack-name $(STACK_NAME)

simulate: ## Generate live demo activity in dev or staging
	uv run python scripts/live_simulator.py \
		--env $(ENVIRONMENT) \
		--region $(AWS_REGION)

clean: ## Remove build artifacts
	rm -rf .aws-sam/ frontend/dist/ lambdas/__pycache__/ .venv/

destroy: ## Empty managed buckets and delete the selected stack
	uv run python scripts/delete_stack.py \
		--env $(ENVIRONMENT) \
		--region $(AWS_REGION) \
		--stack-name $(STACK_NAME) \
		$(if $(filter true,$(ALLOW_PRODUCTION_DESTROY)),--allow-production,)
