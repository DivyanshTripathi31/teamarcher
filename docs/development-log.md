# Development log

## Date: 2026-10-19

### Integration defect fixes

- Updated the Rust route visitor to traverse sibling `.service(...)` receiver chains after restoring the prior scope context; added a regression test for 16 total routes (13 scoped and three attribute routes) across five nested scope families, evidence association, and the admin finding.
- Updated the analysis page to clear old reports when a scan starts, guard duplicate submissions and source changes while busy, and show an explicit loading state.
- Replaced the zero-route assertion with report-driven messaging that distinguishes no routes, absent inventory, and routes without a qualifying peer group; parse error counts are included.
- Direct release engine scan and real API/browser scan of `archer-integration-test-repo`: 16 routes, 1 `/api/admin` peer group, 1 strong invariant, and 1 potential finding for `GET /api/admin/payments`, supported by three `require_admin` routes.
- Failure-state verification: connection-refused rescan clears the prior report. Empty-state verification: malformed and valid no-route repositories produce distinct parse diagnostics and accurate UI copy.
- Rust tests: 18 passed. Locked release build succeeded. Backend tests: 10 passed (44 existing deprecation warnings). Frontend production build passed.
- Remaining limitation: several fixture helpers outside `require_admin` are not recognized as handler authorization evidence; thresholds and evidence rules were not changed.

## Date: 2026-10-19

### Evidence-first analyzer report UI

- Updated `frontend/src/main.tsx` to render the Rust engine's structured finding details, associated invariant and peer group, supporting authorized routes, route handlers, source locations, and evidence mechanisms/symbols.
- Added report counts for files scanned, routes extracted, peer groups, invariants, potential drift findings, and parse errors using API-provided report fields.
- Kept potential drift distinct from confirmed vulnerabilities and distinguished `RouteReference.authorized` from raw route evidence signals.
- FastAPI returns the Rust report structures and normalizes paths; no backend or detector changes were needed.
- Frontend production build: `npm run build` passed. No frontend test script or test files are present.
- Docker services had been started locally, but the complete browser-driven flow was not verified as part of this change.

## Date: 2026-10-18

### Repository audit and integration status

- Confirmed that the checkout is a combined working copy containing both the parent web application and the canonical Rust engine.
- Verified that the canonical detection logic lives in `archer-starter/src/analyzer.rs`.
- Verified the backend integration in `backend/app/main.py` and the frontend consumption in `frontend/src/main.tsx`.
- Confirmed that the repository is in a merge/rebase-in-progress state, but no actual file-level unresolved conflict markers were present in the tracked source files.
- Confirmed the current working tree includes integration edits and the canonical engine changes.

### Verified evidence

- Rust tests: `cargo test --locked` passed with 17 passing tests.
- Rust release build: `cargo build --release --locked` succeeded.
- Backend configuration regression: release binary path precedence was fixed and verified by tests.
- Backend tests: Python backend tests passed in the selected subset.
- Frontend build: `npm run build` succeeded.
- Backend health endpoint: successfully responded with `{"status":"ok"}`.

### Current blockers

- Docker daemons are unavailable in this environment, so the local DB-backed runtime stack cannot be started here.
- Benchmark artifact files such as `expected.json` were not present in this checkout, so historical benchmark values remain unverified in this repository state.

### Next steps

- Run the complete end-to-end local stack once Docker is available.
- Validate the actual analyzer flow through the browser and backend with a real fixture.
- Audit benchmark fixtures and reconcile historical results with the actual artifact set if it is later restored.
- Keep future ARCHER work aligned with the canonical Rust engine and the current integration contract.

## Date: unknown

### Historical project context

- The project originated as a parent web application with a backend and frontend.
- The canonical engine was later incorporated or merged into the working copy as a Rust analysis component.
- Earlier project documentation described a controlled benchmark and a historical result set that is not present in this repository snapshot.

This log will continue to be updated as the implementation status changes. The canonical source of truth remains the current code and the verified test/build results.
