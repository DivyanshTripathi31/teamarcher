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

### EC2 backend foundation (Phase 1)

The repository includes safe templates for the first EC2 phase:

- `deploy/systemd/teamarcher-backend.service` runs Uvicorn as the non-root `teamarcher` account and binds it only to `127.0.0.1:8000`.
- `deploy/nginx/teamarcher-backend.conf` exposes only `/health` and `/api/` through Nginx on port 80.
- `deploy/teamarcher-backend.env.example` documents the private `/etc/teamarcher/backend.env` file. The real file must remain on the server with restrictive permissions and must never be committed.

For this phase, `GET /health` is intentionally database-independent. If PostgreSQL has not yet been provisioned, the service starts in health-only mode; database-backed routes remain unavailable until the separate PostgreSQL phase. Object storage is likewise disabled until the separate S3 phase supplies real configuration. This is deliberate: do not add placeholder production users, database data, or AWS credentials solely to make the process start.

On the new EC2 host, after cloning the repository and installing `nginx` and `python3-venv`, run the idempotent foundation script as `ubuntu`:

```bash
bash /opt/teamarcher/deploy/phase1-ec2-backend.sh ec2-65-2-74-233.ap-south-1.compute.amazonaws.com
```

It creates the virtual environment, generates the JWT only in `/etc/teamarcher/backend.env` on first run, starts the non-root service, installs the Nginx site, and verifies loopback, Nginx, and public `/health`. It never changes the EC2 security group or opens port 8000/5432.

### RDS database setup (Phase 2)

The existing backend models are now captured in `backend/alembic/` as the initial Alembic migration. On production, application startup uses migrations rather than `create_all`; `DATABASE_AUTO_CREATE=false` is enforced by the Phase 2 script.

After confirming private RDS reachability from EC2 and creating the administrative `teamarcher_admin` role, pull the current checkout and run this **only from the EC2 SSH session**:

```bash
sudo git -C /opt/teamarcher pull --ff-only origin main
bash /opt/teamarcher/deploy/phase2-rds-database.sh your-rds-endpoint.ap-south-1.rds.amazonaws.com
```

The script securely prompts on EC2 for the `teamarcher_admin` password. It confirms TLS, applies Alembic migrations, creates a separate least-privilege `teamarcher_app` role, writes only that application connection URL to `/etc/teamarcher/backend.env`, optionally prompts for the five existing seed-account passwords, restarts the non-root service, and verifies both a real database query and `/health`. Passwords are never printed or added to this repository. It refuses to overwrite an existing unversioned schema or unknown application credential.

## GitHub Pages frontend preparation

The repository includes `.github/workflows/deploy-frontend-pages.yml`, which builds only `frontend/dist` on pushes to `main` and uploads it through the official GitHub Pages Actions workflow. It does not deploy FastAPI, PostgreSQL, MinIO, S3, or authentication infrastructure.

GitHub Actions currently builds Vite with `VITE_BASE_PATH=/teamarcher/`, appropriate for the standard project URL `https://divyanshtripathi31.github.io/teamarcher/`. React Router uses Vite's generated base path, so navigation and refreshes remain inside `/teamarcher/`. The build copies `index.html` to `404.html`, allowing GitHub Pages to serve the React application for direct requests to browser routes such as `/teamarcher/team` and `/teamarcher/presentations/example`.

When registrar verification is complete, switch the workflow's `VITE_BASE_PATH` to `/` before enabling the `teamarcher.in` custom domain. Do not add a `CNAME` file or configure custom-domain DNS until then.

Set the public `VITE_API_BASE_URL` at build time. GitHub Actions is prepared to use `https://api.teamarcher.in`; this is a public API location, not a secret, and it does not require the backend to be live during the static build. Never put credentials or private values in a `VITE_*` variable.

## Browser compatibility

Folder selection uses the browser’s `webkitdirectory` capability, supported by Chromium-based browsers. Dragging a folder itself is not equally consistent across browsers, so the page also provides an explicit **Add folder** control. Unsupported document formats remain downloadable and openable from the in-site viewer; PDFs, images and text display inside the portal.
