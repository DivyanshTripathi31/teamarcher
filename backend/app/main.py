from datetime import date
import json
import logging
import os
from pathlib import Path
import re
import subprocess
import tempfile
from typing import Optional
from fastapi import Depends, FastAPI, File, Form, HTTPException, UploadFile, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy import func
from sqlalchemy.orm import Session
from .config import get_settings
from .database import Base, engine, get_db
from .models import Presentation, PresentationAsset, ProfileAvatar, PublicProfile, SiteContent, User
from .security import bearer, create_token, hash_password, token_subject, verify_password
from .bootstrap import bootstrap_database
from .storage import delete_many, download_url, local_file, safe_key, upload

app = FastAPI(title="Archer Project Portal API", version="0.1.0")
settings = get_settings()
logger = logging.getLogger(__name__)
app.add_middleware(CORSMiddleware, allow_origins=[x.strip() for x in settings.cors_origins.split(",")], allow_origin_regex=r"https?://(localhost|127\.0\.0\.1):\d+$", allow_credentials=False, allow_methods=["*"], allow_headers=["*"])

ALLOWED = {".pdf", ".ppt", ".pptx", ".png", ".jpg", ".jpeg", ".doc", ".docx", ".txt", ".md"}
CONTENT_TYPES = {
    ".pdf": "application/pdf",
    ".ppt": "application/vnd.ms-powerpoint",
    ".pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".doc": "application/msword",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ".txt": "text/plain; charset=utf-8",
    ".md": "text/markdown; charset=utf-8",
}
ARCHER_ALLOWED = {".rs", ".toml", ".lock", ".md", ".txt", ".json", ".yaml", ".yml"}
ARCHER_IGNORED_DIRS = {"target", "node_modules", ".venv", "venv", "dist", "build", "__pycache__"}
AVATAR_CONTENT_TYPES = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".webp": "image/webp"}
class Login(BaseModel): username: str; password: str
class ProfileUpdate(BaseModel):
    display_name: str = Field(min_length=1, max_length=100)
    email: Optional[EmailStr] = None
    skills: list[str] = []
    skill_groups: dict[str, list[str]] = {}
    archer_focus: list[str] = []
    show_email_public: bool = False
class PasswordUpdate(BaseModel): current_password: str; new_password: str = Field(min_length=10, max_length=128); confirm_password: str
class SiteContentUpdate(BaseModel):
    project_name: str = Field(min_length=1, max_length=100)
    tagline: str = Field(min_length=1, max_length=300)
    description: str = Field(min_length=1)
    problem: str = Field(min_length=1)
    objectives: str = Field(min_length=1)
    intended_users: str = Field(min_length=1)
    core_features: str = Field(min_length=1)
    roles: dict[str, str]

@app.on_event("startup")
def startup():
    # The foundation service must stay observable before PostgreSQL is
    # provisioned. Database-backed routes remain unavailable until then, while
    # /health continues to report that the process and reverse proxy are alive.
    try:
        if settings.database_auto_create:
            Base.metadata.create_all(bind=engine)
        bootstrap_database()
    except SQLAlchemyError:
        logger.warning("Database is unavailable; starting in health-only mode until PostgreSQL is configured.")

def current_user(credentials=Depends(bearer), db: Session = Depends(get_db)) -> User:
    user = db.get(User, token_subject(credentials))
    if not user: raise HTTPException(status.HTTP_401_UNAUTHORIZED, "User no longer exists")
    return user
def admin(user: User = Depends(current_user)) -> User:
    if user.role not in {"ADMIN", "INSTRUCTOR"}: raise HTTPException(status.HTTP_403_FORBIDDEN, "Insufficient permissions")
    return user
def content_admin(user: User = Depends(current_user)) -> User:
    if user.role != "ADMIN": raise HTTPException(status.HTTP_403_FORBIDDEN, "Only student admins can edit public site content")
    return user
def password_changed(user: User):
    if user.must_change_password:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Change your temporary password before uploading or publishing")

def safe_repository_path(root: Path, relative_path: str) -> Path:
    normalized = relative_path.replace("\\", "/").lstrip("/")
    candidate = (root / normalized).resolve()
    if candidate == root or root not in candidate.parents or ".." in Path(normalized).parts:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Invalid repository path")
    return candidate
def cleanup_new_objects(keys: list[str]) -> None:
    """Best-effort cleanup for objects that never became database records."""
    if not keys:
        return
    try:
        delete_many(keys)
    except Exception:
        # Do not conceal the original validation/database failure. The object
        # keys are collision-safe and can be removed manually if storage is
        # temporarily unavailable.
        logger.exception("Could not clean up uncommitted storage objects")
def profile_skills_data(profile: Optional[PublicProfile]):
    import json
    if not profile: return {}, []
    data = json.loads(profile.skills_json)
    if isinstance(data, list): return {"Core skills": data}, []
    if not isinstance(data, dict): return {}, []
    groups_data = data.get("skill_groups", data)
    focus_data = data.get("archer_focus", [])
    groups = {str(category): [str(skill) for skill in skills] for category, skills in groups_data.items() if isinstance(skills, list)} if isinstance(groups_data, dict) else {}
    focus = [str(item) for item in focus_data] if isinstance(focus_data, list) else []
    return groups, focus
def skill_groups_out(profile: Optional[PublicProfile]):
    return profile_skills_data(profile)[0]
def user_out(u: User):
    profile = u.public_profile
    skill_groups, archer_focus = profile_skills_data(profile)
    return {"id":u.id,"username":u.username,"display_name":u.display_name,"email":u.email,"role":u.role,"must_change_password":u.must_change_password,"avatar_url":download_url(u.avatar.file_storage_key) if u.avatar else None,"skills":[skill for skills in skill_groups.values() for skill in skills],"skill_groups":skill_groups,"archer_focus":archer_focus,"show_email_public":profile.show_email_public if profile else False}
def member_slug(name: str) -> str: return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
def public_member_out(u: User, team_roles: dict):
    profile = u.public_profile
    skill_groups, archer_focus = profile_skills_data(profile)
    return {"name":u.display_name,"slug":member_slug(u.display_name),"role":team_roles.get(u.display_name, "Team member"),"skills":[skill for skills in skill_groups.values() for skill in skills],"skill_groups":skill_groups,"archer_focus":archer_focus,"avatar_url":download_url(u.avatar.file_storage_key) if u.avatar else None,"email":u.email if profile and profile.show_email_public else None}
@app.get("/api/files/{object_key:path}")
def local_uploaded_file(object_key: str):
    path = local_file(object_key)
    if not path:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "File not found")
    return FileResponse(path)
def presentation_out(p: Presentation, include_url=False):
    data = {"id":p.id,"title":p.title,"slug":p.slug,"version":p.version,"presentation_date":p.presentation_date,"authors":p.authors,"change_summary":p.change_summary,"file_name":p.file_name,"published":p.published,"created_at":p.created_at,"created_by":p.created_by.display_name}
    if include_url:
        assets = p.assets or [PresentationAsset(relative_path=p.file_name, file_name=p.file_name, file_storage_key=p.file_storage_key, content_type=p.content_type, size_bytes=0)]
        data["assets"] = [{"id":a.id,"relative_path":a.relative_path,"file_name":a.file_name,"content_type":a.content_type,"size_bytes":a.size_bytes,"file_url":download_url(a.file_storage_key),"download_url":download_url(a.file_storage_key,a.file_name)} for a in assets]
        data["file_url"] = data["assets"][0]["file_url"]
    return data
def site_content_out(content: SiteContent):
    import json
    return {"projectName":content.project_name,"tagline":content.tagline,"description":content.description,"problem":content.problem,"objectives":content.objectives,"intendedUsers":content.intended_users,"coreFeatures":content.core_features,"roles":json.loads(content.roles_json)}

@app.get("/health", include_in_schema=False)
@app.get("/api/health")
def health(): return {"status":"ok"}
@app.post("/api/auth/login")
def login(body: Login, db: Session = Depends(get_db)):
    user = db.query(User).filter(func.upper(User.username) == body.username.strip().upper()).first()
    if not user or not verify_password(body.password, user.password_hash): raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid username or password")
    return {"access_token":create_token(user.id),"token_type":"bearer","user":user_out(user)}
@app.get("/api/auth/me")
def me(user: User = Depends(current_user)): return user_out(user)
@app.patch("/api/users/me")
def update_profile(body: ProfileUpdate, user: User = Depends(current_user), db: Session = Depends(get_db)):
    import json
    user.display_name, user.email = body.display_name, str(body.email) if body.email else None
    clean_groups = {category.strip()[:40]: list(dict.fromkeys(skill.strip()[:40] for skill in skills if skill.strip()))[:8] for category, skills in body.skill_groups.items() if category.strip()}
    clean_groups = {category: skills for category, skills in clean_groups.items() if skills}
    if not clean_groups:
        clean_skills = list(dict.fromkeys(skill.strip()[:40] for skill in body.skills if skill.strip()))[:15]
        clean_groups = {"Core skills": clean_skills} if clean_skills else {}
    clean_focus = list(dict.fromkeys(item.strip()[:60] for item in body.archer_focus if item.strip()))[:8]
    profile_data = json.dumps({"skill_groups": clean_groups, "archer_focus": clean_focus})
    if not user.public_profile: db.add(PublicProfile(user_id=user.id, skills_json=profile_data, show_email_public=body.show_email_public))
    else: user.public_profile.skills_json, user.public_profile.show_email_public = profile_data, body.show_email_public
    db.commit(); db.refresh(user); return user_out(user)
@app.post("/api/users/me/password")
def change_password(body: PasswordUpdate, user: User = Depends(current_user), db: Session = Depends(get_db)):
    if body.new_password != body.confirm_password: raise HTTPException(422, "Passwords do not match")
    if not verify_password(body.current_password, user.password_hash): raise HTTPException(400, "Current password is incorrect")
    user.password_hash, user.must_change_password = hash_password(body.new_password), False; db.commit(); return {"message":"Password updated"}
@app.post("/api/users/me/avatar")
async def update_avatar(file: UploadFile = File(...), user: User = Depends(current_user), db: Session = Depends(get_db)):
    filename = Path(file.filename or "").name
    suffix = Path(filename).suffix.lower()
    if suffix not in AVATAR_CONTENT_TYPES: raise HTTPException(415, "Profile image must be PNG, JPG, or WEBP")
    contents = await file.read()
    if not contents or len(contents) > 5 * 1024 * 1024: raise HTTPException(413, "Profile image must be between 1 byte and 5 MB")
    key = safe_key("profiles", str(user.id), filename)
    content_type = AVATAR_CONTENT_TYPES[suffix]
    try: upload(key, contents, content_type)
    except Exception: raise HTTPException(502, "Profile image storage failed")
    old_key = user.avatar.file_storage_key if user.avatar else None
    try:
        if user.avatar:
            user.avatar.file_storage_key, user.avatar.content_type = key, content_type
        else: db.add(ProfileAvatar(user_id=user.id, file_storage_key=key, content_type=content_type))
        db.commit(); db.refresh(user)
    except SQLAlchemyError:
        db.rollback()
        cleanup_new_objects([key])
        raise HTTPException(500, "Profile image could not be saved")
    if old_key and old_key != key:
        cleanup_new_objects([old_key])
    return user_out(user)
@app.get("/api/site-content")
def site_content(db: Session = Depends(get_db)):
    return site_content_out(db.get(SiteContent, 1))
@app.patch("/api/admin/site-content")
def update_site_content(body: SiteContentUpdate, user: User = Depends(content_admin), db: Session = Depends(get_db)):
    import json
    content = db.get(SiteContent, 1)
    for key in ("project_name", "tagline", "description", "problem", "objectives", "intended_users", "core_features"):
        setattr(content, key, getattr(body, key).strip())
    content.roles_json = json.dumps({name: role.strip() for name, role in body.roles.items()})
    db.commit(); db.refresh(content); return site_content_out(content)
@app.get("/api/team")
def team(db: Session = Depends(get_db)):
    import json
    roles = json.loads(db.get(SiteContent, 1).roles_json)
    users = db.query(User).filter_by(role="ADMIN").all()
    return sorted([public_member_out(user, roles) for user in users], key=lambda member: member["name"])
@app.get("/api/team/{slug}")
def team_member(slug: str, db: Session = Depends(get_db)):
    import json
    roles = json.loads(db.get(SiteContent, 1).roles_json)
    user = next((candidate for candidate in db.query(User).filter_by(role="ADMIN").all() if member_slug(candidate.display_name) == slug), None)
    if not user: raise HTTPException(404, "Team member not found")
    return public_member_out(user, roles)

@app.post("/api/archer/analyze")
async def analyze_repository(relative_paths: str = Form("[]"), files: list[UploadFile] = File(...), user: User = Depends(admin)):
    password_changed(user)
    if not files:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Upload at least one repository file")
    try:
        paths = json.loads(relative_paths)
    except json.JSONDecodeError:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Invalid repository path data")
    if not isinstance(paths, list) or len(paths) != len(files):
        paths = [Path(file.filename or "").name for file in files]
    selected = [(file, path) for file, path in zip(files, paths) if not any(part in ARCHER_IGNORED_DIRS for part in Path(str(path).replace("\\", "/")).parts)]
    if len(selected) > 500:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Repository contains more than 500 analyzable files; exclude generated files")
    if not selected:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "No analyzable repository files were selected")

    settings = get_settings()
    if not Path(settings.archer_binary).is_file() or not os.access(settings.archer_binary, os.X_OK):
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "Archer analyzer is not built on the server")
    with tempfile.TemporaryDirectory(prefix="archer-analysis-") as directory:
        root = Path(directory).resolve()
        written = 0
        for file, relative_path in selected:
            filename = Path(file.filename or "").name
            target = safe_repository_path(root, str(relative_path))
            if not filename or target.name != filename or target.suffix.lower() not in ARCHER_ALLOWED:
                raise HTTPException(status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, f"Unsupported repository file: {filename}")
            contents = await file.read()
            if not contents or len(contents) > settings.max_upload_mb * 1024 * 1024:
                raise HTTPException(status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, f"Invalid file size: {filename}")
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(contents)
            written += len(contents)
        try:
            completed = subprocess.run([settings.archer_binary, "--json", str(root)], capture_output=True, text=True, timeout=120, check=False)
        except subprocess.TimeoutExpired:
            raise HTTPException(status.HTTP_504_GATEWAY_TIMEOUT, "Archer analysis timed out after 120 seconds")
        if completed.returncode != 0:
            logger.error("Archer failed: %s", completed.stderr[-4000:])
            raise HTTPException(status.HTTP_502_BAD_GATEWAY, "Archer could not analyze this repository")
        try:
            report = json.loads(completed.stdout)
        except json.JSONDecodeError:
            logger.error("Archer returned invalid JSON: %s", completed.stdout[-4000:])
            raise HTTPException(status.HTTP_502_BAD_GATEWAY, "Archer returned an invalid report")
        for route in report.get("routes", []):
            try:
                route["file"] = str(Path(route["file"]).resolve().relative_to(root))
            except (KeyError, ValueError):
                route["file"] = Path(str(route.get("file", "unknown"))).name
            for evidence in route.get("authorization", []):
                try:
                    evidence["file"] = str(Path(evidence["file"]).resolve().relative_to(root))
                except (KeyError, ValueError):
                    evidence["file"] = Path(str(evidence.get("file", "unknown"))).name
        for group in report.get("peer_groups", []):
            for route in group.get("routes", []):
                route["file"] = normalize_report_path(route.get("file"), root)
                for evidence in route.get("authorization", []):
                    evidence["file"] = normalize_report_path(evidence.get("file"), root)
        for finding in report.get("finding_details", []):
            suspicious = finding.get("suspicious_route", {})
            suspicious["file"] = normalize_report_path(suspicious.get("file"), root)
            for evidence in finding.get("suspicious_route_evidence", []):
                evidence["file"] = normalize_report_path(evidence.get("file"), root)
            for route in finding.get("authorized_peer_routes", []):
                route["file"] = normalize_report_path(route.get("file"), root)
                for evidence in route.get("authorization", []):
                    evidence["file"] = normalize_report_path(evidence.get("file"), root)
        report["findings"] = [finding.replace(str(root), "").lstrip("/\\") for finding in report.get("findings", [])]
        report["parse_errors"] = [error.replace(str(root), "").lstrip("/\\") for error in report.get("parse_errors", [])]
    report["repository_files"] = len(selected)
    report["repository_bytes"] = written
    return report

def normalize_report_path(value: object, root: Path) -> str:
    try:
        return str(Path(str(value)).resolve().relative_to(root))
    except (KeyError, ValueError, TypeError):
        return Path(str(value or "unknown")).name

@app.get("/api/presentations")
def presentations(db: Session = Depends(get_db)):
    return [presentation_out(p) for p in db.query(Presentation).filter_by(published=True).order_by(Presentation.presentation_date.desc()).all()]
@app.get("/api/presentations/{slug}")
def presentation(slug: str, db: Session = Depends(get_db)):
    p = db.query(Presentation).filter_by(slug=slug, published=True).first()
    if not p: raise HTTPException(404, "Presentation not found")
    return presentation_out(p, True)
@app.get("/api/admin/dashboard")
def dashboard(user: User = Depends(admin), db: Session = Depends(get_db)):
    records = db.query(Presentation).order_by(Presentation.created_at.desc()).limit(10).all()
    return {"published_count":db.query(Presentation).filter_by(published=True).count(),"recent":[presentation_out(p) for p in records]}
@app.post("/api/presentations/upload", status_code=201)
async def create_presentation(title: str = Form(..., min_length=1, max_length=200), version: str = Form(..., min_length=1, max_length=40), presentation_date: date = Form(...), authors: str = Form(..., min_length=1), change_summary: str = Form(..., min_length=1), relative_paths: str = Form("[]"), files: list[UploadFile] = File(...), user: User = Depends(admin), db: Session = Depends(get_db)):
    password_changed(user)
    import json
    try: paths = json.loads(relative_paths)
    except json.JSONDecodeError: raise HTTPException(422, "Invalid folder path data")
    if not files or len(files) > 100: raise HTTPException(422, "Upload between 1 and 100 files")
    if not isinstance(paths, list) or len(paths) != len(files): paths = [Path(f.filename or "").name for f in files]
    clean_title, clean_version = title.strip(), version.strip()
    if not clean_title or not clean_version or not authors.strip() or not change_summary.strip():
        raise HTTPException(422, "Presentation metadata cannot be blank")
    if db.query(Presentation).filter_by(title=clean_title, version=clean_version).first():
        raise HTTPException(409, "This title and version already exists; versions are immutable")
    uploaded = []
    try:
        for file, relative_path in zip(files, paths):
            filename = Path(file.filename or "").name
            relative_path = str(relative_path).replace("\\", "/").lstrip("/")
            if not filename or len(filename) > 255 or len(relative_path) > 500 or ".." in Path(relative_path).parts or Path(relative_path).name != filename: raise HTTPException(422, "Invalid folder path")
            suffix = Path(filename).suffix.lower()
            if suffix not in ALLOWED: raise HTTPException(415, f"Unsupported file type: {filename}")
            contents = await file.read()
            if not contents: raise HTTPException(422, f"File is empty: {filename}")
            if len(contents) > settings.max_upload_mb * 1024 * 1024: raise HTTPException(413, f"File exceeds {settings.max_upload_mb} MB limit: {filename}")
            key = safe_key(clean_title, clean_version, filename)
            content_type = CONTENT_TYPES[suffix]
            try: upload(key, contents, content_type)
            except Exception: raise HTTPException(502, "Object storage upload failed; no presentation was created")
            uploaded.append((filename, relative_path, key, content_type, len(contents)))
    except Exception:
        cleanup_new_objects([item[2] for item in uploaded])
        raise
    normalized = re.sub(r"[^a-z0-9]+", "-", f"{clean_title}-{clean_version}".lower()).strip("-")
    filename, _, key, content_type, _ = uploaded[0]
    p = Presentation(title=clean_title, version=clean_version, slug=normalized, presentation_date=presentation_date, authors=authors.strip(), change_summary=change_summary.strip(), file_name=filename, file_storage_key=key, content_type=content_type, created_by_id=user.id)
    db.add(p)
    try:
        db.flush()
        for filename, relative_path, key, content_type, size in uploaded:
            db.add(PresentationAsset(presentation_id=p.id, file_name=filename, relative_path=relative_path, file_storage_key=key, content_type=content_type, size_bytes=size))
        db.commit(); db.refresh(p)
    except IntegrityError:
        db.rollback(); cleanup_new_objects([item[2] for item in uploaded]); raise HTTPException(409, "A presentation with this permanent URL already exists")
    except SQLAlchemyError:
        db.rollback(); cleanup_new_objects([item[2] for item in uploaded]); raise HTTPException(500, "Presentation metadata could not be saved")
    return presentation_out(p)
@app.post("/api/presentations/{presentation_id}/publish")
def publish(presentation_id: int, user: User = Depends(admin), db: Session = Depends(get_db)):
    password_changed(user)
    p = db.get(Presentation, presentation_id)
    if not p: raise HTTPException(404, "Presentation not found")
    p.published = True; db.commit(); db.refresh(p); return presentation_out(p)
@app.delete("/api/presentations/{presentation_id}", status_code=204)
def delete_presentation(presentation_id: int, user: User = Depends(content_admin), db: Session = Depends(get_db)):
    p = db.get(Presentation, presentation_id)
    if not p: raise HTTPException(404, "Presentation not found")
    keys = [p.file_storage_key, *(asset.file_storage_key for asset in p.assets)]
    try: delete_many(keys)
    except Exception: raise HTTPException(502, "Archive storage deletion failed; the archive was not removed")
    db.delete(p); db.commit()
