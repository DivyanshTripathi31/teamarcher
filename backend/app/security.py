from datetime import datetime, timedelta, timezone
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
def token_subject(credentials: Optional[HTTPAuthorizationCredentials]) -> int:
    if not credentials: raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Authentication required")
    try: return int(jwt.decode(credentials.credentials, get_settings().jwt_secret, algorithms=["HS256"])["sub"])
    except (jwt.PyJWTError, ValueError): raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid or expired session")
