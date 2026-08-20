#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT_DIR"

echo "Trust & Safety Orchestration Agent setup"

for command_name in aws sam node npm; do
    if ! command -v "$command_name" >/dev/null 2>&1; then
        echo "ERROR: Required command not found: ${command_name}" >&2
        exit 1
    fi
done

if ! node -e '
    const [major, minor] = process.versions.node.split(".").map(Number);
    const supported = major === 20 ? minor >= 19 : major === 22 ? minor >= 12 : major > 22;
    process.exit(supported ? 0 : 1);
'; then
    echo "ERROR: Node.js 20.19+, 22.12+, or a newer major release is required." >&2
    exit 1
fi

if ! command -v uv >/dev/null 2>&1; then
    echo "ERROR: uv is required. Install it from https://docs.astral.sh/uv/getting-started/installation/." >&2
    exit 1
fi

echo "Installing Python dependencies..."
uv sync --locked --quiet

echo "Installing frontend dependencies..."
(
    cd frontend
    npm ci --silent
)

echo "Building SAM application..."
sam build --parallel

echo "Building frontend..."
(
    cd frontend
    npm run build
)

if aws sts get-caller-identity >/dev/null 2>&1; then
    account_id="$(aws sts get-caller-identity --query Account --output text)"
    region="$(aws configure get region 2>/dev/null || true)"
    echo "AWS credentials available for account ${account_id}, region ${region:-us-east-1}."
else
    echo "AWS credentials are not active. Authenticate before running a deployment."
fi

echo "Setup complete. Run 'make quickstart' for a seeded dev deployment."
