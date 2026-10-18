# Architecture

## Scope

This repository is a combined working copy that contains both the parent application and the canonical ARCHER engine. The actual behavior is defined by the current code, not by assumptions from earlier repository history.

## Current module map

### Canonical engine

- `archer-starter/src/analyzer.rs`
  - route extraction
  - authorization evidence extraction
  - peer grouping
  - invariant inference
  - drift detection
  - report model definitions
- `archer-starter/src/main.rs`
  - CLI entry point
  - JSON output mode for machine-readable reports

### Backend

- `backend/app/main.py`
  - FastAPI service
  - analysis endpoint `/api/archer/analyze`
  - health checks
  - project and admin routes
- `backend/app/config.py`
  - settings and default resolver for the ARCHER binary
- `backend/app/storage.py`
  - object storage abstraction
- `backend/app/models.py`
  - database metadata models
- `backend/app/security.py`
  - JWT and password handling

### Frontend

- `frontend/src/main.tsx`
  - React Router app
  - analysis page, dashboard, admin pages, archive pages
  - report rendering and API handling
- `frontend/src/siteContent.ts`
  - public site content fallback
- `frontend/src/styles.css`
  - site styling

## Runtime data flow

User → React frontend → FastAPI backend → Rust CLI → JSON report → backend normalization → frontend dashboard

### Intended flow

- the user uploads a Rust repository or folder snapshot through the analysis page
- the frontend packages the upload into multipart form data
- the backend validates file types and paths
- the backend resolves the configured `ARCHER_BINARY`
- the backend executes the Rust CLI with JSON mode
- the Rust engine analyzes the repo and emits JSON
- the backend normalizes file paths relative to the uploaded repo
- the frontend consumes the report and renders the inventory and findings

## Actual report schema

The canonical engine currently defines the report model in `archer-starter/src/analyzer.rs`.

The JSON contract includes:

- `files_scanned`: number of Rust files scanned
- `parse_errors`: parse diagnostics and skipped files
- `routes`: extracted route entries with method, path, scope, handler, evidence, file, and line
- `peer_groups`: grouped route sets with route references
- `invariants`: inferred authorization patterns for each peer group
- `findings`: formatted human-readable drift messages
- `finding_details`: structured drift records with suspicious route, evidence, peer routes, and invariant

The frontend consumes these fields in `frontend/src/main.tsx` and renders them conditionally when present.

## Backend integration contract

The relevant endpoint is:

- `POST /api/archer/analyze`

Behavior:

- accepts multipart upload with file list and optional relative path metadata
- rejects empty uploads
- validates path safety and file types
- verifies the engine binary exists and is executable
- executes the binary with `--json` and the temporary repo root
- parses JSON, normalizes file paths, and returns the report to the client
- returns structured HTTP errors for invalid input, timeout, malformed output, and missing engine binary

## Deployment architecture

This repository expects a standard deployment layout:

- frontend served as static files or Vite build output
- FastAPI backend served behind Nginx or a reverse proxy
- PostgreSQL for metadata storage
- S3-compatible object storage for files
- Rust engine built as a release binary for backend integration

The deployment configuration is defined in:

- `docker-compose.yml`
- `Makefile`
- `README.md`
- `deploy/`

## Intended but not yet fully verified

These are intended architecture decisions that are not fully verified in this environment:

- local Docker-based PostgreSQL and MinIO stack for the full application
- real browser-driven analysis flow against the live API stack
- production EC2 / Nginx / S3 deployment sequence
- benchmark artifact validation against a real benchmark fixture directory

## Compatibility notes

- The engine is the source of truth for detection behavior.
- The backend is a wrapper around the engine and not a replacement for it.
- The frontend is a renderer and consumer of the JSON report.
- The app as a whole is a combined web application and research engine; it is not just a frontend-only site.
