import hashlib
import secrets
import time
from fastapi import Depends, HTTPException, Request
from sqlalchemy.orm import Session
from .db import LoginSession, User, get_db

COOKIE = 'fieldnotes_session'
TTL = 60 * 60 * 24 * 7

def hash_password(password: str, salt: str | None = None) -> str:
    salt = salt or secrets.token_hex(16)
    value = hashlib.scrypt(password.encode(), salt=bytes.fromhex(salt), n=16384, r=8, p=1).hex()
    return f'{salt}:{value}'

def verify_password(password: str, stored: str) -> bool:
    return secrets.compare_digest(hash_password(password, stored.split(':')[0]), stored)

def token_hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()

def current_user(request: Request, db: Session = Depends(get_db)) -> User:
    token = request.cookies.get(COOKIE)
    session = db.get(LoginSession, token_hash(token)) if token else None
    if not session or session.expires_at <= int(time.time()):
        raise HTTPException(401, 'Please sign in to continue.')
    user = db.get(User, session.user_id)
    if not user:
        raise HTTPException(401, 'Please sign in to continue.')
    return user
