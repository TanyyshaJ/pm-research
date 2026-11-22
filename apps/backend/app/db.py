import os
import uuid
from pathlib import Path
from sqlalchemy import create_engine, ForeignKey, String, Text, Integer, JSON, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[3]
load_dotenv(ROOT / '.env', override=False)
(ROOT / 'data').mkdir(exist_ok=True)
DATABASE_URL = os.getenv('DATABASE_URL', f"sqlite:///{(ROOT / 'data' / 'fieldnotes.db').as_posix()}")
engine = create_engine(DATABASE_URL, connect_args={'check_same_thread': False} if DATABASE_URL.startswith('sqlite') else {})
SessionLocal = sessionmaker(engine, expire_on_commit=False)

class Base(DeclarativeBase):
    pass

def uid():
    return str(uuid.uuid4())

class User(Base):
    __tablename__ = 'users'
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    email: Mapped[str] = mapped_column(String(254), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(Text)

class LoginSession(Base):
    __tablename__ = 'login_sessions'
    token_hash: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey('users.id'), index=True)
    expires_at: Mapped[int] = mapped_column(Integer)

class Project(Base):
    __tablename__ = 'projects'
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    owner_id: Mapped[str] = mapped_column(ForeignKey('users.id'), index=True)
    name: Mapped[str] = mapped_column(String(120))
    question: Mapped[str] = mapped_column(Text)
    audience: Mapped[str] = mapped_column(String(200), default='')
    geography: Mapped[str] = mapped_column(String(100), default='')
    created_at: Mapped[int] = mapped_column(Integer)

class ResearchRun(Base):
    __tablename__ = 'research_runs'
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    project_id: Mapped[str] = mapped_column(ForeignKey('projects.id'), index=True)
    active_project_id: Mapped[str | None] = mapped_column(String(36), unique=True, nullable=True)
    status: Mapped[str] = mapped_column(String(30), default='planning')
    model: Mapped[str] = mapped_column(String(100))
    config: Mapped[dict] = mapped_column(JSON)
    plan: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    brief: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    error: Mapped[str] = mapped_column(Text, default='')
    created_at: Mapped[int] = mapped_column(Integer)
    updated_at: Mapped[int] = mapped_column(Integer)
    cancel_requested: Mapped[int] = mapped_column(Integer, default=0)

class AgentStage(Base):
    __tablename__ = 'agent_stages'
    __table_args__ = (UniqueConstraint('run_id', 'name'),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    run_id: Mapped[str] = mapped_column(ForeignKey('research_runs.id'), index=True)
    name: Mapped[str] = mapped_column(String(40))
    status: Mapped[str] = mapped_column(String(20))
    output: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    error: Mapped[str] = mapped_column(Text, default='')
    started_at: Mapped[int] = mapped_column(Integer)
    finished_at: Mapped[int | None] = mapped_column(Integer, nullable=True)

class ModelCall(Base):
    __tablename__ = 'model_calls'
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    run_id: Mapped[str] = mapped_column(ForeignKey('research_runs.id'), index=True)
    role: Mapped[str] = mapped_column(String(40))
    status: Mapped[str] = mapped_column(String(20))
    usage: Mapped[dict] = mapped_column(JSON, default=dict)
    started_at: Mapped[int] = mapped_column(Integer)
    finished_at: Mapped[int | None] = mapped_column(Integer, nullable=True)

class ResearchSource(Base):
    __tablename__ = 'research_sources'
    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    run_id: Mapped[str] = mapped_column(ForeignKey('research_runs.id'), index=True)
    url: Mapped[str] = mapped_column(Text)
    title: Mapped[str] = mapped_column(Text)
    content: Mapped[str] = mapped_column(Text)
    content_hash: Mapped[str] = mapped_column(String(64))
    retrieved_at: Mapped[int] = mapped_column(Integer)

def get_db():
    with SessionLocal() as db:
        yield db
