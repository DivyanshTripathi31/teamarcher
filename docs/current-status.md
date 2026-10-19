# Current status

## Implemented and tested

- Canonical Rust analyzer implemented in `archer-starter/src/analyzer.rs`
- CLI JSON-emitting interface implemented in `archer-starter/src/main.rs`
- Rust test suite passes in the current environment (`35 passed, 0 failed`)
- Release build succeeds for the engine (`cargo build --release --locked`); three dead-code warnings and nine `cargo fmt --check` hunks are pre-existing in the committed baseline
- Backend health endpoint responds successfully
- Backend tests pass for the current project scope (`10 passed, 0 failed` for the verified backend subset)
- Frontend production build succeeds
- Analyzer report UI renders structured Rust findings, peer groups, invariants, route evidence, and the six report summary counts
- Sibling Actix-Web `.service(...)` registrations are traversed with scope context restored between siblings
- Authorization-style free-function calls produce typed role, permission, or ownership evidence; authentication-only calls remain weak identity evidence
- Token-validation and access-log helpers such as `verify_access_token` and `check_access_log` are not promoted to permission checks; `access` counts only as the final word of a check helper (`check_access`, `verify_resource_access`)
- Cross-file handler resolution: every free function is indexed by crate and module path, and each route's handler is resolved through local definitions, explicit/renamed/re-exported imports, unambiguous globs, and module-qualified paths (`handlers::x`, `crate::`, `self::`, `super::`)
- Each route reports additive `handler_path` and `handler_resolution` JSON fields; `Ambiguous` and `Unresolved` handlers carry no evidence, and evidence from same-named functions is never merged
- Nested handler functions resolve within their own lexical block, local bindings (`let`, parameters, closure/loop/match/`if let` patterns, block `const`/`static`) shadow handler names in statement order, and functions declared inside a handler body no longer lend it their evidence
- Controlled integration fixture passes through the current release engine CLI and the authenticated `POST /api/archer/analyze` endpoint (HTTP `200`) for all 16 routes, zero parse errors, three peer groups/invariants, and the single expected `GET /api/admin/payments` finding supported by the users, orders, and reports admin routes; structured API report fields match the CLI (see `docs/testing/archer-integration-test-report.md`, section K). The previous engine version also passed through the browser UI
- Frontend clears old reports at scan start and distinguishes zero routes from failed analysis
- Backend binary selection now prefers the release binary and falls back to debug

## Implemented but not fully verified

- End-to-end application stack using PostgreSQL and MinIO
- Browser UI with the current engine binary: not rerun since the handler-resolution changes
- Deployment and EC2 startup scripts under `deploy/`
- Benchmark artifact validation against actual fixture data

## In progress

- Documentation alignment between the parent project and the canonical engine
- Benchmark artifact audit and historical result reconciliation

## Not implemented

- A separate Python or JavaScript detector reimplementation
- Benchmark artifact directory or expected fixture set in this checkout
- Verified production deployment against live cloud infrastructure in this environment

## Blocked

- Benchmark fixture set not present in the current checkout
- Authorization helper recognition remains a name-based heuristic; arbitrary project-specific helper semantics still require review and must not be inferred from missing evidence
- Handler resolution does not model `use` inside function bodies, macro-generated bindings, `#[path]` modules, `impl`-method handlers, or cross-crate workspace dependencies; calls into helper bodies are not followed

## Current judgment

The current engine passes its expected 16-route integration fixture scenario and admin drift finding through the release CLI and the authenticated analysis API. This is synthetic-fixture validation of a single-file repository, not evidence of real-world accuracy or generalization. Production deployment and broader evidence-recognition behavior remain unverified; lack of recognized evidence must not be reported as proof of missing authorization.
