# RecoverAI — Frontend

React + Vite interface for the RecoverAI recovery agent.

## Running

```bash
npm install
npm run dev
```

The API base URL comes from `VITE_API_BASE_URL`. Without it the app falls
back to `http://127.0.0.1:8000`, which is the local backend.

For a production build, set the variable first — it is baked into the
bundle at build time, not read at runtime:

```bash
VITE_API_BASE_URL=https://your-backend npm run build
```

## Checks

```bash
npm run lint
npm run build
```

## What the interface shows

Every figure is read from the backend. Nothing on the dashboard is
hardcoded: the revenue totals come from recovery outcomes, the risk
bands from stored risk assessments, the guardrails from
`GET /recovery-policy`, and the activity feed from audit events.

Recovery execution is a **test simulation** — no payment provider is
contacted. The interface labels it as such wherever results are shown.