import os
from datetime import datetime, timedelta, timezone
import jwt
from jwt.exceptions import InvalidTokenError
import hashlib
import hmac
import secrets
from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from .database import get_db
from .models import User

SECRET = os.getenv("JWT_SECRET", "development-secret-do-not-deploy")
ALGORITHM = "HS256"
class PasswordHasher:
    @staticmethod
    def hash(password: str) -> str:
        salt = secrets.token_bytes(16)
        digest = hashlib.scrypt(password.encode(), salt=salt, n=2**14, r=8, p=1)
        return salt.hex() + ":" + digest.hex()

    @staticmethod
    def verify(password: str, stored: str) -> bool:
        try:
            salt_hex, expected_hex = stored.split(":", 1)
            actual = hashlib.scrypt(password.encode(), salt=bytes.fromhex(salt_hex), n=2**14, r=8, p=1)
            return hmac.compare_digest(actual, bytes.fromhex(expected_hex))
        except ValueError:
            return False

passwords = PasswordHasher()
auth_scheme = HTTPBearer()

def create_token(user_id: int) -> str:
    return jwt.encode({"sub": str(user_id), "exp": datetime.now(timezone.utc)+timedelta(hours=24)}, SECRET, algorithm=ALGORITHM)

def get_user(credentials: HTTPAuthorizationCredentials = Depends(auth_scheme), db: Session = Depends(get_db)) -> User:
    try:
        payload = jwt.decode(credentials.credentials, SECRET, algorithms=[ALGORITHM])
        user = db.get(User, int(payload["sub"]))
    except (InvalidTokenError, ValueError, KeyError, TypeError):
        raise HTTPException(status_code=401, detail="Invalid token")
    if user is None:
        raise HTTPException(status_code=401, detail="Invalid token")
    return user
