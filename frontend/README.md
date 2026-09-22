# Wildfire Tracker Frontend

React and Leaflet client for recent NASA FIRMS detections and possible fire
clusters across the Iberian Peninsula. The frontend is an independent Vite
application and communicates only with the FastAPI service.

## Requirements

- Node.js 22.21.0, recorded in `.nvmrc`
- npm 10.9.4

## Setup

Install the locked dependencies:

```bash
npm ci
```

The default development API path is `/api`; `vite.config.js` proxies it to
`http://127.0.0.1:8000`. To call another API, create `.env.local` from
`.env.example` and set `VITE_API_URL`.

Firebase web and reCAPTCHA values are public browser configuration, not server
secrets. When they are absent, App Check is intentionally disabled for local
development. Production builds must provide all four Firebase/App Check values.
Never place `NASA_KEY`, the client-ID HMAC secret, or Google service credentials
in a `VITE_*` variable.

## Commands

```bash
npm run dev
npm run test:smoke
npm test
npm run lint
npm run build
npm run preview
```

`npm run test:smoke` runs the small set used by ordinary pull requests. `npm
test` uses automatic discovery for the full suite and is reserved for very important
frontend changes and releases. See the root `TESTING.md` for selection rules.

## Data Behavior

- Detection and incident caches are versioned, separated by observation window,
  and expire after two hours.
- Incidents load only when selected; do not add a detections-then-incidents
  request waterfall.
- Manual refresh bypasses browser storage but not the API's NASA protection.
- Stale successful data remains visible with its approximate source age.
- Cluster envelopes are observation context, not confirmed incidents or measured
  burned-area boundaries.

## Production Build And Hosting

Run `npm run build:production` to validate the API and Firebase/App Check values
before generating `dist/`. Firebase Hosting serves that directory and rewrites
application routes to `index.html` according to `firebase.json`. `npm run build`
remains available for local and CI compilation without production credentials.

See the root `README.md`, `DEPLOYMENT.md`, and `IMPLEMENTATION_PLAN.md` for the
full architecture, release procedure, and roadmap.
