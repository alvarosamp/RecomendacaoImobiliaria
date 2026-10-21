import pytest
from api.routes import cases
from test_land_projects import client as project_client, payload, as_user, team_with_members

@pytest.fixture
def client(project_client,monkeypatch):
    project_client.test_app.include_router(cases.router,prefix='/api')
    monkeypatch.setattr(cases,'territory_for_city',lambda city:[])
    return project_client

def body(**changes):return {**dict(title='Comparação',kind='invest',inputs={}),**changes}
def update_body(saved,**changes):return {key:changes.get(key,saved[key]) for key in ['title','kind','city_ibge','project_id','organization_id','demonstration','inputs','revision']}

@pytest.mark.parametrize('kind',['incorpora','obras','invest','mercado','negocios','governo'])
def test_six_demo_lifecycles(client,kind):
    response=client.post('/api/case-demos/'+kind)
    assert response.status_code==201,response.text
    saved=response.json();base=f"/api/cases/{saved['id']}"
    assert saved['demonstration'] and saved['result']['tables']
    assert client.get(base).json()==saved
    assert client.get('/api/cases').json()==[]
    assert len(client.get('/api/cases?demonstration=true').json())==1
    report=client.get(base+'/report')
    assert report.status_code==200 and 'SIMULAÇÃO DEMONSTRATIVA' in report.text
    assert 'default-src' in report.headers['content-security-policy']
    assert client.get(base+'/report?format=markdown').status_code==200
    reset=client.post(base+'/reset-demo',json={'revision':saved['revision']})
    assert reset.status_code==200 and reset.json()['revision']==saved['revision']+1

def test_draft_invalidation_conflict_privacy(client):
    saved=client.post('/api/cases',json=body()).json();base=f"/api/cases/{saved['id']}"
    assert client.post(base+'/reset-demo',json={'revision':1}).status_code==409
    assert client.get(base+'/report').status_code==422
    analyzed=client.post(base+'/analyze',json={'revision':1}).json()
    assert analyzed['result']['summary']['gaps']
    updated=client.patch(base,json=update_body(analyzed,inputs={'budget':0})).json()
    assert updated['result'] is None
    assert client.patch(base,json=update_body(analyzed)).status_code==409
    assert len(client.get(base+'/history').json())==3
    as_user(client,2)
    for route in [base,base+'/report',base+'/history']:assert client.get(route).status_code==404
    assert client.get('/api/cases').json()==[]

def test_tasks_evidence_revisions_membership(client):
    team=team_with_members(client)
    saved=client.post('/api/cases',json=body(organization_id=team['id'])).json();base=f"/api/cases/{saved['id']}"
    task={'revision':1,'title':'Conferir orçamento','status':'done','evidence':''}
    assert client.post(base+'/tasks',json=task).status_code==422
    task.update(status='pending',assignee='Equipe técnica',due_date='2026-11-01')
    saved=client.post(base+'/tasks',json=task).json();tid=saved['tasks'][0]['id']
    as_user(client,2)
    assert client.get(base).json()['can_edit'] is False
    assert client.patch(base+'/tasks/'+tid,json={**task,'revision':2}).status_code==403
    as_user(client,3)
    done=client.patch(base+'/tasks/'+tid,json={**task,'revision':2,'status':'done','evidence':'Orçamento revisado.'})
    assert done.status_code==200 and done.json()['tasks'][0]['completed_at']
    assert client.patch(base+'/tasks/'+tid,json={**task,'revision':2}).status_code==409
    as_user(client,1);client.delete(f"/api/organizations/{team['id']}/members/2")
    as_user(client,2);assert client.get(base).status_code==404

def test_linked_access_and_source_revision(client):
    team=team_with_members(client)
    p=client.post('/api/projects',json=payload(organization_id=team['id'])).json()
    case=client.post('/api/cases',json=body(kind='obras',project_id=p['id'])).json();base=f"/api/cases/{case['id']}"
    case=client.post(base+'/analyze',json={'revision':1}).json();assert case['stale'] is False
    client.patch(f"/api/projects/{p['id']}",json=payload(organization_id=team['id'],revision=1,notes='Alteração'))
    assert client.get(base).json()['stale'] is True
    assert client.get(base+'/report').status_code==409
    as_user(client,2);assert client.get('/api/cases').json()[0]['can_edit'] is False
    as_user(client,1);client.delete(f"/api/organizations/{team['id']}/members/2")
    as_user(client,2)
    assert client.get(base).status_code==404 and client.get('/api/cases').json()==[]

def test_unknown_city_escape_and_minimal_telemetry(client,monkeypatch):
    def unexpected(city):raise AssertionError('No lookup for declared investments')
    monkeypatch.setattr(cases,'territory_for_city',unexpected)
    saved=client.post('/api/cases',json=body(title='<script>alert(1)</script>',city_ibge='3550308')).json()
    base=f"/api/cases/{saved['id']}"
    analyzed=client.post(base+'/analyze',json={'revision':1}).json()
    assert analyzed['result']['sources']==[]
    assert any('sem cobertura' in x for x in analyzed['result']['summary']['gaps'])
    html=client.get(base+'/report').text
    assert '<script>' not in html and '&lt;script&gt;' in html
    assert client.post(base+'/interactions',json={'event':'partner_interest','price':100}).status_code==422
    assert client.post(base+'/interactions',json={'event':'partner_interest'}).status_code==204

def test_link_after_initial_save_and_review_completed_tasks(client):
    saved=client.post('/api/cases',json=body(kind='obras')).json();base=f"/api/cases/{saved['id']}"
    p=client.post('/api/projects',json=payload()).json()
    linked=client.patch(base,json=update_body(saved,project_id=p['id'])).json()
    assert linked['project_id']==p['id'] and linked['result'] is None
    task={'revision':linked['revision'],'title':'Vistoria','status':'done','evidence':'Referência anterior'}
    complete=client.post(base+'/tasks',json=task).json()
    updated=client.patch(base,json=update_body(complete,inputs={'investigation_note':'Novo escopo'})).json()
    assert updated['tasks'][0]['status']=='pending'
    assert updated['tasks'][0]['evidence']==''
    assert updated['tasks'][0]['previous_evidence']=='Referência anterior'
    assert updated['tasks'][0]['review_required'] is True
    assert client.patch(base,json=update_body(updated,project_id=None)).status_code==409

def test_feedback_is_private_and_not_telemetry(client):
    saved=client.post('/api/cases',json=body()).json();base=f"/api/cases/{saved['id']}"
    response=client.post(base+'/feedback',json={'revision':1,'note':'Preciso entender melhor o prazo.','comprehension':'unclear'})
    assert response.status_code==201
    assert response.json()['feedback'][0]['note']=='Preciso entender melhor o prazo.'
    assert client.post(base+'/interactions',json={'event':'step_viewed','step':3,'note':'private text'}).status_code==422
    as_user(client,2)
    assert client.get(base).status_code==404
    assert client.post(base+'/feedback',json={'revision':2,'note':'Not authorized'}).status_code==404

def test_registered_city_stays_without_pa_coverage(client):
    data={'ibge':'3550308','name':'São Paulo','state':'SP'}
    assert client.post('/api/municipalities',json=data).status_code==403
    as_user(client,1,'admin')
    assert client.post('/api/municipalities',json=data).status_code==201
    assert client.post('/api/municipalities',json=data).status_code==409
    city=next(c for c in client.get('/api/municipalities').json() if c['ibge']=='3550308')
    assert city['coverage']=='pending' and city['sources']==[]
    assert city['capabilities']['territory']=='pending'
    saved=client.post('/api/cases',json=body(city_ibge='3550308')).json()
    analyzed=client.post(f"/api/cases/{saved['id']}/analyze",json={'revision':1}).json()
    assert analyzed['result']['municipality_name']=='São Paulo'
    assert analyzed['result']['sources']==[]
