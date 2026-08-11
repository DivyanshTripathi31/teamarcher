from datetime import date
from pathlib import Path
import re
from typing import Optional
from fastapi import Depends, FastAPI, File, Form, HTTPException, UploadFile, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from .config import get_settings
from .database import Base, engine, get_db
from .models import Presentation, PresentationAsset, ProfileAvatar, PublicProfile, SiteContent, User
from .security import bearer, create_token, hash_password, token_subject, verify_password
from .seed import seed
from .storage import download_url, safe_key, upload

app = FastAPI(title="Archer Project Portal API", version="0.1.0")
settings = get_settings()
app.add_middleware(CORSMiddleware, allow_origins=[x.strip() for x in settings.cors_origins.split(",")], allow_credentials=False, allow_methods=["*"], allow_headers=["*"])

ALLOWED = {".pdf", ".ppt", ".pptx", ".png", ".jpg", ".jpeg", ".doc", ".docx", ".txt", ".md"}
class Login(BaseModel): username: str; password: str
class ProfileUpdate(BaseModel):
    display_name: str = Field(min_length=1, max_length=100)
    email: Optional[EmailStr] = None
    skills: list[str] = []
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
    Base.metadata.create_all(bind=engine)
    with Session(engine) as db:
        seed(db)
        if not db.get(SiteContent, 1):
            db.add(SiteContent(id=1, project_name="ARCHER", tagline="A living record of our software engineering project.", description="Archer brings the project’s planning, progress, and presentation history into one clear, permanent public portal.", problem="Add the real problem statement for Archer here.", objectives="Add the specific, measurable objectives the team agrees on.", intended_users="Add the people Archer is being built for.", core_features="Add the key capabilities that define Archer.", roles_json='{"Divyansh Tripathi":"Role to be assigned","Lavish Gambhir":"Role to be assigned","Mehardeep Singh":"Role to be assigned","Vidit Gupta":"Role to be assigned"}'))
            db.commit()

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
def user_out(u: User):
    import json
    profile = u.public_profile
    return {"id":u.id,"username":u.username,"display_name":u.display_name,"email":u.email,"role":u.role,"must_change_password":u.must_change_password,"avatar_url":download_url(u.avatar.file_storage_key) if u.avatar else None,"skills":json.loads(profile.skills_json) if profile else [],"show_email_public":profile.show_email_public if profile else False}
def member_slug(name: str) -> str: return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
def public_member_out(u: User, team_roles: dict):
    import json
    profile = u.public_profile
    return {"name":u.display_name,"slug":member_slug(u.display_name),"role":team_roles.get(u.display_name, "Team member"),"skills":json.loads(profile.skills_json) if profile else [],"avatar_url":download_url(u.avatar.file_storage_key) if u.avatar else None,"email":u.email if profile and profile.show_email_public else None}
def presentation_out(p: Presentation, include_url=False):
    data = {"id":p.id,"title":p.title,"slug":p.slug,"version":p.version,"presentation_date":p.presentation_date,"authors":p.authors,"change_summary":p.change_summary,"file_name":p.file_name,"published":p.published,"created_at":p.created_at,"created_by":p.created_by.display_name}
    if include_url:
        assets = p.assets or [PresentationAsset(relative_path=p.file_name, file_name=p.file_name, file_storage_key=p.file_storage_key, content_type=p.content_type, size_bytes=0)]
        data["assets"] = [{"id":a.id,"relative_path":a.relative_path,"file_name":a.file_name,"content_type":a.content_type,"size_bytes":a.size_bytes,"file_url":download_url(a.file_storage_key)} for a in assets]
        data["file_url"] = data["assets"][0]["file_url"]
    return data
def site_content_out(content: SiteContent):
    import json
    return {"projectName":content.project_name,"tagline":content.tagline,"description":content.description,"problem":content.problem,"objectives":content.objectives,"intendedUsers":content.intended_users,"coreFeatures":content.core_features,"roles":json.loads(content.roles_json)}

@app.get("/api/health")
def health(): return {"status":"ok"}
@app.post("/api/auth/login")
def login(body: Login, db: Session = Depends(get_db)):
    user = db.query(User).filter_by(username=body.username).first()
    if not user or not verify_password(body.password, user.password_hash): raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid username or password")
    return {"access_token":create_token(user.id),"token_type":"bearer","user":user_out(user)}
@app.get("/api/auth/me")
def me(user: User = Depends(current_user)): return user_out(user)
@app.patch("/api/users/me")
def update_profile(body: ProfileUpdate, user: User = Depends(current_user), db: Session = Depends(get_db)):
    import json
    user.display_name, user.email = body.display_name, str(body.email) if body.email else None
    clean_skills = list(dict.fromkeys(skill.strip()[:40] for skill in body.skills if skill.strip()))[:15]
    if not user.public_profile: db.add(PublicProfile(user_id=user.id, skills_json=json.dumps(clean_skills), show_email_public=body.show_email_public))
    else: user.public_profile.skills_json, user.public_profile.show_email_public = json.dumps(clean_skills), body.show_email_public
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
    if suffix not in {".png", ".jpg", ".jpeg", ".webp"}: raise HTTPException(415, "Profile image must be PNG, JPG, or WEBP")
    contents = await file.read()
    if not contents or len(contents) > 5 * 1024 * 1024: raise HTTPException(413, "Profile image must be between 1 byte and 5 MB")
    key = safe_key("profiles", str(user.id), filename)
    try: upload(key, contents, file.content_type or "image/jpeg")
    except Exception: raise HTTPException(502, "Profile image storage failed")
    if user.avatar:
        user.avatar.file_storage_key, user.avatar.content_type = key, file.content_type or "image/jpeg"
    else: db.add(ProfileAvatar(user_id=user.id, file_storage_key=key, content_type=file.content_type or "image/jpeg"))
    db.commit(); db.refresh(user); return user_out(user)
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
    uploaded = []
    for file, relative_path in zip(files, paths):
        filename = Path(file.filename or "").name
        relative_path = str(relative_path).replace("\\", "/").lstrip("/")
        if not filename or ".." in Path(relative_path).parts or Path(relative_path).name != filename: raise HTTPException(422, "Invalid folder path")
        suffix = Path(filename).suffix.lower()
        if suffix not in ALLOWED: raise HTTPException(415, f"Unsupported file type: {filename}")
        contents = await file.read()
        if not contents: raise HTTPException(422, f"File is empty: {filename}")
        if len(contents) > settings.max_upload_mb * 1024 * 1024: raise HTTPException(413, f"File exceeds {settings.max_upload_mb} MB limit: {filename}")
        key = safe_key(title, version, filename)
        try: upload(key, contents, file.content_type or "application/octet-stream")
        except Exception: raise HTTPException(502, "Object storage upload failed; no presentation was created")
        uploaded.append((filename, relative_path, key, file.content_type or "application/octet-stream", len(contents)))
    normalized = re.sub(r"[^a-z0-9]+", "-", f"{title}-{version}".lower()).strip("-")
    if db.query(Presentation).filter_by(title=title.strip(), version=version.strip()).first(): raise HTTPException(409, "This title and version already exists; versions are immutable")
    filename, _, key, content_type, _ = uploaded[0]
    p = Presentation(title=title.strip(), version=version.strip(), slug=normalized, presentation_date=presentation_date, authors=authors.strip(), change_summary=change_summary.strip(), file_name=filename, file_storage_key=key, content_type=content_type, created_by_id=user.id)
    db.add(p)
    try:
        db.flush()
        for filename, relative_path, key, content_type, size in uploaded:
            db.add(PresentationAsset(presentation_id=p.id, file_name=filename, relative_path=relative_path, file_storage_key=key, content_type=content_type, size_bytes=size))
        db.commit(); db.refresh(p)
    except IntegrityError:
        db.rollback(); raise HTTPException(409, "A presentation with this permanent URL already exists")
    return presentation_out(p)
@app.post("/api/presentations/{presentation_id}/publish")
def publish(presentation_id: int, user: User = Depends(admin), db: Session = Depends(get_db)):
    password_changed(user)
    p = db.get(Presentation, presentation_id)
    if not p: raise HTTPException(404, "Presentation not found")
    p.published = True; db.commit(); db.refresh(p); return presentation_out(p)
