"""Offline provider doubles verify orchestration, not live model quality."""
import hashlib
import json
import socket
import threading
import time
import pytest
import httpx
from sqlalchemy import select, func
from app.db import ResearchRun, AgentStage, ModelCall, ResearchSource
from app.research import workflow, routes, web, provider
from app.research.provider import ResearchError, Cancelled, connections
from app.research.schemas import Plan
from .test_workspace import CREDS, PROJECT, register

QUOTE = 'Invoices can be tracked and payment reminders can be scheduled by the account owner.'
PRICE = 'The Standard plan is USD 12 per month when billed monthly.'

class FakeProvider:
    calls = []
    discovery_contexts = []
    search_barrier = None
    fail_synthesis_once = False

    def __init__(self, key, model, meter):
        self.meter = meter

    def record(self, role):
        self.calls.append(role)
        call = self.meter.begin(role)
        self.meter.finish(call, {'input_tokens': 100, 'output_tokens': 50}, 'completed')

    def discover(self, role, data):
        self.record(role + '_search')
        self.discovery_contexts.append(data)
        if self.search_barrier:
            self.search_barrier.wait(timeout=5)
        return {'sources': [{'url': 'https://example.org/' + role, 'title': role}]}

    def structured(self, role, instructions, data, schema):
        self.record(role)
        if role == 'planner':
            return {'objective': data['question'], 'questions': ['What problems and alternatives are supported?'], 'market_queries': ['customer invoice workflow research'], 'competitor_queries': ['invoice product pricing features'], 'completion_criteria': ['Supported sources and comparison'], 'assumptions': ['Audience is provisional']}
        if role in ('market', 'competitor', 'customer'):
            source = data['sources'][0]
            quote = source['content'] if role == 'customer' else QUOTE
            competitors = [{'name': 'Example Product', 'facts': [
                {'dimension': 'features', 'text': 'Supports scheduled reminders.', 'source_id': source['id'], 'quote': QUOTE},
                {'dimension': 'pricing', 'text': 'USD 12 per month, billed monthly, Standard plan.', 'source_id': source['id'], 'quote': PRICE},
            ]}] if role == 'competitor' else []
            return {'findings': [{'source_id': source['id'], 'quote': quote, 'finding': f'{role} finding for the saved question', 'limitation': 'Limited source sample.'}], 'competitors': competitors, 'gaps': []}
        if role == 'synthesizer':
            if self.fail_synthesis_once:
                FakeProvider.fail_synthesis_once = False
                raise ResearchError('Temporary provider failure.')
            eid = data['evidence'][0]['id']
            return {'title': data['context']['question'], 'subtitle': 'Offline test result', 'sections': [
                {'id': name, 'title': name.title(), 'eyebrow': 'Research', 'blocks': [
                    {'id': f'raw_{name}', 'type': 'observation' if name in ('summary','market','customers') else 'experiment', 'text': 'A scoped source-backed finding.' if name in ('summary','market','customers') else 'Test a proposed workflow with five participants.', 'evidence_ids': [eid], 'limitation': 'Limited evidence.'}
                ]} for name in ('summary','market','customers','opportunities','validation')], 'limitations': []}
        if role == 'reviewer':
            claims = [b for s in data['draft']['sections'] for b in s['blocks']]
            claims += [f for c in data['competitors'] for f in c['facts']]
            return {'claims': [{'claim_id': c['id'], 'supported': True, 'reason': 'Supported in this offline test.'} for c in claims], 'gaps': []}
        raise AssertionError(role)

@pytest.fixture
def research(clients, monkeypatch):
    a, b, sessions = clients
    register(a)
    user = a.get('/api/auth/me').json()
    project = a.post('/api/projects', json=PROJECT).json()
    FakeProvider.calls, FakeProvider.discovery_contexts = [], []
    FakeProvider.search_barrier, FakeProvider.fail_synthesis_once = None, False
    connections.set(user['id'], 'test-key-not-a-real-secret', 'gpt-5-mini')
    monkeypatch.setattr(routes, 'validate_connection', lambda key, model: None)
    def fetch(url, run_id):
        text = QUOTE + ' ' + PRICE
        return {'id': 'src_' + hashlib.sha256((run_id+url).encode()).hexdigest()[:24], 'url': url, 'title': 'Example Product pricing and features', 'content': text, 'content_hash': hashlib.sha256(text.encode()).hexdigest(), 'retrieved_at': int(time.time())}
    monkeypatch.setattr(workflow, 'fetch_source', fetch)
    monkeypatch.setattr(workflow, 'launch', lambda run_id, key, model: workflow.execute(run_id, key, model, provider_factory=FakeProvider))
    return a, b, sessions, project, user

def start_and_approve(a, project, notes=''):
    result = a.post(f'/api/projects/{project["id"]}/runs', json={'competitors': ['Example Product'], 'customer_notes': notes})
    assert result.status_code == 202, result.text
    rid = result.json()['id']
    assert a.get(f'/api/runs/{rid}').json()['status'] == 'awaiting_approval'
    assert FakeProvider.calls == ['planner']
    assert a.post(f'/api/runs/{rid}/approve', json={}).status_code == 200
    return rid, a.get(f'/api/runs/{rid}').json()

def test_real_question_parallel_agents_and_reviewed_report(research):
    a, _, sessions, project, _ = research
    FakeProvider.search_barrier = threading.Barrier(2)
    rid, result = start_and_approve(a, project)
    assert result['status'] == 'completed', result
    assert result['brief']['title'] == PROJECT['question']
    assert result['brief']['mode'] == 'live'
    assert result['brief']['competitors'][0]['name'] == 'Example Product'
    assert 'market_search' in FakeProvider.calls and 'competitor_search' in FakeProvider.calls
    assert FakeProvider.calls[-2:] == ['synthesizer','reviewer']
    assert result['usage']['model_requests'] == 7
    assert result['usage']['input_tokens'] == 700
    assert result['usage']['cost_usd'] is None
    with sessions() as db:
        assert db.scalar(select(func.count()).select_from(ResearchSource).where(ResearchSource.run_id == rid)) == 2
    assert a.get(f'/api/projects/{project["id"]}/brief').json()['run_id'] == rid

def test_customer_notes_never_enter_search(research):
    a, _, _, project, _ = research
    private_note = 'PRIVATE INTERVIEW: I manually follow up on unpaid invoices every Friday.'
    _, result = start_and_approve(a, project, private_note)
    assert result['status'] == 'completed', result
    assert 'customer' in FakeProvider.calls
    assert private_note not in json.dumps(FakeProvider.discovery_contexts)
    assert any(e['kind'] == 'Supplied customer notes' for e in result['brief']['evidence'])

def test_connection_is_private_and_not_persisted(research):
    a, b, sessions, _, _ = research
    key = 'test-api-secret-for-settings-only'
    response = a.post('/api/settings/ai', json={'api_key':key,'model':'gpt-5-mini'})
    assert response.status_code == 200
    assert key not in response.text
    assert key not in a.get('/api/settings/ai').text
    register(b, 'another@example.com')
    assert b.get('/api/settings/ai').json()['configured'] is False
    assert a.post('/api/settings/ai/disconnect',json={}).json()['configured'] is False

def test_no_key_no_run_and_no_sample_fallback(clients):
    a, _, sessions = clients
    register(a)
    project = a.post('/api/projects',json=PROJECT).json()
    result = a.post(f'/api/projects/{project["id"]}/runs',json={})
    assert result.status_code == 503
    assert a.get(f'/api/projects/{project["id"]}/brief').status_code == 404
    with sessions() as db:
        assert db.scalar(select(func.count()).select_from(ResearchRun)) == 0

def test_run_ownership_and_duplicate_active_run(research):
    a, b, _, project, _ = research
    rid = a.post(f'/api/projects/{project["id"]}/runs',json={}).json()['id']
    assert a.post(f'/api/projects/{project["id"]}/runs',json={}).status_code == 409
    register(b,'outsider@example.com')
    for suffix in ['', '/approve', '/cancel', '/resume']:
        response = b.get(f'/api/runs/{rid}') if not suffix else b.post(f'/api/runs/{rid}{suffix}',json={})
        assert response.status_code == 404
    assert b.get(f'/api/projects/{project["id"]}/runs').status_code == 404

def test_cancel_plan_does_not_call_research_agents(research):
    a, _, _, project, _ = research
    rid = a.post(f'/api/projects/{project["id"]}/runs',json={}).json()['id']
    assert a.post(f'/api/runs/{rid}/cancel',json={}).json()['status'] == 'cancelled'
    assert FakeProvider.calls == ['planner']
    assert a.post(f'/api/runs/{rid}/approve',json={}).status_code == 409

def test_resume_reuses_completed_checkpoints(research):
    a, _, _, project, _ = research
    FakeProvider.fail_synthesis_once = True
    rid, failed = start_and_approve(a,project)
    assert failed['status'] == 'failed'
    searches_before = FakeProvider.calls.count('market_search')
    assert a.post(f'/api/runs/{rid}/resume',json={}).status_code == 200
    resumed = a.get(f'/api/runs/{rid}').json()
    assert resumed['status'] == 'completed'
    assert FakeProvider.calls.count('planner') == 1
    assert FakeProvider.calls.count('market_search') == searches_before
    assert FakeProvider.calls.count('synthesizer') == 2

def test_restart_marks_inflight_usage_unknown(research):
    _, _, sessions, project, _ = research
    with sessions() as db:
        run = ResearchRun(project_id=project['id'], active_project_id=project['id'],status='researching',model='gpt-5-mini',config={},created_at=1,updated_at=1)
        db.add(run);db.flush()
        rid = run.id
        db.add(ModelCall(run_id=rid,role='market',status='running',usage={},started_at=1))
        db.commit()
    workflow.recover_interrupted()
    with sessions() as db:
        assert db.get(ResearchRun,rid).status == 'interrupted'
        assert db.get(ResearchRun,rid).active_project_id is None
        assert db.scalar(select(ModelCall).where(ModelCall.run_id==rid)).status == 'unknown'

def test_exact_quote_matching_rejects_fabricated_quote():
    source = {'id':'s','title':'Test','url':'https://example.org','content':QUOTE,'retrieved_at':1}
    assert workflow.verified_evidence({'source_id':'s','quote':QUOTE}, {'s':source},'market')
    assert workflow.verified_evidence({'source_id':'s','quote':'A quotation that does not exist in the source.'}, {'s':source},'market') is None

def test_reviewer_removal_and_invalid_citations_fail_closed():
    draft = {'title':'T','subtitle':'S','limitations':[],'sections':[{'id':'summary','title':'Summary','eyebrow':'','blocks':[
        {'id':'ok','type':'observation','text':'Supported','evidence_ids':['e'],'limitation':''},
        {'id':'bad','type':'observation','text':'Wrong citation','evidence_ids':['missing'],'limitation':''},
        {'id':'unreviewed','type':'observation','text':'Not reviewed','evidence_ids':['e'],'limitation':''},
    ]}]}
    review = {'claims':[{'claim_id':'ok','supported':True,'reason':''},{'claim_id':'bad','supported':True,'reason':''}], 'gaps':[]}
    brief = workflow.build_brief('r',draft,[{'id':'e'}],[],review,[],{})
    assert [b['id'] for b in brief['sections'][0]['blocks']] == ['ok']
    assert brief['review']['removed_claims'] == 2

@pytest.mark.parametrize('url',['http://127.0.0.1','http://169.254.169.254','http://[::1]/','file:///etc/passwd','https://user:pass@example.com','https://example.com:8443'])
def test_nonpublic_or_unsafe_urls_rejected(url):
    with pytest.raises(ResearchError):
        web.public_target(url)

def test_mixed_dns_answer_rejected(monkeypatch):
    monkeypatch.setattr(socket,'getaddrinfo',lambda *a,**k:[(2,1,6,'',('93.184.216.34',443)),(2,1,6,'',('127.0.0.1',443))])
    with pytest.raises(ResearchError):
        web.public_target('https://example.com')

def test_public_dns_is_pinned_with_original_tls_name(monkeypatch):
    monkeypatch.setattr(socket,'getaddrinfo',lambda *a,**k:[(2,1,6,'',('93.184.216.34',443))])
    canonical, pinned, host = web.public_target('https://example.com/path?q=1#fragment')
    assert canonical == 'https://example.com/path?q=1'
    assert pinned == 'https://93.184.216.34/path?q=1'
    assert host == 'example.com'

def test_provider_contract_and_usage(research,monkeypatch):
    a, _, _, project, _ = research
    rid=a.post(f'/api/projects/{project["id"]}/runs',json={}).json()['id']
    seen=[]
    plan={'objective':'Q','questions':['Q'],'market_queries':['Q'],'competitor_queries':['Q'],'completion_criteria':['Q'],'assumptions':[]}
    def respond(request):
        body=json.loads(request.content);seen.append(body)
        return httpx.Response(200,json={'status':'completed','usage':{'input_tokens':10,'output_tokens':20},'output':[{'type':'message','content':[{'type':'output_text','text':json.dumps(plan)}]}]})
    original_client=httpx.Client
    monkeypatch.setattr(provider.httpx,'Client',lambda **kwargs:original_client(transport=httpx.MockTransport(respond)))
    client=provider.OpenAIProvider('not-a-real-key','gpt-5-mini',workflow.Meter(rid))
    assert client.structured('planner','instructions',{'question':'Q'},Plan) == plan
    assert seen[0]['store'] is False
    assert seen[0]['text']['format']['strict'] is True
    assert 'tools' not in seen[0]

def test_cancel_prevents_publication(research):
    a, _, sessions, project, _ = research
    rid=a.post(f'/api/projects/{project["id"]}/runs',json={}).json()['id']
    a.post(f'/api/runs/{rid}/cancel',json={})
    with pytest.raises(Cancelled):
        workflow.set_run(rid,status='completed',brief={'should':'not publish'})
    with sessions() as db:
        assert db.get(ResearchRun,rid).brief is None

def test_unavailable_sources_never_publish_a_sample(research, monkeypatch):
    a, _, _, project, _ = research
    def blocked(*args):
        raise ResearchError('Source is blocked.')
    monkeypatch.setattr(workflow, 'fetch_source', blocked)
    _, result = start_and_approve(a, project)
    assert result['status'] == 'failed'
    assert result['brief'] is None
    assert 'synthesizer' not in FakeProvider.calls
    assert a.get(f'/api/projects/{project["id"]}/brief').status_code == 404

def test_reviewer_rejecting_all_claims_prevents_publication(research, monkeypatch):
    a, _, _, project, _ = research
    original = FakeProvider.structured
    def reject(self, role, instructions, data, schema):
        result = original(self, role, instructions, data, schema)
        if role == 'reviewer':
            for decision in result['claims']:
                decision['supported'] = False
                decision['reason'] = 'Insufficient support.'
        return result
    monkeypatch.setattr(FakeProvider, 'structured', reject)
    _, result = start_and_approve(a, project)
    assert result['status'] == 'failed'
    assert result['brief'] is None
    assert a.get(f'/api/projects/{project["id"]}/brief').status_code == 404

def test_failed_competitor_branch_produces_partial_not_complete(research, monkeypatch):
    a, _, _, project, _ = research
    original = workflow.fetch_source
    def fetch(url, run_id):
        if url.endswith('/competitor'):
            raise ResearchError('Competitor page is blocked.')
        return original(url, run_id)
    monkeypatch.setattr(workflow, 'fetch_source', fetch)
    _, result = start_and_approve(a, project)
    assert result['status'] == 'partial'
    assert result['brief']['competitors'] == []
    assert any('blocked' in gap for gap in result['brief']['limitations'])
