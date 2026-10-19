# ARCHER Integration Test Report

**Run date:** 2026-10-19
**Fixture:** `/Users/vidit/Desktop/archer-integration-test-repo`
**Current assessment:** The fixture's engine → API → UI flow passed after route extraction, UI state, and branch-inspired free-function evidence recognition fixes. After the cross-file handler-resolution and lexical-scoping changes (section K), the current release CLI still extracts all 16 routes, produces finance, manager, and admin peer groups/invariants, and reports the expected `/api/admin/payments` potential drift; the authenticated API/UI rerun with this engine is pending. Historical checkpoints below retain earlier counts. Evidence inference remains heuristic, and identity extraction is not authorization.

Potential drift is a review signal, not proof of exploitability.

## A. Environment

- Application repository: `/Users/vidit/teamarcher`, branch `main`, HEAD `d77127647fd562b8c25a05823a0fc087f1d877bf` (`integrated backend frontend and the archer engine`). Branch status was ahead 1 / behind 1 relative to `origin/main`.
- Engine repository: `archer-starter`, branch `main`, HEAD `59dda67c2bf37694f4d60d86a34748106657a08b` (`Implement initial authorization drift detection`). The engine working tree had local modifications to `.DS_Store`, `Cargo.lock`, `Cargo.toml`, `src/analyzer.rs`, and `src/main.rs`; these were inspected and not edited by this diagnostic.
- The application worktree also had pre-existing modifications and untracked files, including `frontend/src/main.tsx`, `frontend/src/styles.css`, and documentation. No existing work was discarded.
- The workspace reported edits under `examples/archer-detailed-demo/src/`, but those source paths could not be opened at run time. Current directory listings showed `Cargo.lock` and an empty `src/routes/` directory; that demo was not used as a fixture.
- Engine package/CLI version: `archer 0.1.0`.
- Toolchains: `rustc 1.98.1`, `cargo 1.98.1`, `Python 3.14.4`, `Node v24.3.0`, `npm 11.4.2`.
- Backend configuration resolved `ARCHER_BINARY` to `/Users/vidit/teamarcher/archer-starter/target/release/archer`; the direct comparison was run using that release binary after rebuilding it from the current engine source.
- PostgreSQL and MinIO Docker containers were running. FastAPI was started on `127.0.0.1:8000`; Vite was started on `127.0.0.1:5173`.
- The analysis route requires a signed-in ADMIN or INSTRUCTOR whose forced password change is complete. The existing browser session was restored and used; no credentials were reset or bypassed.

### Commands executed

- `cargo run --manifest-path ../archer-starter/Cargo.toml -- --json /Users/vidit/Desktop/archer-integration-test-repo`
- `cargo build --locked --release --manifest-path /Users/vidit/teamarcher/archer-starter/Cargo.toml`
- `/Users/vidit/teamarcher/archer-starter/target/release/archer --json /Users/vidit/Desktop/archer-integration-test-repo`
- Browser upload through the existing `/use` interface to `POST /api/archer/analyze` (multipart `files` and `relative_paths`).
- Authenticated API probes for missing files, traversal paths, a minimal Rust file, malformed Rust, and a missing engine binary.
- `cargo test --locked --manifest-path /Users/vidit/teamarcher/archer-starter/Cargo.toml`
- `.venv/bin/python -m pytest -q` in `backend/`.
- `npm --prefix /Users/vidit/teamarcher/frontend run build`
- `curl -i http://127.0.0.1:8000/health`

An initial Rust and npm test invocation used paths relative to the repository root while the shell was in `backend/`; those attempts failed to locate their manifests/package file. The corrected absolute-path invocations above ran successfully. `cargo run` emitted unused-code warnings but exited successfully.

## B. Direct engine results (pre-fix baseline)

### Fixture scan

The canonical release CLI exited with status `0`; stderr was empty. The earlier `cargo run` debug invocation exited `0` and emitted three existing dead-code warning groups: unused enum variants, unused `Route` methods, and unused `infer_prototype_drift`.

| Report field | Actual value |
|---|---:|
| `files_scanned` | 1 |
| `parse_errors` | 0 |
| `routes` | 5 |
| `peer_groups` | 0 |
| `invariants` | 0 |
| `findings` | 0 |
| `finding_details` | 0 |

Actual extracted routes (all had an empty `authorization` array):

| Method | Path | Handler | Scope prefix | Source |
|---|---|---|---|---|
| GET | `/api/profile` | `profile` | empty | `src/main.rs:65` |
| GET | `/api/public-info` | `public_info` | empty | `src/main.rs:70` |
| POST | `/api/session` | `create_session` | empty | `src/main.rs:74` |
| GET | `/api/public/ready` | `readiness` | `/api/public` | `src/main.rs:109` |
| GET | `/api/public/health` | `health` | `/api/public` | `src/main.rs:108` |

### Comparison with fixture specification

The fixture contains 16 route declarations: 11 ordinary `.route(...).to(...)` registrations in chained nested `.service(...)` calls, plus three attribute routes and two routes in the final public scope. Only five were emitted.

- **Admin nested scope:** expected four GET routes under `/api/admin`; none were extracted. Therefore `/api/admin` prefix propagation for this branch was not exercised successfully.
- **Admin audit method separation:** `POST /api/admin/audit` was not extracted, so its separation cannot be observed in this fixture report. The engine's `drift_finding_excludes_structural_non_peers` Rust unit test passes; peer comparison requires matching methods.
- **Manager, finance, and documents scopes:** all six ordinary registrations in those scopes were absent (two each); together with the four admin GET routes and one admin audit POST, eleven chained registrations were missed.
- **Attribute routes:** `GET /api/profile`, `GET /api/public-info`, and `POST /api/session` were extracted with their handlers and source lines.
- **Public nested routes:** `/api/public/health` and `/api/public/ready` were extracted with the `/api/public` scope prefix. The intended public endpoints were not reported as findings.
- **Authorization evidence:** no evidence was present on any emitted fixture route. In particular, `profile` calls `require_authenticated_user()`, but the current handler-symbol recognition does not classify that helper. The fixture's `require_admin`, `require_manager`, `verify_finance_permission`, and `check_resource_owner` calls are in routes that were not extracted, so their association cannot be evaluated from this fixture report.
- **Primary drift candidate:** `/api/admin/payments`, and all three expected supporting admin peers, were absent. No peer group was formed, so the detector never evaluated the configured peer threshold or generated a finding. This is an upstream route-extraction failure, not evidence that the candidate passed authorization review.



In `RouteVisitor::visit_expr_method_call`, the `service` branch visits the current call's arguments and returns without walking its receiver chain. In the fixture's chained `cfg.service(...).service(...).service(...)` expression, earlier sibling service arguments are therefore skipped; the final public service is visited. `#[get]`/`#[post]` handlers are visited separately, which accounts for the other three extracted routes. Existing nested-scope unit coverage tests a single nested service expression and passes, but does not cover this chained-sibling shape.

### Supplemental real-source probe

To exercise the finding pipeline separately from the fixture extraction failure, a small Rust AST source probe was written under `/tmp/archer-ui-probe/` and analyzed by the actual release binary and actual API. It declared four GET attribute routes with three `require_admin()` calls and one unprotected payments handler; it was not part of the supplied fixture and was not used to score it.

- Direct CLI: exit `0`, 1 Rust file, 4 routes, 1 peer group, 1 invariant, 1 finding, no parse errors.
- Finding: `GET /api/admin/payments`, supported by `/api/admin/users`, `/api/admin/orders`, and `/api/admin/reports`.
- Each supporting route carried `RoleCheck`, mechanism and symbol `require_admin`, strength `Strong`, handler, file, and line.
- Invariant values: 3 of 4 routes authorized, 1 without, evidence pattern `require_admin`, strength `Strong`.
- Since these were attribute routes with empty `scope_prefix`, the engine described the group as `GET static routes under /`. This is the actual structural grouping description and demonstrates that grouping uses route method, scope prefix, segment count, and dynamic-segment shape; it does not imply those routes share a literal `/api/admin` scope.

## C. Backend results (pre-fix baseline)

**Endpoint:** `POST /api/archer/analyze`
**Request:** authenticated multipart upload with `files` and a JSON `relative_paths` array. The fixture upload contained six accepted files (the Cargo manifest, Rust source, README, expected JSON, and two docs).

- Actual fixture request: HTTP `200`.
- Response top-level fields: `files_scanned`, `parse_errors`, `routes`, `peer_groups`, `invariants`, `findings`, `finding_details`, `repository_files`, `repository_bytes`.
- Values matched the direct current-release report for all engine fields: 1 file scanned, 5 routes, 0 parse errors, groups, invariants, and findings.
- The API normalized absolute temporary paths to `archer-integration-test-repo/src/main.rs` and added `repository_files: 6` and `repository_bytes: 7812`. No route, evidence, peer-group, invariant, or finding fields were renamed or dropped. The response contained no temporary upload root or host filesystem path.
- On the supplemental finding probe, the actual API returned the same finding, invariant, and three supporting peers as the direct CLI, with paths normalized relative to the upload root.

Failure and safety probes, all with the real API:

| Probe | HTTP | Observed response |
|---|---:|---|
| No bearer authorization | 401 | `Authentication required` |
| No uploaded files | 422 | FastAPI missing `files` validation detail |
| Relative path `../escape/main.rs` | 422 | `Invalid repository path`; no path disclosure |
| Minimal `fn main() {}` Rust upload | 200 | 1 file scanned, 0 routes, no parse errors or findings |
| Malformed Rust upload `fn broken( {` | 200 | 1 file scanned, 0 routes, one parse error (`cannot parse string into token stream`) |
| Isolated API configured with nonexistent `ARCHER_BINARY` | 503 | `Archer analyzer is not built on the server`; no filesystem path disclosed |

`GET /health` returned HTTP `200` with `{"status":"ok"}`.

## D. Frontend results (pre-fix baseline)

The real UI was opened at `http://127.0.0.1:5173/use` with the existing authenticated browser session.

- **Actual fixture:** rendered all six summary values exactly as returned by the API (`1`, `5`, `0`, `0`, `0`, `0`), all five route rows, full emitted paths/methods, handlers, and normalized source locations. It showed no findings or peer groups because those arrays were empty. This is faithful rendering of an incomplete engine report, not a UI-generated finding.
- **Supplemental finding probe:** displayed the suspicious payments route, source location, expected invariant, observed absence of recognized evidence, peer group, and all three supporting `require_admin` routes. Opening the support disclosure showed each route's handler, file/line, mechanism, symbol, and strength. UI metrics matched the API report.
- **Malformed Rust:** displayed `Parse errors: 1` and the returned relative-file diagnostic; no stale routes/findings from the prior repository remained after selecting the new folder.
- **Successful scans:** browser checks reported no console errors or failed requests. A screenshot of the expanded supplemental finding card was captured by the browser tool during this session; the screenshot tool did not produce a workspace file, so no image artifact is included here.
- **Repeated successful scans:** repeated fixture scans returned the same counts. Changing the selection to the supplemental source and back updated the report and metrics correctly.
- **Failure-state defect:** after a successful fixture scan, the API process was stopped and the same scan was submitted again without changing the selection. The UI showed `Failed to fetch` but retained the previous report, five route rows, and all old metrics. The request failure was `net::ERR_CONNECTION_REFUSED`. Thus a prior result remains visible as though current after a failed rescan.
- **Empty-reasoning copy defect:** the malformed one-file scan returned zero routes, but the UI's no-peer panel said “Archer kept the routes in the inventory”. That statement is inaccurate for this valid report shape. The panel also displays a generic “no meaningful peer group” message, which is fine; the assertion about retained routes is not.
- Non-2xx probes (`401`, `422`, `503`) generated expected browser resource error messages when deliberately called; clean successful scans did not.

## E. Test matrix (pre-fix baseline)

| Check | Status | Evidence |
|---|---|---|
| Direct canonical engine scan completes | PASS | Release CLI exit 0; no stderr |
| Fixture parses without Rust parse errors | PASS | `files_scanned=1`, `parse_errors=[]` |
| All expected route registrations extracted | FAIL | 5 of 16 route declarations emitted; 11 chained `.route` declarations missing |
| `/api/admin` nested routes and prefix preserved | FAIL | No admin routes in report; only the final `/api/public` service branch was extracted |
| `POST /api/admin/audit` extracted separately | FAIL | Route absent in fixture output |
| GET/POST method separation in peer logic | PASS | `drift_finding_excludes_structural_non_peers` Rust test passes; fixture observation itself is unavailable because audit was not extracted |
| Intended fixture admin group/invariant/finding | FAIL | Payments and its three peers are missing before grouping; no finding produced |
| Intentional public routes kept conservative | PASS | Three emitted public routes produced no findings |
| Real API fixture request and schema | PASS | HTTP 200; engine fields match direct report; only path normalization and two upload metadata fields added |
| Invalid path, missing upload, auth, engine error | PASS | 422 traversal, 422 missing files, 401 unauthenticated, 503 missing binary |
| Minimal and malformed repository reports | PASS | Minimal: 200/0 routes; malformed: 200/one parse error |
| UI metrics and route inventory match actual API | PASS | Browser DOM counts match API counts on fixture and supplemental probe |
| UI renders structured finding/supporting evidence | PASS | Actual API and engine produced 1 finding with three authorized peers; UI displayed them |
| UI repeated successful scans avoid stale data | PASS | Same/different/same selection scans updated metrics and rows |
| UI failed rescan clears old report | FAIL | Real connection-refused rescan showed error but retained prior report and metrics |
| UI parse-error display | PASS | One API parse error appeared in count and details |
| UI empty-reasoning statement matches report | FAIL | Zero-route report was described as having routes retained in inventory |
| Rust tests | PASS | `cargo test --locked`: 17 passed, 0 failed |
| Rust release build | PASS | `cargo build --locked --release` succeeded; existing dead-code warnings remain |
| Backend tests | PASS | `pytest -q`: 10 passed; 44 deprecation warnings from FastAPI/Starlette under Python 3.14 |
| Frontend production build | PASS | `npm run build`: TypeScript and Vite succeeded |
| Frontend test suite | NOT TESTED | `frontend/package.json` defines no test script; no frontend test files were found |
| API health | PASS | HTTP 200 `{"status":"ok"}` |
| Full fixture engine → API → UI intended scenario | FAIL | API/UI faithfully show engine's missing admin routes and zero findings |

## F. Defects and limitations (pre-fix diagnosis)

### Route extraction — fixture-impacting defect

- **Observed:** chained `.service()` sibling registrations are skipped by the visitor's early-return traversal; 11 `.route(...)` registrations are absent.
- **Impact:** nested prefix, handler evidence, peer grouping, invariant inference, and drift finding for `/api/admin/payments` cannot occur for the supplied fixture.
- **Reproduction:** run the release CLI against `/Users/vidit/Desktop/archer-integration-test-repo`; inspect the report's five routes and empty group/finding arrays.
- **Smallest proposed fix:** update the route visitor to traverse the service receiver chain as well as each service argument while preserving the correct scope context; add a regression test using this exact sibling-chain shape. No fix was applied pending approval.

### Authorization evidence extraction — supported-name limitation

- **Observed:** the emitted `/api/profile` handler calls `require_authenticated_user()`, but its route evidence is empty. Current symbol recognition explicitly handles `require_admin`, identity types, and names containing role/authorize/permission; this helper name matches none of those patterns. Similar helpers such as `check_resource_owner` and `require_manager` are not demonstrated as recognized by this fixture report.
- **Impact:** even after route traversal is corrected, some fixture handlers may still lack recognized evidence unless their helper naming is supported. `verify_finance_permission` matches the current permission-name rule but its route is currently skipped.
- **Smallest proposed fix:** define and test the intended helper-name recognition contract without weakening peer thresholds. Not changed during this diagnostic.

### Peer grouping / invariant inference — fixture path blocked upstream

- **Observed:** no fixture group or invariant is generated because the intended routes are absent. Current grouping compares equal scope prefix, method, segment count, and dynamic-segment shape; findings require at least two authorized peers and at least one unauthorized route.
- **Impact:** the fixture cannot validate the real nested admin threshold until extraction succeeds. The supplemental attribute-route scan met the threshold, producing 3 authorized peers and 1 potential drift finding.
- **Limitation:** the attribute probe's empty scope prefix caused the actual group description `GET static routes under /`; this is not evidence of correct `/api/admin` scope grouping.

### Frontend rendering/state

- **Stale report on failed rescan:** `ArcherUse.analyze` does not clear `report` before issuing a new request. A failed same-selection rescan leaves old results visible alongside `Failed to fetch`. Recommended small fix: clear the prior report when a scan starts (or otherwise explicitly mark it stale) and test the failure transition.
- **Inaccurate empty-state sentence:** the no-peer panel unconditionally claims routes remain in the inventory, including reports with zero extracted routes. Recommended small fix: make the message conditional on the actual route count and parse errors.

### Backend integration / deployment

- No backend report-contract defect observed. The API invokes the configured release binary, returns real JSON, normalizes fixture file locations, and provides safe 401/422/503 responses.
- No deployment configuration defect blocked this run. PostgreSQL and MinIO were already running; the local API and Vite servers were started for verification.
- Full scoring remains limited by engine extraction and helper-recognition behavior, not a backend substitute or a frontend mock.

## G. Overall assessment (pre-fix)

**The complete intended integration flow did not pass.** The backend and frontend transport/rendering paths work with real engine output, and the structured finding interface was verified against an actual engine-generated finding. However, the supplied fixture's chained Actix-Web service registrations lose eleven routes at extraction, including all four admin GET routes and the audit POST. Consequently the real fixture produces no admin peer group, invariant, or potential drift finding. The UI additionally retains stale reports after failed rescans and has misleading copy for zero-route reports.

No fixture files, expected outcomes, engine thresholds, detector logic, or benchmark ground truth were changed. The diagnostic recommends a focused route-visitor regression fix and two small frontend state/copy fixes; no application code fix was applied here.

## H. Post-route/state-fix verification (before evidence follow-up)

### Changes verified

- `RouteVisitor::visit_expr_method_call` now visits each `.service()` receiver chain after restoring the enclosing scope context. This visits earlier sibling registrations without duplicating routes or leaking scope prefixes.
- A Rust regression test covers 16 total routes (13 scoped registrations across sibling `/api/admin`, `/api/manager`, `/api/finance`, `/api/documents`, and `/api/public` scopes, plus three attribute routes), methods, source handlers, recognized admin evidence, peer grouping, invariant inference, and finding generation.
- A new scan clears the previous report before issuing its request. While busy, the Run button and repository input are disabled, and the output panel shows an analysis-in-progress state.
- The no-reasoning state now distinguishes zero extracted routes, missing route inventory, and extracted routes with no qualifying peer group. Its zero-route explanation includes actual scanned-file and parse-error counts.

### Direct release engine

Command: `/Users/vidit/teamarcher/archer-starter/target/release/archer --json /Users/vidit/Desktop/archer-integration-test-repo`

- Exit status: `0`; stderr empty.
- `files_scanned=1`, `parse_errors=[]`, `routes=16`, `peer_groups=1`, `invariants=1`, `findings=1`, `finding_details=1`.
- All 16 expected method/path pairs from `expected.json` were present.
- Nested scope prefixes were preserved for `/api/admin`, `/api/manager`, `/api/finance`, `/api/documents`, and `/api/public`; the three attribute routes retained their empty `scope_prefix` as expected.
- `POST /api/admin/audit` remained separate from GET peers.
- `GET /api/admin/payments` was the one suspicious route. Its peer group contained the three GET admin routes with `require_admin` evidence.
- Invariant: strong; 3 of 4 routes with authorization evidence, 1 without; pattern `require_admin`.
- Public routes produced no potential drift findings.

### Backend and frontend

- The real authenticated `POST /api/archer/analyze` upload returned HTTP `200`, with all engine report fields preserved, six uploaded repository files, and normalized relative source paths.
- The browser rendered 16 route rows, summary metrics `1 / 16 / 1 / 1 / 1 / 0` (files, routes, peer groups, invariants, potential findings, parse errors), one finding, and all three supporting `require_admin` routes. These values matched the API response.
- A real connection-refused rescan showed `Failed to fetch`, removed the old metrics/report, and left the empty report state visible; no stale result appeared current.
- While a request was held by a browser automation interception, the UI showed “Analysis in progress” and disabled the Run button. The interception did not release to the API and timed out, so this was not counted as an end-to-end delayed-response or duplicate-click test. The form handler also has an explicit `busy` guard, and the button and file input are disabled while busy.
- A malformed one-file scan returned HTTP `200`, zero routes, and one parse error; the UI displayed “No routes were extracted” and correctly reported one scanned Rust file and one parse error.
- A valid one-file `fn main() {}` scan returned HTTP `200`, zero routes, and zero parse errors; the UI distinguished it from a failed request and reported that no parse errors occurred.
- After the controlled outage test, the API was restarted and the fixture was rerun successfully.

### Post-fix test matrix

| Check | Status | Evidence |
|---|---|---|
| Sibling scope route extraction | PASS | Rust regression test and release scan; all 16 fixture routes emitted |
| Nested prefixes and methods | PASS | Five scope prefixes correct; audit is POST and separate from GET peer group |
| Admin peer/invariant/finding | PASS | 1 group, 1 strong invariant, payments finding with 3 supporting peers |
| Authorization evidence association | PASS for admin peers | `require_admin` kind/mechanism/symbol/handler/line preserved on users, orders, reports, and audit |
| Other fixture helper evidence | LIMITATION | `require_manager`, `verify_finance_permission()`, `require_authenticated_user()`, and `check_resource_owner()` remain unrecognized in current handler evidence extraction; no threshold was changed |
| Real API and UI fixture scan | PASS | HTTP 200; response, metrics, routes, finding, and support routes match |
| Failed rescan stale-state check | PASS | Actual API outage produced error with no prior report or metrics remaining |
| Loading state and repeated-submit guard | PASS (state/guard) | Busy state and disabled button observed; `busy` guard prevents a second analysis handler from starting. Delayed-response duplicate-click automation was not completed because the browser route interception did not release the request. |
| Zero-route malformed/valid states | PASS | Both showed zero routes; parse-error diagnostics differentiated the cases from each other and from request failure |
| Rust tests | PASS | 18 passed, 0 failed |
| Rust release build | PASS | `cargo build --locked --release` succeeded; existing dead-code warnings remain |
| Backend tests | PASS | 10 passed; 44 existing FastAPI/Starlette deprecation warnings under Python 3.14 |
| Frontend production build | PASS | `npm run build` passed |

The remaining evidence-recognition limitation is not evidence that those fixture routes are protected or unprotected; it means the engine did not recognize those helper forms. No authorization helper heuristic or peer threshold was changed in this fix.

## I. Overall assessment after route/state fixes

The route traversal and frontend state/empty-state fixes passed through the real release engine, FastAPI endpoint, and React interface. That checkpoint still had limited free-function evidence recognition. No fixture, expected output, benchmark ground truth, or detection threshold was changed.

## J. Branch-inspired call-evidence follow-up

Commit reviewed: `05561a31d8fc34ff4d936bc27bcec5b80837aa29` on `origin/feature/archer-improvements`. Its free-function authorization-name recognition and negative tests were adapted into the published engine's typed evidence model; its string-valued report schema was not copied.

- Free-function `check_permission` and `verify_finance_permission` calls now emit `PermissionCheck`/`Strong` evidence.
- `require_manager` emits `RoleCheck`/`Strong`; `check_resource_owner` emits `OwnershipCheck`/`Medium`.
- `require_authenticated_user` emits `IdentityExtraction`/`Weak` and is not considered authorization by `Route::is_authorized()`.
- Names such as `admin_dashboard_title` and error-only/error-match code produce no authorization evidence.
- No thresholds or peer-group rules changed.
- Rust suite: 19 passed; release build succeeded. Backend suite: 10 passed (44 existing deprecation warnings). Frontend build succeeded.
- Live fixture API/UI scan: HTTP 200; 16 routes, 3 peer groups, 3 invariants, 1 finding, no parse errors. Browser showed 16 route rows, the corresponding summary counts, and three supporting admin routes.
- Remaining limitation: helper names are lexical heuristics, not proof of implementation semantics. Unrecognized names remain “no recognized evidence,” not confirmed absence of authorization.

## K. Cross-file handler resolution and lexical-scoping verification

Engine changes on top of engine commit `8e85c3f`: access-helper classification, cross-file handler resolution, nested-handler block scoping, nested-function evidence isolation, and local-variable shadowing. Backend and frontend code were not changed.

### Direct release engine

Command: `/Users/vidit/teamarcher/archer-starter/target/release/archer --json /Users/vidit/Desktop/archer-integration-test-repo` after `cargo build --release --locked`.

- Exit status: `0`.
- `files_scanned=1`, `parse_errors=[]`, `routes=16`, `peer_groups=3`, `invariants=3`, `findings=1`, `finding_details=1`.
- Handler resolution: 13 `Local` (ordinary registrations in `src/main.rs`) and 3 `Definition` (attribute routes).
- Peer groups: `/api/finance` GET (2/2 authorized, `verify_finance_permission`), `/api/manager` GET (2/2, `require_manager`), `/api/admin` GET (3/4, `require_admin`, strong).
- Finding: `GET /api/admin/payments` (`src/main.rs:87`) with no recognized evidence, supported by `GET /api/admin/users` (line 10), `GET /api/admin/orders` (line 14), and `GET /api/admin/reports` (line 18), each `RoleCheck` `require_admin`.
- `expected.json`: the primary drift candidate and its three expected peers match; no intentional public route was reported.
- The JSON report equals the committed-baseline engine's report apart from the two additive per-route fields `handler_path` and `handler_resolution`. The text CLI output is unchanged.

### Engine test and build results

| Check | Status | Evidence |
|---|---|---|
| Rust tests | PASS | `cargo test --offline --locked`: 35 passed, 0 failed |
| `cargo check` | PASS | `cargo check --offline --locked` succeeded; three dead-code warnings identical to the committed baseline |
| Rust release build | PASS | `cargo build --release --locked` succeeded |
| Formatting | PRE-EXISTING FAILURE | `cargo fmt --check` reports nine hunks; the same nine are present in committed engine commit `8e85c3f`; none were introduced and unrelated code was not reformatted |
| Cross-file, qualified, imported, renamed, re-exported, and glob handlers | PASS | Multi-file regression tests resolve evidence to the defining file and line |
| Ambiguous, unresolved, and duplicate handlers | PASS | Tests confirm no evidence is attached and same-named evidence is never merged |
| Nested-handler scoping and local-variable shadowing | PASS | Tests cover forward declarations, sibling isolation, shadowing of module-level handlers, statement order, and scope restoration; behavior was checked against `rustc` with offline `actix-web 4.17.0` scratch crates |
| Authenticated API with current engine | PASS | HTTP `200`; all engine report fields match the release CLI after path normalization, except the pre-existing `findings` text-path cosmetic difference below |
| Browser UI with current engine | NOT TESTED | Not rerun for this engine version |

### Authenticated API run

Run 2026-10-19 17:34 IST against the running local API (`127.0.0.1:8000`, unchanged since before the engine rebuild; not restarted). The backend resolved `archer-starter/target/release/archer` built from engine commit `118d2b7` (`ARCHER_BINARY` not overridden). The session token was obtained by the account owner through `POST /api/auth/login` in their own terminal and passed to curl as a header file; no credential or token was printed or logged, and the header file was deleted after the request. Unauthenticated requests still return `401`.

- Request: the documented multipart upload of `Cargo.toml` and `src/main.rs` with `relative_paths=["Cargo.toml","src/main.rs"]`.
- Response: HTTP `200` in 0.05 s, 11,081 bytes; top-level fields `files_scanned`, `parse_errors`, `routes`, `peer_groups`, `invariants`, `findings`, `finding_details`, `repository_files`, `repository_bytes`.
- Summary: `16 routes; 0 parse errors; 3 groups; ['GET /api/admin/payments'] ['/api/admin/orders', '/api/admin/reports', '/api/admin/users']`, matching the expected output.
- The single finding is `GET /api/admin/payments` (`src/main.rs:87`), supported by the three authorized admin peers with `require_admin` evidence; every route carries the additive `handler_path` and `handler_resolution` fields (`Local` or `Definition`).
- Upload metadata: `repository_files: 2`, `repository_bytes: 4193`.
- Comparison with the release CLI (`archer --json` on the fixture, with CLI paths made relative to the fixture root): every structured field (`files_scanned`, `parse_errors`, `routes`, `peer_groups`, `invariants`, `finding_details`, including evidence, lines, handlers, and resolution kinds) is identical, and structured paths are normalized to `src/main.rs`.
- One difference: in the human-readable `findings` text, the API shows `/src/main.rs:87` (leading slash) where the CLI shows the fixture path. `backend/app/main.py` removes the temporary upload root from each `findings` string and then strips only the string's leading slash, so embedded paths keep `/`. This line predates the engine changes (`d771276`). It does not affect structured fields, and the response contained no temporary-root or host filesystem path.

The procedure below can be reused to rerun the check.

The analysis route requires a bearer token for an `ADMIN` or `INSTRUCTOR` account whose forced password change is complete. A token comes from `POST /api/auth/login` (`{"username": ..., "password": ...}` → `access_token`, valid for `JWT_EXPIRE_MINUTES`, default 480) or, in a signed-in browser session, from `localStorage.getItem('token')` on the application origin. With the local API on `127.0.0.1:8000`, the backend resolves the release binary above because `ARCHER_BINARY` is not overridden.

```bash
ARCHER_TOKEN=$(python3 -c '
import getpass, json, urllib.request
tty = open("/dev/tty", "r+"); tty.write("Username: "); tty.flush(); username = tty.readline().strip()
password = getpass.getpass("Password: ")
request = urllib.request.Request("http://127.0.0.1:8000/api/auth/login", json.dumps({"username": username, "password": password}).encode(), {"Content-Type": "application/json"})
print(json.load(urllib.request.urlopen(request))["access_token"])')

cd /Users/vidit/Desktop/archer-integration-test-repo
curl -sS -X POST http://127.0.0.1:8000/api/archer/analyze -H "Authorization: Bearer $ARCHER_TOKEN" \
  -F 'relative_paths=["Cargo.toml","src/main.rs"]' -F files=@Cargo.toml -F files=@src/main.rs \
  | python3 -c 'import json, sys; r = json.load(sys.stdin); f = r["finding_details"]; print(len(r["routes"]), "routes;", len(r["parse_errors"]), "parse errors;", len(r["peer_groups"]), "groups;", [x["suspicious_route"]["method"] + " " + x["suspicious_route"]["path"] for x in f], sorted(p["path"] for x in f for p in x["authorized_peer_routes"]))'
```

Expected output, matching the direct release CLI: `16 routes; 0 parse errors; 3 groups; ['GET /api/admin/payments'] ['/api/admin/orders', '/api/admin/reports', '/api/admin/users']`.

### Assessment

The current engine reproduces the fixture's expected routes, groups, invariants, and single admin drift finding through the release CLI and the authenticated `POST /api/archer/analyze` endpoint, with no change to thresholds, fixture files, or expected outcomes. The browser check for this engine version was not rerun. This fixture is a synthetic single-file repository; passing it does not establish accuracy or generalization on real-world Actix-Web applications.
