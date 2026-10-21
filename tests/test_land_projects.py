"""Project lifecycle and ownership; analytical sources are controlled fixtures."""
import os
from uuid import uuid4

import h3
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.schema import CreateSchema, DropSchema
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from api.routes import auth, projects, organizations

CELL = h3.latlng_to_cell(-22.23, -45.94, 8)


@pytest.fixture
def client(monkeypatch):
    url = os.getenv("URBIA_TEST_DATABASE_URL", "sqlite://")
    engine = create_engine(url, **({"connect_args": {"check_same_thread": False}, "poolclass": StaticPool} if url == "sqlite://" else {}))
    schema = None
    if url != 'sqlite://':
        schema = 'urbia_test_' + uuid4().hex
        with engine.begin() as connection:
            connection.execute(CreateSchema(schema))
        engine = engine.execution_options(schema_translate_map={None: schema})
    auth.Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine)
    with factory() as session:
        session.add_all([auth.User(name=f"User {i}", email=f"{i}@test.local", password_hash="unused", role="incorporadora") for i in [1, 2, 3, 4]])
        session.commit()
    app = FastAPI()
    app.include_router(auth.router, prefix="/api")
    app.include_router(projects.router, prefix="/api")
    app.include_router(organizations.router, prefix="/api")
    def db():
        with factory() as session:
            yield session
    app.dependency_overrides[auth.get_db] = db
    app.dependency_overrides[auth.get_current_user] = lambda: auth.User(id=1)
    monkeypatch.setattr(projects, "get_scores", lambda: [{"h3_id": CELL, "zona": "ZR", "score_residencial": 71, "score_comercial": 31, "risk_level": "baixo", "explainability": []}])
    monkeypatch.setattr(projects, "assess_legal_compatibility", lambda **kw: {"status": "conditioned", "zone": "ZR", "notes": "Exige validação", "articles": ["Art. teste"], "sources": [{"title": "Fonte de teste", "url": "https://example.org/test"}], "spatial_overlays_verified": False})
    with TestClient(app) as test_client:
        test_client.test_app = app
        test_client.db_factory = factory
        yield test_client
    if schema:
        with engine.begin() as connection:
            connection.execute(DropSchema(schema, cascade=True))
    engine.dispose()


def payload(**changes):
    return {"name": "Estudo residencial", "h3_id": CELL, "premises": {"lotArea": 300, "buildArea": 165}, **changes}


def test_lifecycle_reopen_and_integrated_report(client):
    created = client.post('/api/projects', json=payload()).json()
    analyzed = client.post(f"/api/projects/{created['id']}/analyze", json={"revision": 1})
    assert analyzed.status_code == 200
    saved = analyzed.json()
    assert saved['revision'] == 2
    assert saved['analysis']['area']['h3_id'] == CELL
    assert len(saved['analysis']['concept']['scenarios']) == 3
    assert client.get(f"/api/projects/{saved['id']}").json() == saved
    assert client.get('/api/projects').json()[0] == saved
    report = client.get(f"/api/projects/{saved['id']}/report")
    assert report.status_code == 200
    for text in [CELL, 'Art. teste', 'https://example.org/test', 'Cenários preliminares', 'não o limite cadastral']:
        assert text in report.text


def test_edit_invalidates_results_and_rejects_stale_revision(client):
    created = client.post('/api/projects', json=payload()).json()
    client.post(f"/api/projects/{created['id']}/analyze", json={"revision": 1})
    changed = payload(revision=2, premises={"lotArea": 450})
    updated = client.patch(f"/api/projects/{created['id']}", json=changed)
    assert updated.status_code == 200
    assert updated.json()['analysis'] is None
    assert client.patch(f"/api/projects/{created['id']}", json=changed).status_code == 409
    assert client.post(f"/api/projects/{created['id']}/analyze", json={"revision": 2}).status_code == 409
    assert 'Análise pendente' in client.get(f"/api/projects/{created['id']}/report").text


def test_projects_are_private_including_report_and_analysis(client):
    created = client.post('/api/projects', json=payload()).json()
    client.test_app.dependency_overrides[auth.get_current_user] = lambda: auth.User(id=2)
    assert client.get('/api/projects').json() == []
    for suffix in ['', '/report']:
        assert client.get(f"/api/projects/{created['id']}{suffix}").status_code == 404
    assert client.patch(f"/api/projects/{created['id']}", json=payload(revision=1)).status_code == 404
    assert client.post(f"/api/projects/{created['id']}/analyze", json={"revision": 1}).status_code == 404


def test_validation_and_missing_selection(client):
    assert client.post('/api/projects', json=payload(name='   ')).status_code == 422
    assert client.post('/api/projects', json=payload(h3_id='bad')).status_code == 422
    assert client.post('/api/projects', json=payload(premises={"lotArea": -1})).status_code == 422
    created = client.post('/api/projects', json=payload(h3_id=None)).json()
    assert client.post(f"/api/projects/{created['id']}/analyze", json={"revision": 1}).status_code == 422


def test_note_only_edit_preserves_analysis(client):
    created = client.post('/api/projects', json=payload()).json()
    saved = client.post(f"/api/projects/{created['id']}/analyze", json={"revision": 1}).json()
    response = client.patch(f"/api/projects/{created['id']}", json={**saved, "notes": "Documento adicional"})
    assert response.status_code == 200
    assert response.json()['analysis'] == saved['analysis']


def test_analysis_uses_server_territorial_values(client):
    created = client.post('/api/projects', json=payload(premises={"residentialScore": 99, "zone": "fake"})).json()
    saved = client.post(f"/api/projects/{created['id']}/analyze", json={"revision": 1}).json()
    assert saved['analysis']['premises_used']['residentialScore'] == 71
    assert saved['analysis']['premises_used']['zone'] == 'ZR'


def test_projects_require_authentication(client):
    client.test_app.dependency_overrides.pop(auth.get_current_user)
    assert client.get('/api/projects').status_code == 401


def test_real_login_can_save_and_reopen_project(client):
    client.test_app.dependency_overrides.pop(auth.get_current_user)
    registered = client.post('/api/auth/register', json={"name": "Owner", "email": "owner@test.local", "password": "local-only-test", "profile": "incorporadora"})
    assert registered.status_code == 200
    token = client.post('/api/auth/login', json={"email": "owner@test.local", "password": "local-only-test"}).json()['access_token']
    headers = {"Authorization": f"Bearer {token}"}
    created = client.post('/api/projects', json=payload(), headers=headers)
    assert created.status_code == 201
    assert client.get('/api/projects', headers=headers).json()[0]['id'] == created.json()['id']
    assert client.get(f"/api/projects/{created.json()['id']}", headers=headers).json()['name'] == 'Estudo residencial'


def test_zero_scores_and_zero_confidence_are_not_replaced_with_defaults():
    from api.routes.concept import ConceptInput, analyze_concept
    zero = analyze_concept(ConceptInput(residentialScore=0, commercialScore=0, riskLevel="alto", riskConfidence=0))
    missing = analyze_concept(ConceptInput(riskLevel="alto", riskConfidence=0))
    assert zero['plan']['viabilityScore'] < missing['plan']['viabilityScore']
    assert zero['plan']['riskAdjustment']['factor'] == 1.0


def as_user(client, user_id, profile='incorporadora'):
    client.test_app.dependency_overrides[auth.get_current_user] = lambda: auth.User(id=user_id, role=profile)


def team_with_members(client):
    team = client.post('/api/organizations', json={'name': 'Equipe teste'}).json()
    for user_id, role in [(2, 'viewer'), (3, 'editor')]:
        assert client.post(f"/api/organizations/{team['id']}/members", json={'email': f'{user_id}@test.local', 'role': role}).status_code == 201
    return team


def test_teams_enforce_owner_management_and_protect_responsible(client):
    team = team_with_members(client)
    base = f"/api/organizations/{team['id']}/members"
    assert client.post(base, json={'email': '2@test.local', 'role': 'viewer'}).status_code == 409
    assert client.delete(base + '/1').status_code == 409
    assert client.patch(base + '/1', json={'role': 'viewer'}).status_code == 409
    assert client.post(base, json={'email': '4@test.local', 'role': 'owner'}).status_code == 422
    as_user(client, 3)
    assert client.get(base).status_code == 403
    assert client.post(base, json={'email': '4@test.local', 'role': 'editor'}).status_code == 403
    as_user(client, 4, 'governo')
    assert client.get('/api/organizations').json() == []
    assert client.get(base).status_code == 404


def test_shared_project_viewer_and_editor_permissions(client):
    team = team_with_members(client)
    created = client.post('/api/projects', json=payload(organization_id=team['id'])).json()
    base = f"/api/projects/{created['id']}"
    as_user(client, 2)
    assert client.get(base).json()['can_edit'] is False
    assert client.get(base + '/report').status_code == 200
    assert client.patch(base, json=payload(revision=1, organization_id=team['id'])).status_code == 403
    assert client.post(base + '/analyze', json={'revision': 1}).status_code == 403
    assert client.post('/api/projects', json=payload(organization_id=team['id'])).status_code == 403
    as_user(client, 3)
    updated = client.patch(base, json=payload(name='Edição da equipe', revision=1, organization_id=team['id']))
    assert updated.status_code == 200
    assert client.post(base + '/analyze', json={'revision': 2}).status_code == 200
    assert client.patch(base, json=payload(revision=3, organization_id=None)).status_code == 409
    as_user(client, 4, 'governo')
    assert client.get(base).status_code == 404
    assert client.get(base + '/report').status_code == 404


def test_private_study_is_shared_explicitly_and_revocation_blocks_creator(client):
    team = team_with_members(client)
    as_user(client, 3)
    created = client.post('/api/projects', json=payload()).json()
    base = f"/api/projects/{created['id']}"
    as_user(client, 1)
    assert client.get(base).status_code == 404
    as_user(client, 3)
    assert client.post(base + '/share', json={'organization_id': team['id'], 'revision': 99}).status_code == 409
    assert client.get(base).json()['organization_id'] is None
    shared = client.post(base + '/share', json={'organization_id': team['id'], 'revision': 1})
    assert shared.status_code == 200
    assert shared.json()['revision'] == 2
    as_user(client, 1)
    assert client.get(base).status_code == 200
    assert client.delete(f"/api/organizations/{team['id']}/members/3").status_code == 204
    as_user(client, 3)
    assert client.get('/api/projects').json() == []
    assert client.get(base).status_code == 404
    assert client.get(base + '/report').status_code == 404


def test_downgrade_is_effective_without_changing_profile(client):
    team = team_with_members(client)
    created = client.post('/api/projects', json=payload(organization_id=team['id'])).json()
    assert client.patch(f"/api/organizations/{team['id']}/members/3", json={'role': 'viewer'}).status_code == 200
    as_user(client, 3, 'incorporadora')
    assert client.get(f"/api/projects/{created['id']}").json()['can_edit'] is False
    assert client.patch(f"/api/projects/{created['id']}", json=payload(revision=1, organization_id=team['id'])).status_code == 403


def test_adding_team_tables_preserves_legacy_private_study():
    import json
    engine = create_engine('sqlite://', poolclass=StaticPool)
    auth.Base.metadata.create_all(engine, tables=[auth.User.__table__, projects.LandStudy.__table__])
    factory = sessionmaker(bind=engine)
    with factory() as db:
        account = auth.User(name='Legacy', email='legacy@test.local', password_hash='unused')
        db.add(account); db.flush()
        study = projects.LandStudy(user_id=account.id, name='Projeto legado', revision=7, document=json.dumps({'analysis': None, 'notes': 'Preservar'}))
        db.add(study); db.commit()
        account_id, study_id = account.id, study.id
    auth.Base.metadata.create_all(engine)
    with factory() as db:
        restored = projects.serialize(projects.owned(db, auth.User(id=account_id), study_id))
        assert restored['organization_id'] is None
        assert restored['can_edit'] is True
        assert restored['revision'] == 7
        assert restored['notes'] == 'Preservar'
    engine.dispose()


def test_financial_assumptions_persist_recalculate_and_invalidate(client):
    financial = {'land_cost': 100000, 'construction_cost_m2': 1000, 'other_costs': 0, 'contingency_pct': 0,
                 'saleable_area_m2': 100, 'sale_price_m2': 3000, 'sales_expenses_pct': 0, 'months': 12,
                 'annual_discount_pct': 0, 'cost_variation_pct': 10, 'price_variation_pct': 10,
                 'reference_date': '2026-10-14', 'source_note': 'Premissas de teste'}
    created = client.post('/api/projects', json=payload(financial=financial)).json()
    base = f"/api/projects/{created['id']}"
    saved = client.post(base + '/analyze', json={'revision': 1}).json()
    assert saved['financial']['reference_date'] == '2026-10-14'
    assert saved['analysis']['financial']['scenarios'][0]['profit'] == 35000
    assert client.get(base).json()['analysis']['financial']['status'] == 'complete'
    report = client.get(base + '/report').text
    assert 'Estudo financeiro informado' in report
    assert 'Premissas de teste' in report
    assert '35000' in report
    financial['land_cost'] = 150000
    updated = client.patch(base, json=payload(financial=financial, revision=2)).json()
    assert updated['analysis'] is None
    recalculated = client.post(base + '/analyze', json={'revision':3}).json()
    assert recalculated['analysis']['financial']['scenarios'][0]['profit'] == -15000


def test_financial_draft_does_not_fabricate_results_and_saleable_area_is_validated(client):
    assert client.post('/api/projects', json=payload(financial={'saleable_area_m2': 200})).status_code == 422
    created = client.post('/api/projects', json=payload(financial={'land_cost': 0})).json()
    saved = client.post(f"/api/projects/{created['id']}/analyze", json={'revision': 1}).json()
    assert saved['analysis']['financial']['status'] == 'pending'
    assert 'scenarios' not in saved['analysis']['financial']


def test_history_is_atomic_ordered_and_private(client):
    created=client.post('/api/projects',json=payload()).json()
    base=f"/api/projects/{created['id']}"
    assert client.patch(base,json=payload(revision=99)).status_code==409
    assert len(client.get(base+'/history').json()['items'])==1
    assert client.patch(base,json=payload(revision=1,notes='Nova observação')).status_code==200
    assert client.post(base+'/analyze',json={'revision':2}).status_code==200
    items=client.get(base+'/history').json()['items']
    assert [item['revision'] for item in items]==[3,2,1]
    assert [item['action'] for item in items]==['analyzed','updated','created']
    assert items[1]['changed_fields']==['notes']
    assert items[0]['actor_name']=='User 1'
    assert client.get(base+'/history?before_revision=2').json()['items'][0]['revision']==1
    assert client.get(base+'/history?before_revision=-1').status_code==422
    assert 'Atividades registradas' in client.get(base+'/report').text
    as_user(client,2)
    assert client.get(base+'/history').status_code==404


def test_technical_snapshot_persists_and_changes_invalidate_results(client):
    created=client.post('/api/projects',json=payload(technical={'slope_pct':0,'water':'reported_unavailable'})).json()
    base=f"/api/projects/{created['id']}"
    saved=client.post(base+'/analyze',json={'revision':1}).json()
    assert saved['analysis']['technical']['assumptions']['slope_pct']==0
    assert saved['analysis']['technical']['unavailable']==['Água']
    assert 'Evidências técnicas do terreno' in client.get(base+'/report').text
    updated=client.patch(base,json=payload(revision=2,technical={'water':'reported_available'})).json()
    assert updated['analysis'] is None
    assert client.get(base+'/history').json()['items'][0]['changed_fields']==['technical']


def test_shared_history_records_actual_editor_and_revokes_access(client):
    team=team_with_members(client)
    created=client.post('/api/projects',json=payload(organization_id=team['id'])).json()
    base=f"/api/projects/{created['id']}"
    as_user(client,3)
    assert client.patch(base,json=payload(organization_id=team['id'],revision=1,notes='Revisão editorial')).status_code==200
    as_user(client,2)
    assert client.get(base+'/history').json()['items'][0]['actor_name']=='User 3'
    as_user(client,1)
    client.delete(f"/api/organizations/{team['id']}/members/2")
    as_user(client,2)
    assert client.get(base+'/history').status_code==404


@pytest.mark.parametrize('profile',['construtora','empreendedor'])
def test_new_profiles_register_without_granting_admin_or_team_permissions(client,profile):
    response=client.post('/api/auth/register',json={'name':'Novo perfil','email':profile+'@test.local','password':'test-only-password','profile':profile})
    assert response.status_code==200
    assert response.json()['role']==profile
    assert response.json()['is_admin'] is False


def test_workspace_preference_preserves_legacy_admin_role(client):
    with client.db_factory() as db:
        account=db.get(auth.User,1);account.role='admin';db.commit();db.refresh(account)
    client.test_app.dependency_overrides[auth.get_current_user]=lambda:account
    response=client.patch('/api/auth/me/profile',json={'profile':'construtora'})
    assert response.status_code==200
    assert response.json()['role']=='construtora'
    assert response.json()['is_admin'] is True
    with client.db_factory() as db:
        assert db.get(auth.User,1).role=='admin'
        assert db.get(auth.UserWorkspace,1).profile=='construtora'
    assert client.patch('/api/auth/me/profile',json={'profile':'admin'}).status_code==422


def test_history_pagination_has_no_duplicate_revisions(client):
    created=client.post('/api/projects',json=payload()).json()
    with client.db_factory() as db:
        for revision in range(2,57):
            db.add(projects.StudyEvent(project_id=created['id'],actor_id=1,actor_name='User 1',revision=revision,action='updated',occurred_at='2026-10-14T12:00:00+00:00',changed_fields='["notes"]'))
        db.commit()
    base=f"/api/projects/{created['id']}/history"
    page=client.get(base).json()
    assert len(page['items'])==50
    older=client.get(base+f"?before_revision={page['next_before_revision']}").json()
    all_revisions=[item['revision'] for item in page['items']+older['items']]
    assert all_revisions==list(range(56,0,-1))
    assert older['next_before_revision'] is None


def test_declared_analysis_works_without_h3_or_territorial_sources(client,monkeypatch):
    def unexpected(): raise AssertionError('Territorial lookup must not run in declared-only mode')
    monkeypatch.setattr(projects,'get_scores',unexpected)
    created=client.post('/api/projects',json=payload(h3_id=None,technical={'slope_pct':0})).json()
    base=f"/api/projects/{created['id']}"
    response=client.post(base+'/analyze-premises',json={'revision':1})
    assert response.status_code==200
    result=response.json()['analysis']
    assert result['mode']=='premises_only'
    assert result['legal']['status']=='analisar'
    assert result['technical']['assumptions']['slope_pct']==0
    assert result['concept']['scenarios']==[]
    assert 'contexto territorial não consultado' in client.get(base+'/report').text
    assert client.get(base+'/history').json()['items'][0]['action']=='premises_analyzed'
    assert client.post(base+'/analyze-premises',json={'revision':1}).status_code==409
    as_user(client,2)
    assert client.post(base+'/analyze-premises',json={'revision':2}).status_code==404


def test_declared_analysis_rejects_empty_study_and_reader(client):
    empty=client.post('/api/projects',json=payload(h3_id=None)).json()
    assert client.post(f"/api/projects/{empty['id']}/analyze-premises",json={'revision':1}).status_code==422
    team=team_with_members(client)
    created=client.post('/api/projects',json=payload(organization_id=team['id'],technical={})).json()
    as_user(client,2)
    assert client.post(f"/api/projects/{created['id']}/analyze-premises",json={'revision':1}).status_code==403


@pytest.mark.parametrize('premises',[{'buildArea':1e100},{'residentialScore':101},{'riskConfidence':2},{'latitude':91}])
def test_project_rejects_unsupported_premise_ranges(client,premises):
    assert client.post('/api/projects',json=payload(premises=premises)).status_code==422


def test_commercial_snapshot_report_and_criteria_invalidation(client, monkeypatch):
    from test_business_study import criteria
    monkeypatch.setattr(projects, 'get_scores', lambda: [{'h3_id': CELL, 'pop_estimated': 1200,
        'poi_pharmacy_cnt': 0, 'dist_min_pharmacy_m': 600, 'score_updated_at': '2026-10-15T12:00:00Z'}])
    created = client.post('/api/projects', json=payload(business=criteria())).json()
    base = f"/api/projects/{created['id']}"
    response = client.post(base + '/analyze', json={'revision': 1})
    assert response.status_code == 200
    saved = response.json()
    assert saved['analysis']['business']['mapped_establishments'] == 0
    assert saved['analysis']['business']['status'] == 'ready_for_market_research'
    report = client.get(base + '/report').text
    assert 'Localização comercial' in report and 'Hipótese a investigar' in report
    assert '2026-10-15T12:00:00Z' in report
    saved['business']['sector'] = 'market'
    updated = client.patch(base, json=saved)
    assert updated.status_code == 200
    assert updated.json()['analysis'] is None
    assert 'business' in client.get(base + '/history').json()['items'][0]['changed_fields']


def test_commercial_only_calculation_requires_no_territorial_lookup(client, monkeypatch):
    from test_business_study import criteria
    def unavailable():
        raise AssertionError('Premises calculation must not consult territorial data')
    monkeypatch.setattr(projects, 'get_scores', unavailable)
    created = client.post('/api/projects', json=payload(h3_id=None, business=criteria())).json()
    response = client.post(f"/api/projects/{created['id']}/analyze-premises", json={'revision': 1})
    assert response.status_code == 200
    result = response.json()['analysis']['business']
    assert result['status'] == 'territorial_data_pending'
    assert result['population_estimate'] is None
