# LedgerLoop web dashboard

This is the React/Vite version of LedgerLoop. The original Streamlit app remains
available from the repository root and is not replaced by this frontend.

## Run locally

```powershell
cd web
npm install
npm run dev
```

For a production build:

```powershell
npm run build
npm run preview
```

The dashboard currently runs in hybrid-demo mode: it uses the same C28 synthetic
fixture and reproduces the core balance, ageing, dispute, state, and priority
views in the browser. The UI keeps its data access behind the calculation layer
so a Python API adapter can be introduced later without replacing the dashboard.

All data is synthetic. Drafts are review-only and the web app does not send
messages, auto-apply receipts, or claim recovered cash.
