import os
import secrets
import time
from collections import defaultdict, deque
from threading import Lock
from fastapi import FastAPI, Depends, HTTPException, Request, Response
from pydantic import BaseModel, EmailStr, Field, field_validator
from sqlalchemy import select, delete
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from .auth import COOKIE, TTL, current_user, hash_password, verify_password, token_hash
from .db import User, Project, LoginSession, get_db
from .fixture import research_brief
from contextlib import asynccontextmanager
from .research.routes import router as research_router
from .research.workflow import recover_interrupted
from .db import ResearchRun

@asynccontextmanager
async def lifespan(app):
    recover_interrupted()
    yield

app = FastAPI(title='Fieldnotes API', version='0.2.0', lifespan=lifespan)
app.include_router(research_router)
ORIGINS = set(os.getenv('ALLOWED_ORIGINS', 'http://127.0.0.1:3000,http://localhost:3000').split(','))
attempts: dict[str, deque] = defaultdict(deque)
rate_lock = Lock()
DUMMY_HASH = hash_password('unused-timing-comparison')

@app.middleware('http')
async def protect(request: Request, call_next):
    from fastapi.responses import JSONResponse
    if request.method in {'POST', 'PATCH', 'DELETE', 'PUT'}:
        origin = request.headers.get('origin')
        if (origin and origin not in ORIGINS) or request.headers.get('x-requested-with') != 'Fieldnotes':
            return JSONResponse({'detail': 'Request origin could not be verified.'}, status_code=403)
    response = await call_next(request)
    response.headers['Cache-Control'] = 'no-store'
    response.headers['X-Content-Type-Options'] = 'nosniff'
    return response

class Credentials(BaseModel):
    email: EmailStr
    password: str = Field(min_length=12, max_length=128)

class ProjectInput(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    question: str = Field(min_length=10, max_length=3000)
    audience: str = Field(default='', max_length=200)
    geography: str = Field(default='', max_length=100)

    @field_validator('name', 'question', 'audience', 'geography', mode='before')
    @classmethod
    def trim(cls, value):
        return value.strip() if isinstance(value, str) else value

def user_json(user):
    return {'id': user.id, 'email': user.email}

def project_json(project):
    return {key: getattr(project, key) for key in ['id', 'name', 'question', 'audience', 'geography', 'created_at']}

def rate_limit(request):
    key = request.client.host if request.client else 'unknown'
    now = time.time()
    with rate_lock:
        bucket = attempts[key]
        while bucket and bucket[0] < now - 60:
            bucket.popleft()
        if len(bucket) >= 20:
            raise HTTPException(429, 'Too many attempts. Please wait a minute.')
        bucket.append(now)

def sign_in(user, response, db):
    token = secrets.token_urlsafe(32)
    db.add(LoginSession(token_hash=token_hash(token), user_id=user.id, expires_at=int(time.time()) + TTL))
    db.commit()
    response.set_cookie(COOKIE, token, httponly=True, secure=os.getenv('COOKIE_SECURE') == 'true', samesite='lax', max_age=TTL, path='/')
    return user_json(user)

@app.get('/api/health')
def health():
    return {'status': 'ok', 'milestone': 'multi-agent-research', 'auth': 'local-development'}

@app.post('/api/auth/register', status_code=201)
def register(body: Credentials, request: Request, response: Response, db: Session = Depends(get_db)):
    rate_limit(request)
    user = User(email=str(body.email).lower(), password_hash=hash_password(body.password))
    db.add(user)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, 'Unable to create account. Try signing in instead.')
    return sign_in(user, response, db)

@app.post('/api/auth/login')
def login(body: Credentials, request: Request, response: Response, db: Session = Depends(get_db)):
    rate_limit(request)
    user = db.scalar(select(User).where(User.email == str(body.email).lower()))
    valid = verify_password(body.password, user.password_hash if user else DUMMY_HASH)
    if not user or not valid:
        raise HTTPException(401, 'Email or password is incorrect.')
    old_token = request.cookies.get(COOKIE)
    if old_token:
        db.execute(delete(LoginSession).where(LoginSession.token_hash == token_hash(old_token)))
    return sign_in(user, response, db)

@app.get('/api/auth/me')
def me(user: User = Depends(current_user)):
    return user_json(user)

@app.post('/api/auth/logout', status_code=204)
def logout(request: Request, response: Response, db: Session = Depends(get_db)):
    token = request.cookies.get(COOKIE)
    if token:
        db.execute(delete(LoginSession).where(LoginSession.token_hash == token_hash(token)))
        db.commit()
    response.delete_cookie(COOKIE, path='/')

@app.get('/api/projects')
def list_projects(user: User = Depends(current_user), db: Session = Depends(get_db)):
    return [project_json(p) for p in db.scalars(select(Project).where(Project.owner_id == user.id).order_by(Project.created_at.desc(), Project.id))]

@app.post('/api/projects', status_code=201)
def create_project(body: ProjectInput, user: User = Depends(current_user), db: Session = Depends(get_db)):
    project = Project(**body.model_dump(), owner_id=user.id, created_at=int(time.time()))
    db.add(project)
    db.commit()
    return project_json(project)

def owned_project(project_id, user, db):
    project = db.scalar(select(Project).where(Project.id == project_id, Project.owner_id == user.id))
    if not project:
        raise HTTPException(404, 'Project not found.')
    return project

@app.get('/api/projects/{project_id}')
def get_project(project_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
    return project_json(owned_project(project_id, user, db))

@app.get('/api/projects/{project_id}/brief')
def get_brief(project_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
    owned_project(project_id, user, db)
    run = db.scalar(select(ResearchRun).where(ResearchRun.project_id == project_id, ResearchRun.status.in_(['completed', 'partial'])).order_by(ResearchRun.created_at.desc(), ResearchRun.id))
    if not run or not run.brief:
        raise HTTPException(404, 'No live brief yet. Start a research run for this project.')
    return run.brief

@app.get('/api/projects/{project_id}/sample-brief')
def get_sample_brief(project_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
    return research_brief(owned_project(project_id, user, db))
