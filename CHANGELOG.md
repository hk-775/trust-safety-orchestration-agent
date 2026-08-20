# Changelog

All notable changes to this project are documented here.

## 1.0.0 - 2026-08-20

### Added

- Single-use, 60-second WebSocket connection tickets with a Lambda authorizer.
- Secrets Manager-backed API-key and bearer authentication for platform and
  partner integrations.
- Optional customer-managed KMS key permissions scoped through Secrets Manager.
- Guarded production deployment inputs and a production deployment runbook.

### Changed

- Operational metrics now require Cognito authentication.
- Browser authentication state is memory-only.
- Production health responses expose only aggregate status.
- AWS SDK, Redis, Vite, jsdom, TypeScript, Zustand, Testing Library, PostCSS
  tooling, and pinned GitHub Actions were updated together.
- Dependabot uses native uv lockfile support, and CI verifies that generated
  Lambda requirements remain synchronized with `uv.lock`.
- Dependabot groups coupled packages and ignores unsupported framework majors.

### Security

- WebSocket clients can no longer trigger server-wide metrics broadcasts.
- API Gateway authorizer caching is disabled to prevent ticket replay.
- Integration credentials are cached for at most five minutes to support
  rotation.
- Secret and optional KMS permissions are limited to their exact configured
  ARNs and only the functions that use them.

### Validation

- 196 backend tests and 2 frontend tests pass.
- Clean-clone Python and npm installs, frontend build, and SAM packaging pass.
- SAM validation, cfn-lint, AWS Security Pillar Guard rules, Bandit, Zizmor,
  Gitleaks, pip-audit, and npm audit pass.
