# Development log

## Date: 2026-10-19

### Authenticated API integration with the current engine

- Ran the documented section K procedure against the running local API (not restarted), which resolved the release binary built from engine commit `118d2b7`. The account owner obtained the session token through the normal `POST /api/auth/login` flow; no credential or token was printed or logged, and the temporary header file was deleted after use.
- `POST /api/archer/analyze` with `Cargo.toml` and `src/main.rs` returned HTTP `200`: 16 routes, 0 parse errors, 3 peer groups, and exactly one potential finding, `GET /api/admin/payments`, supported by `/api/admin/users`, `/api/admin/orders`, and `/api/admin/reports` (`require_admin`).
- All structured report fields matched the release CLI after path normalization. The one difference was a pre-existing leading slash on embedded paths in the human-readable `findings` text (`/src/main.rs:87`); no temporary-root or host path was exposed.
- This is synthetic-fixture validation of a single-file repository, not evidence of real-world accuracy or generalization. The browser UI was not rerun for this engine version.

## Date: 2026-10-19

### Cross-file handler resolution and lexical scoping

- Evidence classification: `access` now counts as a permission subject only as the final word of a check helper, so `verify_access_token` and `check_access_log` produce no authorization evidence while `check_access`, `verify_resource_access`, and `check_permission` remain `PermissionCheck`/`Strong`.
- Cross-file resolution: the engine now parses every file, indexes all free functions (including ones without evidence) by crate and Cargo module path, then resolves each `.to(...)` handler through local definitions, explicit/renamed/grouped/`self` imports and re-exports, unambiguous globs, and qualified paths. Previously evidence was looked up by bare name within the registering file only, so handlers in other files contributed nothing and same-named functions could overwrite each other.
- Each route now reports additive `handler_path` and `handler_resolution` fields (`Definition`, `Local`, `Imported`, `GlobImported`, `Qualified`, `UniqueName`, `Ambiguous` with candidates, `Unresolved`). Ambiguous and unresolved handlers carry no evidence. The `UniqueName` fallback applies only when path rules find nothing and exactly one compatible definition exists in the crate. `handler` now holds the last segment of qualified paths instead of `null`.
- Nested functions declared in a block resolve only within that block (including before their declaration); siblings never share them, duplicates are `Unresolved`, and function-local modules do not see enclosing block items. This fixed a case where a nested unprotected `health` borrowed a protected module-level `health`'s evidence.
- Local bindings now shadow handler names in lexical and statement order: `let` (after its statement), function/closure parameters, `for`/`match`/`if let`/`while let` patterns, and block `const`/`static`. A shadowed name is `Unresolved` and never reaches the index or the `UniqueName` fallback. Before this, eight compiled shadowing forms attached a protected module-level handler's evidence to unprotected routes.
- Functions, `impl` methods, and `trait` methods declared inside a handler body no longer lend it their evidence. A handler that calls such a helper with an unrecognized name now has no recognized evidence, because calls are not followed.
- Shadowing and nested-handler behavior was checked against Rust's actual rules with offline `actix-web 4.17.0` scratch crates (compile-error oracles for statement order, inner-item precedence, closures, parameters, and block constants).
- Validation: `cargo test --offline --locked` 35 passed; `cargo check --offline --locked` and `cargo build --release --locked` succeeded. The three dead-code warnings and nine `cargo fmt --check` hunks are identical in the committed baseline and were not reformatted. Each new safeguard was mutation-checked in a scratch copy.
- Release CLI scan of `archer-integration-test-repo`: 16 routes, 0 parse errors, 3 peer groups/invariants, 1 potential finding for `GET /api/admin/payments` supported by `/api/admin/users`, `/api/admin/orders`, and `/api/admin/reports` (`require_admin`). The JSON matches the previous engine apart from the two additive fields.
- Not verified: the authenticated `POST /api/archer/analyze` run with this binary is pending a valid admin/instructor session; an unauthenticated request returned `401 Authentication required`. Backend and frontend code were not changed and their suites were not rerun.
- Remaining limitations: `use` inside function bodies, macro-generated bindings, `#[path]` modules, `impl`-method handlers, cross-crate workspace dependencies, and scope-level `.wrap(...)` after routes are not modeled. The fixture is synthetic and single-file; it does not establish real-world accuracy or generalization.

## Date: 2026-10-19

### Adapt branch authorization-call idea

- Reviewed engine commit `05561a31d8fc34ff4d936bc27bcec5b80837aa29`. Adapted its free-function call-name recognition and negative-test intent into the current typed `AuthEvidence` model instead of importing its string-only report schema.
- Free-function calls now recognize role helpers (`require_manager`), permission helpers (`check_permission`, `verify_finance_permission`), ownership helpers (`check_resource_owner`), and explicit authorization checks. `require_authenticated_user` remains `IdentityExtraction` with weak strength and does not satisfy `Route::is_authorized()`.
- Added regression coverage for these evidence kinds and for benign admin-looking names plus error-only/error-match handlers; thresholds and peer logic are unchanged.
- Rebuilt fixture result through direct CLI and live API/UI: 16 routes, 3 peer groups/invariants (finance, manager, admin), 1 potential finding for `GET /api/admin/payments`; browser counts and supporting admin peers matched the API.
- Validation: Rust tests 19 passed; locked release build, backend tests (10 passed, 44 existing deprecation warnings), and frontend production build passed.

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
