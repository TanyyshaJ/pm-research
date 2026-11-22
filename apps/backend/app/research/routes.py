import time
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from .schemas import ConnectionInput, RunInput
from .provider import connections, validate_connection, ResearchError
from . import workflow
from ..auth import current_user
from ..db import get_db, User, Project, ResearchRun, AgentStage, ModelCall

router = APIRouter(prefix='/api')

def owned(project_id, user, db):
    project = db.scalar(select(Project).where(Project.id == project_id, Project.owner_id == user.id))
    if not project:
        raise HTTPException(404, 'Project not found.')
    return project

def owned_run(run_id, user, db):
    run = db.get(ResearchRun, run_id)
    if not run:
        raise HTTPException(404, 'Research run not found.')
    owned(run.project_id, user, db)
    return run

def connection_for(user):
    connection = connections.get(user.id)
    if not connection:
        raise HTTPException(503, 'Connect AI before starting research. Add your OpenAI API key in the app; no key is currently configured.')
    return connection

def run_json(run, db, detail=True):
    calls = db.scalars(select(ModelCall).where(ModelCall.run_id == run.id)).all()
    result = {k: getattr(run, k) for k in ['id', 'project_id', 'status', 'model', 'plan', 'error', 'created_at', 'updated_at', 'cancel_requested']}
    result['usage'] = {
        'model_requests': len(calls), 'max_requests': workflow.MAX_CALLS,
        'input_tokens': sum(c.usage.get('input_tokens', 0) for c in calls),
        'output_tokens': sum(c.usage.get('output_tokens', 0) for c in calls),
        'unknown_requests': sum(c.status == 'unknown' for c in calls),
        'cost_usd': None,
    }
    result['stages'] = [{k: getattr(s, k) for k in ['name', 'status', 'error', 'started_at', 'finished_at']}
        for s in db.scalars(select(AgentStage).where(AgentStage.run_id == run.id).order_by(AgentStage.started_at, AgentStage.name))]
    if detail:
        result['brief'] = run.brief
    return result

@router.get('/settings/ai')
def ai_status(user: User = Depends(current_user)):
    value = connections.get(user.id)
    return {'configured': bool(value), 'model': value[1] if value else 'gpt-5-mini', 'provider': 'OpenAI', 'key_storage': 'server memory or server environment'}

@router.post('/settings/ai')
def connect(body: ConnectionInput, user: User = Depends(current_user)):
    key = body.api_key.get_secret_value().strip()
    try:
        validate_connection(key, body.model)
    except ResearchError as error:
        raise HTTPException(400, str(error)) from None
    connections.set(user.id, key, body.model)
    return {'configured': True, 'model': body.model, 'provider': 'OpenAI', 'key_storage': 'server memory; cleared on server restart'}

@router.post('/settings/ai/disconnect')
def disconnect(user: User = Depends(current_user)):
    connections.clear(user.id)
    # Environment configuration cannot be removed through a browser.
    return ai_status(user)

@router.get('/projects/{project_id}/runs')
def list_runs(project_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
    owned(project_id, user, db)
    return [run_json(r, db, detail=False) for r in db.scalars(select(ResearchRun).where(ResearchRun.project_id == project_id).order_by(ResearchRun.created_at.desc(), ResearchRun.id).limit(30))]

@router.post('/projects/{project_id}/runs', status_code=202)
def start_run(project_id: str, body: RunInput, user: User = Depends(current_user), db: Session = Depends(get_db)):
    project = owned(project_id, user, db)
    key, model = connection_for(user)
    if any(not 1 <= len(c.strip()) <= 500 for c in body.competitors):
        raise HTTPException(422, 'Supply up to five competitor names or public URLs, each at most 500 characters.')
    config = {'question': project.question, 'audience': project.audience, 'geography': project.geography,
        'competitors': [c.strip() for c in body.competitors], 'customer_notes': body.customer_notes,
        'approved': False, 'workflow_version': 1, 'prompt_version': 1}
    run = ResearchRun(project_id=project.id, active_project_id=project.id, status='planning', model=model,
        config=config, created_at=int(time.time()), updated_at=int(time.time()))
    db.add(run)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, 'This project already has an active run. Approve or cancel it before starting another.') from None
    result = run_json(run, db)
    workflow.launch(run.id, key, model)
    return result

@router.get('/runs/{run_id}')
def get_run(run_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
    return run_json(owned_run(run_id, user, db), db)

@router.post('/runs/{run_id}/approve')
def approve(run_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
    run = owned_run(run_id, user, db)
    key, model = connection_for(user)
    if run.status != 'awaiting_approval' or not run.plan:
        raise HTTPException(409, 'This run is not waiting for plan approval.')
    if model != run.model:
        raise HTTPException(409, 'Reconnect the model used for this run before approving it.')
    run.config = {**run.config, 'approved': True}
    run.status, run.updated_at = 'researching', int(time.time())
    db.commit()
    workflow.launch(run.id, key, model)
    return run_json(run, db)

@router.post('/runs/{run_id}/cancel')
def cancel(run_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
    run = owned_run(run_id, user, db)
    if run.status in workflow.TERMINAL:
        return run_json(run, db)
    run.cancel_requested, run.updated_at = 1, int(time.time())
    if run.status == 'awaiting_approval':
        run.status, run.active_project_id = 'cancelled', None
    db.commit()
    return run_json(run, db)

@router.post('/runs/{run_id}/resume')
def resume(run_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
    run = owned_run(run_id, user, db)
    key, model = connection_for(user)
    if run.status not in {'failed', 'interrupted'}:
        raise HTTPException(409, 'Only failed or interrupted runs can be resumed. Start a new run to change the research inputs.')
    if model != run.model:
        raise HTTPException(409, 'Reconnect the model used for this run before resuming it.')
    run.active_project_id, run.cancel_requested, run.error = run.project_id, 0, ''
    run.status = 'researching' if run.config.get('approved') else 'planning'
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, 'Another run is active for this project.') from None
    workflow.launch(run.id, key, model)
    return run_json(run, db)
