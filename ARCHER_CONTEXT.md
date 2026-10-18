# ARCHER project context

## Purpose

ARCHER is a research tool for detecting potential authorization drift in Rust/Actix-Web applications.

The research question is: "Can repository-local authorization invariants detect authorization drift while reducing false positives compared with simple or manually specified rules?"

ARCHER is not a generic vulnerability scanner and must not automatically classify every route without recognized authorization evidence as a vulnerability. The detector is designed to identify suspicious deviations from a repository's own authorization conventions using evidence from comparable peer routes.

## Repository reality in this checkout

This checkout is a combined working copy, not a pure canonical engine repository.

The repository currently contains:

- a canonical Rust analysis engine under `archer-starter/`
- a parent web application under `backend/` and `frontend/`
- deployment and infrastructure files at the repository root

The backend uses the Rust engine as an external CLI binary and returns the JSON analysis report over HTTP to the frontend. The canonical engine remains the source of truth for detection behavior.

## Actual architecture in this checkout

Current implementation flow:

1. Rust repository input
2. AST-based route extraction
3. Handler-level authorization evidence extraction
4. Nested scope and prefix propagation
5. Structural peer grouping
6. Authorization-invariant inference
7. Potential drift detection
8. Evidence-backed findings returned as JSON
9. FastAPI backend normalizes and returns the report
10. React frontend renders route inventory, evidence, peer groups, invariants, and findings

## Canonical engine details

The canonical engine is implemented in `archer-starter/src/analyzer.rs` and the CLI entry point is `archer-starter/src/main.rs`.

Verified engine capabilities in the current code:

- AST-based route extraction from Rust source
- Nested Actix-Web scope prefix propagation
- Support for attribute routes such as `#[get(...)]` and `#[post(...)]`
- Route source location tracking via line numbers and file paths
- Handler-level authorization evidence capture
- Recognition of guard and middleware patterns used as authorization evidence
- Structural peer grouping based on method, scope, and route shape
- Evidence-backed finding generation with suspicious-route, invariant, and supporting peer routes
- Deterministic traversal of Rust files and graceful handling of malformed Rust files
- Rust unit tests covering peer grouping, authentication exclusions, and drift detection

The project must preserve the canonical engine as the single source of truth for route analysis, peer grouping, and invariant inference. Python and JavaScript should not reimplement the detector logic.

## Report contract

The engine emits a JSON report with the following main sections:

- `files_scanned`
- `parse_errors`
- `routes`
- `peer_groups`
- `invariants`
- `findings`
- `finding_details`

Route and evidence records include file paths, line numbers, route methods, route paths, authorization evidence, and handler names where available.

The backend in `backend/app/main.py` validates the output path, sets `settings.archer_binary`, executes the CLI, parses JSON, and normalizes the file paths back to repo-relative locations before returning the response.

The frontend in `frontend/src/main.tsx` expects the real report fields and renders them as route inventory, peer groups, invariants, findings, and supporting evidence. The UI distinguishes absent authorization evidence from confirmation of authorization absence.

## Research and benchmark context

The project goal is to test whether repository-local authorization invariants can detect authorization drift while reducing false positives compared with naive rule-based checks.

The repository currently does not include benchmark artifacts such as `expected.json` or a benchmark directory. The recorded benchmark values below are historical project numbers that were previously reported in project documentation, but they were not revalidated in this checkout because the artifact set is not present.

Historically reported benchmark values:

- Repositories: 20
- Routes analyzed: 73
- True positives: 5
- False positives: 0
- False negatives: 1
- True negatives: 67
- Precision: 100%
- Recall: 83.33%
- F1: 90.91%
- False positives per 1,000 routes: 0

Known false negative:

- `18_parameter_drift`
- route: `GET /admin/payments/{id}`

The detector did not flag this case because the comparable peer set contained only one authorized peer, which was below the current peer threshold.

These numbers are for a controlled synthetic benchmark and do not prove general real-world performance or superiority over tools such as Semgrep or CodeQL.

## Current implementation status

Implemented and tested:

- Rust core analyzer with route extraction and peer detection
- Rust unit tests covering complete logic paths
- release and debug binary resolution in backend configuration
- backend health endpoint and app startup behavior
- backend tests for storage and upload safety
- frontend production build

Implemented but not fully verified in this environment:

- end-to-end DB-backed local stack with PostgreSQL and MinIO
- full browser-driven flow through the frontend against live backend services
- benchmark artifact verification against the actual repository fixture set

Blocked in this environment:

- Docker daemon unavailable for `docker compose up -d`

## Engineering rules

1. Read this file before substantial ARCHER development.
2. Inspect current Git state and source before making changes.
3. Treat the canonical Rust engine as the authority for detection logic.
4. Do not create duplicate detectors in Python or JavaScript.
5. Preserve existing working frontend behavior and app features.
6. Do not fabricate reports, evidence, benchmark metrics, or tests.
7. Do not weaken detection thresholds or alter ground truth to improve scores.
8. Distinguish no recognized authorization evidence from confirmed absence of authorization.
9. Describe findings as potential drift, not confirmed vulnerabilities.
10. Keep controlled benchmark results separate from live repository analysis.
11. Add regression tests for meaningful changes.
12. Run relevant tests and builds and report actual results.
13. Never commit, push, force-push, or discard work without authorization.
14. Update `docs/current-status.md` and `docs/development-log.md` after meaningful milestones.
15. When integration fails, fix the real incompatibility rather than masking it with mocks or silent fallbacks.

## Relevant repository files

- `archer-starter/src/analyzer.rs`: canonical detection logic
- `archer-starter/src/main.rs`: CLI entry point
- `backend/app/main.py`: backend integration and HTTP API
- `backend/app/config.py`: backend configuration and binary resolution
- `backend/tests/test_storage.py`: storage behavior tests
- `backend/tests/test_upload_safety.py`: upload safety tests
- `frontend/src/main.tsx`: frontend dashboard and API consumer
- `README.md`: deployment and local setup documentation
- `docs/REQUIREMENTS_MATRIX.md`: functional requirement status matrix

## Known limitations and non-goals

- ARCHER is designed for repository-local inference, not universal proof of vulnerability.
- It is not a replacement for a general-purpose security audit.
- The project currently depends on a Rust toolchain and backend runtime being present.
- The local deployment stack requires Docker or equivalent infrastructure for PostgreSQL and MinIO.
- The benchmark artifact set is not present in this checkout, so historical numbers remain unverified here.
