import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.db import Base, get_db
from app.main import app, attempts

@pytest.fixture
def clients(tmp_path, monkeypatch):
    engine = create_engine(f'sqlite:///{tmp_path / "test.db"}', connect_args={'check_same_thread': False})
    Base.metadata.create_all(engine)
    sessions = sessionmaker(engine, expire_on_commit=False)
    from app.research import workflow
    from app.research.provider import connections
    monkeypatch.setattr(workflow, 'SessionLocal', sessions)
    monkeypatch.setattr(connections, '_values', {})
    monkeypatch.delenv('OPENAI_API_KEY', raising=False)
    def override():
        with sessions() as db:
            yield db
    app.dependency_overrides[get_db] = override
    attempts.clear()
    headers = {'X-Requested-With': 'Fieldnotes', 'Origin': 'http://127.0.0.1:3000'}
    with TestClient(app, headers=headers) as a, TestClient(app, headers=headers) as b:
        yield a, b, sessions
    app.dependency_overrides.clear()
    engine.dispose()
