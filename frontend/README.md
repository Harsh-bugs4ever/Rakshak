# Rakshak frontend

The Emergency and Aftermath screens are implemented with responsive layouts,
keyboard focus states, immediate bundled triage guidance, saved checklist
progress, FAQ search, resource filters, and grounded assistant answers with steps and citations.

## Run

```powershell
cd frontend
npm install
npm run dev
```

Open http://localhost:3001. The root redirects to Emergency.
To use the SAM backend, run it on port 3000 or configure
`NEXT_PUBLIC_API_BASE` in `.env.local` before starting Next.js.

```powershell
npm run typecheck
npm test
npm run build
```

## Behaviour

The lightweight frontend tests require Node.js 22.6 or newer.

- Emergency content renders without waiting for the API. Selecting No or Not
  sure uses the critical protocol. Switching answers discards stale responses.
- Geolocation is requested on entry. Sharing uses the native share sheet, then
  SMS when unavailable. Without location permission, add a landmark manually.
- Triage is saved in sessionStorage; checklists use localStorage. Browser storage
  failures do not prevent interaction. Checklist selections stay on this device.
- Aftermath checklists, FAQs and the sample resource directory are bundled from
  the repository data. Successful API responses replace fallback results.
- Sample directory entries are reference data; availability is not live.
- The AI endpoints return reference guidance and citations. Local Strands can
  optionally match a retrieved FAQ. Network failures show the unavailable state.
- Production builds save both screens and their static assets through a versioned
  service worker. Wait for the saved-for-offline status before disconnecting.
  Development mode does not register a service worker.

## Manual checks

1. Start without the API: both screens remain usable and show saved data labels.
2. Select Yes, No and Not sure. Confirm the right steps and separate warnings.
3. Reload Emergency and confirm the triage selection returns.
4. Tick checklist items, reload Aftermath, and confirm progress returns.
5. Search an FAQ, expand its answer, and try a query with no matches.
6. Filter resources by type, state and city; clear filters to restore results.
7. Deny location permission and confirm sharing still has usable text.
8. Submit a question without the backend and confirm the unavailable state.
9. Check keyboard navigation and narrow mobile layouts in light and dark modes.

10. Run a production build, wait for the offline status, disconnect, reload both
    screens, and confirm saved progress and triage still work.

Browser smoke test (requires Playwright and a production server):

```powershell
node tests/browser-smoke.cjs
```

Set `BROWSER_CHANNEL=msedge` to use an installed Edge browser instead of a
Playwright browser download. `PLAYWRIGHT_MODULE` can point to a provided
Playwright runtime. Screenshots are written to ignored `artifacts/`.
