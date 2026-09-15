from datetime import datetime, timedelta, timezone
import hmac
from typing import Optional
import jwt
from fastapi import HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from passlib.context import CryptContext
from .config import get_settings

passwords = CryptContext(schemes=["argon2"], deprecated="auto")
bearer = HTTPBearer(auto_error=False)
def hash_password(password: str) -> str: return passwords.hash(password)
def verify_password(password: str, password_hash: str) -> bool: return passwords.verify(password, password_hash)
def create_token(user_id: int) -> str:
    s = get_settings(); exp = datetime.now(timezone.utc) + timedelta(minutes=s.jwt_expire_minutes)
    return jwt.encode({"sub": str(user_id), "exp": exp}, s.jwt_secret, algorithm="HS256")
def create_demo_upload_grant(user_id: int) -> str:
    """Issue a narrowly scoped, short-lived token for the public demo only."""
    s = get_settings(); exp = datetime.now(timezone.utc) + timedelta(minutes=s.public_demo_upload_grant_minutes)
    return jwt.encode({"sub": str(user_id), "scope": "public_demo_upload", "exp": exp}, s.jwt_secret, algorithm="HS256")
def verify_demo_upload_code(code: str) -> bool:
    s = get_settings()
    return bool(s.public_demo_mode and s.public_demo_upload_code and hmac.compare_digest(code, s.public_demo_upload_code))
def demo_upload_subject(credentials: Optional[HTTPAuthorizationCredentials]) -> int:
    if not credentials: raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Upload access is required")
    try:
        payload = jwt.decode(credentials.credentials, get_settings().jwt_secret, algorithms=["HS256"])
        if payload.get("scope") != "public_demo_upload": raise ValueError("wrong token scope")
        return int(payload["sub"])
    except (jwt.PyJWTError, ValueError): raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Upload access has expired; enter the code again")
def token_subject(credentials: Optional[HTTPAuthorizationCredentials]) -> int:
    if not credentials: raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Authentication required")
    try:
        payload = jwt.decode(credentials.credentials, get_settings().jwt_secret, algorithms=["HS256"])
        if payload.get("scope"):
            raise ValueError("scoped token is not a user session")
        return int(payload["sub"])
    except (jwt.PyJWTError, ValueError): raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid or expired session")
