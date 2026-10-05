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
npm run test:e2e
npm run lint
npm run build
npm run preview
```

Vite loads its configuration natively and keeps its disposable transform cache
in the operating-system temporary directory. This avoids Windows/OneDrive file
locks inside `node_modules` without changing application behavior.
If OneDrive has also locked an old `dist/`, set `VITE_OUT_DIR` to an absolute
temporary directory for local build verification; CI and ordinary checkouts
continue to use `dist/`.

`npm run test:smoke` runs the small set used by ordinary pull requests. `npm
test` runs the Node unit suite and jsdom component/accessibility suite and is
reserved for very important frontend changes and releases. Install the Playwright
browser once with `npx playwright install chromium`; `npm run test:e2e` then runs
the browser keyboard checks. See the root `TESTING.md` for selection rules.

## Data Behavior

- Detection and incident caches are versioned, separated by observation window,
  and expire after two hours.
- Incidents load when selected or when manual refresh explicitly updates both
  layers; normal page loading does not create a detections-then-incidents
  request waterfall.
- Manual refresh updates both layers and bypasses browser storage, but not the
  API's NASA protection.
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
