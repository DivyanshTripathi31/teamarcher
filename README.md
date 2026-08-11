# Archer Software Engineering Lab Portal

A deployable MVP for a university software engineering project: a public project site plus a protected interface for uploading, publishing, and retaining immutable presentation versions.

## Architecture

`Browser → React/Vite frontend → FastAPI REST API → PostgreSQL (metadata) + S3-compatible object storage (files)`

The frontend is independently buildable and communicates only with the API. The backend owns authentication, role checks, validation, database records, and S3 uploads. Files never enter Git or PostgreSQL.

## Stack

- Frontend: React, TypeScript, Vite
- Backend: Python, FastAPI, SQLAlchemy
- Database: PostgreSQL
- Storage: AWS S3 or any S3-compatible service (MinIO locally)
- Auth: Argon2 password hashes and signed, expiring JWT bearer tokens

## Local setup

Prerequisites: Python 3.11+, Node 20+, Docker Desktop.

If Docker Desktop is not available, MinIO can also run directly as a local S3-compatible development server. Download the official binary for your architecture, start it bound to `127.0.0.1:9000`, and set the S3 endpoint and matching credentials in `backend/.env`. The current local development environment uses this approach.

1. Create a root `.env` file containing non-default local `POSTGRES_PASSWORD`, `MINIO_ROOT_USER`, and `MINIO_ROOT_PASSWORD` values. This file is ignored by Git. Then start local PostgreSQL and MinIO:

   ```bash
   docker compose up -d
   ```

2. Configure the backend. Copy `backend/.env.example` to `backend/.env`. Set a unique `JWT_SECRET`. For initial account seeding, set `SEED_INITIAL_USERS=true` and supply a JSON mapping in `INITIAL_USER_PASSWORDS_JSON`, for example `{"1024030283":"temporary-password"}`. Include every listed account, then set `SEED_INITIAL_USERS=false` after the first start. Do not commit this file.

3. Create a virtual environment and run the API:

   ```bash
   cd backend
   python -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   uvicorn app.main:app --reload
   ```

   The API creates its minimum schema on startup and will create the configured S3/MinIO bucket when the first file is uploaded. Interactive API docs are at `http://localhost:8000/docs`.

4. Run the frontend in another terminal:

   ```bash
   cd frontend
   cp .env.example .env
   npm install
   npm run dev
   ```

   Open the displayed local Vite URL, normally `http://localhost:5173`.

## Environment variables

Backend values are documented in `backend/.env.example`:

- `DATABASE_URL` — PostgreSQL SQLAlchemy URL
- `JWT_SECRET` — long, random production secret
- `CORS_ORIGINS` — comma-separated permitted frontend origins
- `S3_BUCKET`, `AWS_REGION`, `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY` — object storage configuration
- `S3_ENDPOINT_URL` — set for MinIO/other compatible storage; omit for AWS S3
- `SEED_INITIAL_USERS`, `INITIAL_USER_PASSWORDS_JSON` — one-time secure initial-user bootstrap only
- `MAX_UPLOAD_MB` — server-enforced file size limit

For AWS, create a private bucket and an IAM principal whose permissions are restricted to `s3:PutObject`, `s3:GetObject`, and `s3:HeadBucket` on that bucket. Do not make the bucket public: download access is delivered by short-lived presigned URLs.

## Updating public website copy

The public project name, description, team roles, and current placeholder text are intentionally editable without an admin login in `frontend/src/siteContent.ts`. This keeps normal project copy changes simple and reviewable in Git. Admin login is required only for protected operational data: profile settings and presentation uploads/publishing. Planning V1’s required section structure is in `frontend/src/main.tsx`.

## Initial users

Initial identifiers are uppercase full names (for example, `DIVYANSH TRIPATHI` and `SUKHPAL SINGH`). Their supplied IDs are temporary passwords only and must be changed after first login. The seed script contains names and roles only; it deliberately contains no passwords. Provide temporary passwords through the environment JSON, never source control. The four student accounts are ADMIN. The instructor is INSTRUCTOR and can upload/publish and manage their profile, but cannot edit public site content.

## Upload and version workflow

1. Sign in and change the temporary password.
2. Use **Add files / folder** to drag files, select files, or select a folder. Folder uploads preserve safe relative paths.
3. Enter complete metadata and choose **Publish to the archive**. The API validates every type, filename, relative path, size and the unique title/version pair, then uploads files to S3.
4. Only after successful storage it writes a database record; the dashboard then publishes it.
5. A published version gets a stable public route: `/presentations/{title-version}`.

The unique `(title, version)` constraint prevents overwriting an old version. Published pages include an in-site file browser and preview PDFs, images and text files in the document stage. Publishing only changes the new record’s published state; there are no normal delete or replace endpoints.

## API

- `POST /api/auth/login`, `GET /api/auth/me`
- `PATCH /api/users/me`, `POST /api/users/me/password`
- `GET /api/presentations`, `GET /api/presentations/{slug}`
- `POST /api/presentations/upload`, `POST /api/presentations/{id}/publish`
- `GET /api/admin/dashboard`
- `GET /api/site-content`, `PATCH /api/admin/site-content`

## Deployment on a normal server

Build the frontend with `npm run build`, serve `frontend/dist` from Nginx, and proxy `/api` to a Gunicorn/Uvicorn FastAPI process running under systemd. Use managed or self-hosted PostgreSQL, an S3 bucket, HTTPS certificates at Nginx, a dedicated non-root service account, and production-only environment values in a protected systemd environment file. Point `CORS_ORIGINS` at the deployed site URL. This project does not rely on Vercel, Render, Firebase, Supabase, or GitHub Pages.

## GitHub Pages frontend preparation

The repository includes `.github/workflows/deploy-frontend-pages.yml`, which builds only `frontend/dist` on pushes to `main` and uploads it through the official GitHub Pages Actions workflow. It does not deploy FastAPI, PostgreSQL, MinIO, S3, or authentication infrastructure.

The Vite base path is `/`, appropriate for the future custom domain `teamarcher.in`. Do not add a `CNAME` file or configure the custom domain/DNS until the team is ready. The build copies `index.html` to `404.html`, allowing GitHub Pages to serve the React application for direct requests to browser routes such as `/team` and `/presentations/example`.

Set the public `VITE_API_BASE_URL` at build time. GitHub Actions is prepared to use `https://api.teamarcher.in`; this is a public API location, not a secret, and it does not require the backend to be live during the static build. Never put credentials or private values in a `VITE_*` variable.

## Browser compatibility

Folder selection uses the browser’s `webkitdirectory` capability, supported by Chromium-based browsers. Dragging a folder itself is not equally consistent across browsers, so the page also provides an explicit **Add folder** control. Unsupported document formats remain downloadable and openable from the in-site viewer; PDFs, images and text display inside the portal.
