import json
from sqlalchemy.orm import Session
from .config import get_settings
from .models import User
from .security import hash_password

USERS = [("DIVYANSH TRIPATHI", "1024030283", "Divyansh Tripathi", "ADMIN"), ("MEHARDEEP SINGH", "1024030254", "Mehardeep Singh", "ADMIN"), ("VIDIT GUPTA", "1024030261", "Vidit Gupta", "ADMIN"), ("LAVISH GAMBHIR", "1024030260", "Lavish Gambhir", "ADMIN"), ("SUKHPAL SINGH", "0001001000", "Sukhpal Singh", "INSTRUCTOR")]
def seed(db: Session):
    s = get_settings()
    if not s.seed_initial_users: return
    configured = json.loads(s.initial_user_passwords_json)
    for username, legacy_id, name, role in USERS:
        account = db.query(User).filter_by(username=username).first() or db.query(User).filter_by(username=legacy_id).first()
        if not account:
            password = configured.get(username) or configured.get(legacy_id)
            if not password: raise RuntimeError(f"Missing initial password for {username}")
            db.add(User(username=username, display_name=name, role=role, password_hash=hash_password(password), must_change_password=True))
        elif account.username == legacy_id:
            account.username, account.display_name, account.role = username, name, role
    db.commit()
