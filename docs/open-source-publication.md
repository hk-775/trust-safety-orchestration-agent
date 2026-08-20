# Open Source Publication Checklist

Complete this checklist from a reviewed commit, not from a dirty worktree.

## Source

- Confirm `LICENSE`, `NOTICE`, `CONTRIBUTING.md`, `CODE_OF_CONDUCT.md`,
  `SECURITY.md`, and `SUPPORT.md` are present.
- Confirm the publisher is authorized to release the repository. The source is
  derived from the public MIT-0 `aws-samples` repository identified in
  `NOTICE`, and the original Amazon copyright statement is preserved.
- Confirm bundled binary assets have a documented redistribution source. The
  narration MP3 files match the public MIT-0 upstream repository byte-for-byte;
  recheck provenance if any asset changes.
- Review author and committer names and email addresses across every published
  branch and tag. Rewrite history before publication if any identity should
  remain private, and configure a public or GitHub `noreply` address for the
  publication commit.
- Confirm Gitleaks reports no findings in Git history or publishable files.
- Run `make test`, `make lint`, `make audit`, `make build`, and
  `make frontend-build`.
- Run `sam validate --lint --region us-east-1` and `cfn-lint template.yaml`.
- Generate source-derived IAM requirements with IAM Policy Autopilot and
  compare them with each function's SAM policies. Do not replace scoped
  policies with the analyzer's combined wildcard output.
- Review the complete diff for account IDs, endpoints, credentials, user data,
  generated artifacts, and unrelated local changes.

## GitHub

- Keep the repository private until the publication commit is merged.
- Set an accurate description and topics; disable unused repository features.
- Make the repository public only after the source review is complete.
- Enable private vulnerability reporting, Dependabot alerts, secret scanning,
  push protection, and CodeQL default setup when the public repository supports
  them.
- Keep the default Actions token permission read-only and leave permission for
  Actions to create or approve pull requests disabled.
- Require approval before workflows from outside collaborators use hosted
  runners. Never use `pull_request_target` to execute untrusted pull-request
  code.
- Configure protected deployment environments so only `main` can deploy, use
  exact repository-and-environment OIDC subjects, and require a reviewer for
  `prodtest`.
- Protect `main` with pull-request review, required code-owner review, and
  required CI checks.
- Require branches to be current before merge, block force pushes and branch
  deletion, and delete merged branches.
- Verify issue and pull-request templates render correctly.

## Post-Publication

- Run CI from the public default branch.
- Verify CI from an untrusted fork has read-only token permissions and cannot
  access deployment environments, repository secrets, or AWS credentials.
- Test a fresh clone using the documented tool versions.
- Confirm the license is detected as MIT-0.
- Confirm no deployment, AWS resource, or credential was published.
- Create a release only after the public commit and checks are stable.
