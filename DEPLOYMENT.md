# Deployment Guide

This guide records the current manual deployment contract. Automated production
delivery and infrastructure-as-code remain later roadmap work in
`IMPLEMENTATION_PLAN.md`.

## Required Validation

Pull requests and `main` pushes run the small Level 2 suite in
`.github/workflows/validate.yml` with two independent required jobs:

- `Backend smoke tests`
- `Frontend smoke tests and lint`

Configure branch protection for `main` to require both checks. A failure in one
application must not hide the result of the other. CI uses placeholder or local
configuration, mocks external services, and must not consume NASA quota or write
to Firestore or BigQuery. Very important changes receive the `full-validation` label
or a manual `.github/workflows/full-validation.yml` run. Releases require both
full application suites. `TESTING.md` defines the levels and triggers.

## Supported Runtimes

- Backend: Python 3.13.11 from `backend/.python-version`
- Frontend: Node.js 22.21.0 from `frontend/.nvmrc`, npm 10.9.4

Direct Python dependencies are declared in `backend/requirements.in`; the fully
resolved deployment set is pinned in `backend/requirements.txt`. Frontend
dependencies are installed from `frontend/package-lock.json` with `npm ci`.

### Dependency Updates

Update dependencies deliberately rather than removing version pins. For Python,
change one direct version in `requirements.in`, resolve it in a clean Python
3.13.11 environment, and replace `requirements.txt` with the complete output of
`python -m pip freeze`. Review every transitive change, reinstall that lock in a
second clean environment, and run the full backend suite before merging.

For the frontend, update one dependency with `npm install package@version`,
review both `package.json` and `package-lock.json`, then run tests, lint, and the
production build. Use `npm ci` once more to verify that the lockfile reproduces a
clean install. Runtime version changes must update `.python-version`, `.nvmrc`,
the `engines` field, CI, and this guide together.

## Backend Build Strategy

The backend uses a Cloud Run source deployment, not a repository Dockerfile.
Google Cloud Buildpacks build `backend/` using `.python-version` and
`requirements.txt`; the `Procfile` starts one Uvicorn process:

```text
web: uvicorn main:app --host 0.0.0.0 --port $PORT
```

Cloud Run provides process scaling. The NASA cache, refresh lock, and retry state
remain local to each instance, so adding Uvicorn workers would duplicate those
resources and upstream coordination. Keep one worker unless that architecture is
changed deliberately.

The production request timeout target is 60 seconds. NASA also has separate
5-second connect and 30-second socket-inactivity timeouts plus response byte and
row limits; these are not a strict end-to-end 35-second deadline. Keep
concurrency at or below 20 until load tests establish a different safe value.
Preserve the current runtime service account, Secret Manager bindings,
environment variables, ingress, and public access policy during source
deployments.

Deploy from the repository root after backend validation:

```bash
gcloud run deploy wildfire-api --source backend --region europe-west1 --timeout 60 --concurrency 20
```

Do not pass broad `--set-env-vars` or `--set-secrets` flags during routine code
deployments because they can replace existing production configuration. Verify
configuration separately with `gcloud run services describe` before deployment.

Smoke-test only the liveness endpoint, which consumes no NASA quota:

```bash
curl https://wildfire-api-440479996053.europe-west1.run.app/
```

If the new revision is unhealthy, direct traffic back to the previous healthy
Cloud Run revision. Do not delete the failed revision until its logs and build
metadata have been inspected.

## Frontend Build Strategy

Build with the production API and public Firebase/App Check values from the
deployment environment:

```bash
cd frontend
npm ci
npm test
npm run lint
npm run build:production
firebase deploy --only hosting
```

`build:production` fails before Vite runs unless `VITE_API_URL` and all four
Firebase/App Check variables are available in the shell or a production env
file. This prevents publishing a bundle that Cloud Run will reject for missing
App Check.

After deployment, open the canonical Hosting URL and verify that the page loads,
the API returns detections, App Check succeeds, and both map layers can be
selected. If the release is unhealthy, use Firebase Hosting release history to
roll back to the prior version.

## Schema Order

The checked-in DDL uses validated identifier placeholders. Render it from
`backend/` using the target `BIGQUERY_PROJECT_ID` and `BIGQUERY_DATASET`, inspect
the generated SQL, and only then submit it with `bq query --use_legacy_sql=false`:

```bash
python render_bigquery_sql.py create_bigquery_schema.sql > rendered-schema.sql
python render_bigquery_sql.py migrate_fire_detection_quality.sql > rendered-migration.sql
```

Use the schema resource when provisioning a new dataset. For an existing
deployment, run each applicable reviewed migration before deploying code that
writes new fields. In particular, `migrate_fire_detection_quality.sql` must run
before the quality-aware ingestion code is enabled. Generated `rendered-*.sql`
files are deployment artifacts and must not be committed.

Schema changes and application releases must remain separately reversible. Never
run schema SQL from tests or a public API request.
