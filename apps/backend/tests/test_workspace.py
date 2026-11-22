import time
from sqlalchemy import select
from app.auth import token_hash
from app.db import LoginSession, User

CREDS = {'email': 'researcher@example.com', 'password': 'development-only-passphrase'}
PROJECT = {'name': 'Freelancer finance', 'question': 'How do freelancers follow up on unpaid invoices?', 'audience': 'Freelancers', 'geography': 'India'}

def register(client, email=CREDS['email']):
    result = client.post('/api/auth/register', json={**CREDS, 'email': email})
    assert result.status_code == 201
    return result

def test_private_endpoints_require_session(clients):
    a, _, _ = clients
    assert a.get('/api/projects').status_code == 401
    assert a.get('/api/projects/not-owned/brief').status_code == 401
    assert a.post('/api/projects', json=PROJECT).status_code == 401

def test_registration_cookie_and_hashing(clients):
    a, _, sessions = clients
    result = register(a)
    assert 'httponly' in result.headers['set-cookie'].lower()
    assert 'samesite=lax' in result.headers['set-cookie'].lower()
    assert a.get('/api/auth/me').json()['email'] == CREDS['email']
    with sessions() as db:
        user = db.scalar(select(User))
        session = db.scalar(select(LoginSession))
        assert CREDS['password'] not in user.password_hash
        assert session.token_hash == token_hash(a.cookies['fieldnotes_session'])
        assert session.token_hash != a.cookies['fieldnotes_session']

def test_sign_out_revokes_and_login_restores(clients):
    a, b, _ = clients
    register(a)
    old = a.cookies['fieldnotes_session']
    assert a.post('/api/auth/logout').status_code == 204
    assert a.get('/api/auth/me').status_code == 401
    b.cookies.set('fieldnotes_session', old)
    assert b.get('/api/auth/me').status_code == 401
    assert a.post('/api/auth/login', json=CREDS).status_code == 200
    assert a.cookies['fieldnotes_session'] != old

def test_invalid_login_and_duplicate_email(clients):
    a, _, _ = clients
    register(a)
    assert a.post('/api/auth/register', json=CREDS).status_code == 409
    result = a.post('/api/auth/login', json={**CREDS, 'password': 'incorrect-password'})
    assert result.status_code == 401
    assert 'incorrect' in result.json()['detail']

def test_project_ownership_and_persistence(clients):
    a, b, _ = clients
    register(a)
    result = a.post('/api/projects', json=PROJECT)
    assert result.status_code == 201
    pid = result.json()['id']
    a.post('/api/auth/logout')
    a.post('/api/auth/login', json=CREDS)
    assert a.get('/api/projects').json()[0]['id'] == pid
    register(b, 'other@example.com')
    assert b.get('/api/projects').json() == []
    assert b.get(f'/api/projects/{pid}').status_code == 404
    assert b.get(f'/api/projects/{pid}/brief').status_code == 404

def test_citations_resolve_and_fixture_is_honest(clients):
    a, _, _ = clients
    register(a)
    pid = a.post('/api/projects', json=PROJECT).json()['id']
    assert a.get(f'/api/projects/{pid}/brief').status_code == 404
    brief = a.get(f'/api/projects/{pid}/sample-brief').json()
    assert brief['mode'] == 'fixture'
    assert 'synthetic' in brief['notice'].lower()
    evidence = {e['id']: e for e in brief['evidence']}
    for section in brief['sections']:
        for claim in section['blocks']:
            if claim['type'] == 'observation':
                assert claim['evidence_ids']
            for eid in claim['evidence_ids']:
                assert evidence[eid]['excerpt']
                assert evidence[eid]['location']
                assert evidence[eid]['limitation']

def test_csrf_and_cross_origin_rejected(clients):
    a, _, _ = clients
    assert a.post('/api/auth/register', json=CREDS, headers={'Origin': 'https://attacker.example'}).status_code == 403
    a.headers.pop('X-Requested-With')
    assert a.post('/api/auth/register', json=CREDS).status_code == 403

def test_validation(clients):
    a, _, _ = clients
    assert a.post('/api/auth/register', json={**CREDS, 'password': 'short'}).status_code == 422
    register(a)
    assert a.post('/api/projects', json={**PROJECT, 'name': '   '}).status_code == 422
    assert a.post('/api/projects', json={**PROJECT, 'question': 'short'}).status_code == 422

def test_expired_session(clients):
    a, _, sessions = clients
    register(a)
    with sessions() as db:
        session = db.scalar(select(LoginSession))
        session.expires_at = int(time.time()) - 1
        db.commit()
    assert a.get('/api/auth/me').status_code == 401

def test_rate_limit(clients):
    a, _, _ = clients
    for _ in range(20):
        assert a.post('/api/auth/login', json=CREDS).status_code == 401
    assert a.post('/api/auth/login', json=CREDS).status_code == 429
