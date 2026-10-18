# Copilot instructions for this repository

## Read this first

Before making substantial ARCHER changes, read `ARCHER_CONTEXT.md`.

## Repository workflow

1. Inspect the current repository state and Git status before editing.
2. Treat the canonical Rust engine in `archer-starter/` as the source of truth for detection logic.
3. Preserve existing frontend behavior, navigation, and unrelated application features.
4. Do not create duplicate implementations of route extraction, peer grouping, or invariant inference in Python or JavaScript.
5. Prefer incremental fixes that address the actual incompatibility.
6. Add regression tests for meaningful logic or integration changes.
7. Run targeted tests/builds and report actual results rather than assumptions.
8. Keep benchmark values separate from live repository analysis results.
9. Describe findings as potential drift, not confirmed vulnerabilities.
10. When evidence is absent, do not claim authorization exists or does not exist without the underlying route evidence.
11. Never commit, push, force-push, or discard existing work without explicit authorization.
12. Update `docs/current-status.md` and `docs/development-log.md` after meaningful milestones.

## Project-specific rules

- Do not fabricate report output, evidence, benchmark metrics, or test results.
- Do not weaken detection thresholds or benchmark ground truth to make tests pass.
- Distinguish “no recognized authorization evidence” from “confirmed absence of authorization.”
- Keep controlled benchmark metrics separate from live repository analysis.
- Preserve public website and admin functionality while integrating the canonical engine.
- When the integration fails, identify the root cause and fix it instead of masking it with mock data or silent fallbacks.

## Relevant directories

- `archer-starter/`: canonical Rust engine
- `backend/`: FastAPI app, API routes, and deployment configuration
- `frontend/`: React app and dashboard UI
- `docs/`: project architecture and status documents
- `deploy/`: production deployment scripts and environment templates

## Required references

- `ARCHER_CONTEXT.md` is the master project context.
- `docs/architecture.md` describes the current architecture.
- `docs/current-status.md` captures current verified status.
- `docs/development-log.md` records milestones and evidence.
