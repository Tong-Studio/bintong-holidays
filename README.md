# BinTong public holidays

Public holiday snapshots for BinTong. Data: https://holidays.tong-studio.com/v1/manifest.json

Only PUBLIC holidays and observed/substitute dates are included. Country codes
include territories; availability and future accuracy follow python-holidays.
No account, user records, tracking IDs, API keys or GPS are used by clients.
No government-announcement crawler or immediate-update guarantee is provided.

## Generate and verify

Use Python 3.12+, `pip install -r requirements.txt`, then:

```
python scripts/holiday_data.py generate
python -m unittest discover -s tests -v
npm ci
npm run check
```

The supported range starts in 2024 and ends four years after the current UTC year.
Country JSON URLs are content-addressed SHA-256 paths. Manifest schema is v1;
clients reject unknown schemas. `v1/changes` records the changed countries for each retained release. Only the current and two preceding snapshots
remain published. Clients fetch a fresh manifest before requesting changed country bytes.
An app must distinguish unsupported coverage from a known date with no holiday.

## Corrections

Edit `overrides.json` with records containing `country`, optional `subdivision`,
`date` (YYYY-MM-DD), `action` (add/replace/remove), `names` (en required, ko/ja
optional; omit for remove), `sourceUrl` (official HTTPS announcement), and `reason`.
The maintainer verifies the source before merging. Nationwide changes apply to
all subdivisions before local changes. Duplicate region/date records are rejected.
Corrections are idempotent if upstream later adds the same holiday. Remove an
override after confirming upstream agrees. Do not put fictional examples into
production corrections.

## Publishing and recovery

Daily 00:17 UTC (09:17 Asia/Seoul), manual runs, and source changes on main resolve
the latest stable holidays release. Generation has no deployment credentials.
The publish job verifies the candidate, deploys static assets, checks HTTPS bytes
and cache headers, and rolls back to the previous 100% version if validation fails.
The initial service must be provisioned manually with a validated snapshot first.

Configure repository variable `CLOUDFLARE_ACCOUNT_ID` and a **production environment**
secret `CLOUDFLARE_API_TOKEN`. Restrict that environment to the `main` branch. The
account-owned Cloudflare token needs **Individual Workers Editor** for
**bintong-holidays** only. Versions are uploaded and deployed without changing
existing domains/routes; no account-wide Workers or zone permissions are needed.
Never put tokens in source or the app. The publish job has read-only GitHub access;
a separate job records public data without the Cloudflare secret. Deployment is
via this workflow only; do not enable a second
Cloudflare Git build trigger. Standard public GitHub runners and static assets
avoid request-based application compute billing. No paid storage/database is used.

Inspect failed GitHub Actions runs; enable GitHub's workflow failure notifications.
`status.json` records each successful check even if data is unchanged, maintaining
repository activity. GitHub can disable public schedules after 60 inactive days;
if that happens, re-enable the workflow and run it manually. Schedules may be late.
To check a rotated token, manually run the workflow with `force_deploy: true`.
For manual recovery, use `npx --no-install wrangler versions deploy <version-id>@100 --yes`, then revert
the bad generator/override change and re-run the workflow. Do not modify the
existing tong-studio website service.

## Security

See [SECURITY.md](SECURITY.md) for access boundaries, branch protections,
dependency updates, credential rotation and private vulnerability reports.
The repository and holiday data remain intentionally public.

## Licenses

Generator code: MIT (LICENSE). Redistributed source notices: public/LICENSES.txt.
Upstream: https://github.com/vacanza/holidays and https://babel.pocoo.org/.
