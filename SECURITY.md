# Security policy

## Public data boundary

This repository intentionally publishes holiday generators, corrections, tests,
dependency locks, licenses and generated holiday JSON. Anyone can read or fork it.
Public visibility does not grant permission to push changes or deploy the service.
Do not add app source, backups, schedules, account records, credentials or personal
data. Clients make anonymous HTTPS requests for a manifest and their selected
country file. SHA-256 checks detect corruption/version mismatches; they do not
protect against a compromised maintainer or hosting account.

## Repository controls

- Secret scanning, push protection, Dependabot alerts/security updates and private
  vulnerability reporting are enabled. Detection is not a guarantee that no secret
  has escaped; revoke exposed credentials immediately rather than only deleting a file.
- Actions are limited to GitHub-owned actions, with full commit SHA pinning required.
  Dependabot proposes weekly updates for Actions, npm and Python dependencies.
  Dependency PRs are reviewed and tested; automatic merge is disabled. The holidays
  data source has its own daily stable-version resolver and regression tests.
- All outside contributors require approval before a pull-request workflow runs.
  PRs only generate and test data. Never switch this to `pull_request_target` and
  execute contributor code with deployment credentials.
- `main` disallows force pushes and deletion, requires linear history and resolved
  review conversations, and applies these protections to administrators.
  Mandatory PR reviews/status checks are deliberately not enabled: the daily
  trusted bot records verified data directly on `main` without an extra PAT or
  GitHub App. Only trusted maintainers should have write access. Use reviewed PRs
  for human changes and reconsider this policy before expanding the maintainer team.

## Deployment credentials and recovery

- GitHub's `production` environment allows only the `main` branch. Its environment
  secret `CLOUDFLARE_API_TOKEN` is available only in the publish job, after generation
  and tests. Do not duplicate it as a repository or organization secret.
- The Cloudflare account-owned token `bintong-holidays-production` grants
  **Individual Workers Editor** to **bintong-holidays** only. It grants no access to
  the `tong-studio` website, no DNS/zone editing and no Worker creation/deletion.
- The publish job has read-only GitHub contents permission. A separate job writes
  the verified public data/check record, without the Cloudflare environment secret.
  An outdated source revision is rejected before publishing, and recording uses a
  normal fast-forward push without force/rebase.
- `versions upload` and `versions deploy` replace the existing Worker's static
  asset version without reconciling custom domains. Domain or service provisioning
  requires a separate administrator action. Do not replace this with `wrangler
  deploy` or grant account-wide Workers access to fix a domain-related error.
- HTTPS verification failures restore the previous 100% version. A manual workflow
  run with `force_deploy: true` exercises deployment even when data has not changed.
  For manual recovery, deploy the known-good version at 100%, then revert the bad
  source change on `main` and rerun the workflow. Failed runs remain visible in Actions.
- To rotate a token, create the same single-Worker Editor scope, replace the
  production environment secret, run a forced deployment, verify HTTPS, and then
  disable the previous token. Never put tokens in issues, logs or screenshots.

Maintain MFA/passkeys and recovery methods on GitHub and Cloudflare administrator
accounts. Repository controls cannot enforce the security of a separate hosting
account; organization-wide MFA policy and account recovery remain owner decisions.

## Reporting a vulnerability

Use [GitHub private vulnerability reporting](https://github.com/Tong-Studio/bintong-holidays/security/advisories/new).
Do not post credentials or exploit details in a public issue. Ordinary holiday
corrections can be submitted publicly with an official announcement URL.
