# Instructor Requirements Matrix

| Instructor Requirement | Implementation | Relevant Files | Status |
|---|---|---|---|
| Public website, navigation, project and team | React public routes and responsive navigation | `frontend/src/main.tsx` | Complete |
| Known team members and editable roles | Four supplied names; role placeholders | `frontend/src/main.tsx` | Complete |
| Planning Presentation V1 content and Gantt structure | Public editable outline with required sections and timeline | `frontend/src/main.tsx` | Complete (content placeholders by design) |
| Separate, database-driven presentation versions | Presentation table, list and permanent slug routes | `backend/app/models.py`, `backend/app/main.py` | Complete |
| Immutable version history | Unique title/version constraint; no replacement/delete API | `backend/app/models.py`, `backend/app/main.py` | Complete |
| Admin/instructor authentication and authorization | Argon2, expiring JWT, role dependency on protected routes | `backend/app/security.py`, `backend/app/main.py` | Complete |
| Five initial accounts without committed passwords | Environment-driven one-time account seed | `backend/app/seed.py`, `backend/.env.example` | Complete |
| Forced first-password change | `must_change_password` user field and dashboard warning | `backend/app/models.py`, `frontend/src/main.tsx` | Complete |
| Profile and password management | Protected profile and password endpoints/forms | `backend/app/main.py`, `frontend/src/main.tsx` | Complete |
| Real drag/drop upload and metadata validation | Browser form + multipart FastAPI upload endpoint | `frontend/src/main.tsx`, `backend/app/main.py` | Complete |
| Safe type, size, filename validation | Extension allowlist, basename handling, byte limit | `backend/app/main.py` | Complete |
| Actual object storage | S3 client abstraction and `put_object` before DB commit | `backend/app/storage.py`, `backend/app/main.py` | Complete (requires storage configuration) |
| Database metadata | PostgreSQL SQLAlchemy data model | `backend/app/models.py` | Complete |
| Publish only after upload | Storage upload precedes record creation; separate publish endpoint | `backend/app/main.py` | Complete |
| Public download/access | Public metadata endpoint with short-lived S3 URL | `backend/app/main.py`, `backend/app/storage.py` | Complete |
| Frontend/backend/database/storage separation | Four independent layers and compose local services | `frontend/`, `backend/`, `docker-compose.yml` | Complete |
| Deployment readiness and documentation | Standard server deployment instructions | `README.md` | Complete |
| Secrets and generated artifacts excluded | Git ignore and environment examples | `.gitignore`, `backend/.env.example` | Complete |
| Folder / multi-file upload | Browser folder picker, multi-file handling, preserved safe relative paths and asset records | `frontend/src/main.tsx`, `backend/app/main.py`, `backend/app/models.py` | Complete (Chromium folder picker) |
| Admin-editable public placeholders and team roles | Database-backed site content plus authenticated content editor | `backend/app/models.py`, `backend/app/main.py`, `frontend/src/main.tsx` | Complete |
| Full production infrastructure | Requires team AWS/server credentials and deployment | `README.md` | External configuration required |
