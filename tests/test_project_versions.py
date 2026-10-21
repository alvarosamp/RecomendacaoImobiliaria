"""Immutable revision captures, recovery and current-access enforcement."""
import json
import pytest

from api.routes import projects
from test_land_projects import client, payload, as_user, team_with_members


def test_snapshots_keep_values_and_recovery_creates_revision_without_old_analysis(client):
    created = client.post('/api/projects', json=payload(technical={'slope_pct': 0})).json()
    base = f"/api/projects/{created['id']}"
    analyzed = client.post(base + '/analyze', json={'revision': 1}).json()
    assert analyzed['revision'] == 2
    edited = client.patch(base, json={**analyzed, 'name': 'Nova hipótese', 'premises': {'lotArea': 900}}).json()
    historical = client.get(base + '/versions/2').json()
    assert historical['inputs']['premises']['lotArea'] == 300
    assert historical['analysis'] == analyzed['analysis']
    assert historical['current_revision'] == 3
    assert {'field': 'premises.lotArea', 'historical': 300, 'current': 900} in historical['differences']
    response = client.post(base + '/versions/2/restore', json={'revision': 3})
    assert response.status_code == 200
    restored = response.json()
    assert restored['revision'] == 4
    assert restored['name'] == created['name']
    assert restored['premises']['lotArea'] == 300
    assert restored['technical']['slope_pct'] == 0
    assert restored['analysis'] is None
    assert restored['created_at'] == created['created_at']
    assert client.get(base + '/versions/2').json()['analysis'] == historical['analysis']
    assert client.get(base + '/versions/3').json()['inputs']['name'] == edited['name']
    event = client.get(base + '/history').json()['items'][0]
    assert event['action'] == 'restored' and event['restored_from_revision'] == 2
    assert event['snapshot_available'] is True
    assert 'premissas recuperadas da revisão 2' in client.get(base + '/report').text


def test_stale_missing_and_current_revision_recovery_do_not_write(client):
    created = client.post('/api/projects', json=payload()).json()
    base = f"/api/projects/{created['id']}"
    assert client.get(base + '/versions/99').status_code == 404
    assert client.get(base + '/versions/0').status_code == 422
    assert client.post(base + '/versions/1/restore', json={'revision': 1}).status_code == 409
    assert client.patch(base, json=payload(revision=1, notes='Nova nota')).status_code == 200
    assert client.post(base + '/versions/1/restore', json={'revision': 1}).status_code == 409
    assert client.post(base + '/versions/99/restore', json={'revision': 2}).status_code == 404
    with client.db_factory() as db:
        assert db.query(projects.StudyVersion).count() == 2
        assert db.query(projects.StudyEvent).count() == 2
    assert client.get(base).json()['revision'] == 2
    as_user(client, 2)
    assert client.get(base + '/versions/1').status_code == 404
    assert client.post(base + '/versions/1/restore', json={'revision': 2}).status_code == 404


def test_recovery_keeps_current_team_and_revoked_members_lose_old_private_snapshots(client):
    team = team_with_members(client)
    created = client.post('/api/projects', json=payload()).json()
    base = f"/api/projects/{created['id']}"
    assert client.post(base + '/share', json={'revision': 1, 'organization_id': team['id']}).status_code == 200
    as_user(client, 2)
    assert client.get(base + '/versions/1').status_code == 200
    assert client.post(base + '/versions/1/restore', json={'revision': 2}).status_code == 403
    as_user(client, 3)
    restored = client.post(base + '/versions/1/restore', json={'revision': 2})
    assert restored.status_code == 200
    assert restored.json()['organization_id'] == team['id']
    assert client.get(base + '/history').json()['items'][0]['actor_name'] == 'User 3'
    as_user(client, 1)
    assert client.delete(f"/api/organizations/{team['id']}/members/2").status_code == 204
    as_user(client, 2)
    assert client.get(base + '/versions/1').status_code == 404


def test_legacy_baseline_preserves_only_last_known_values(client):
    created = client.post('/api/projects', json=payload()).json()
    base = f"/api/projects/{created['id']}"
    with client.db_factory() as db:
        db.query(projects.StudyEvent).delete()
        db.query(projects.StudyVersion).delete()
        record = db.get(projects.LandStudy, created['id'])
        record.revision = 7
        db.commit()
    assert client.get(base + '/versions/7').status_code == 404
    assert client.patch(base, json=payload(revision=7, notes='Primeira alteração nova')).status_code == 200
    assert client.get(base + '/versions/7').json()['inputs']['notes'] == ''
    assert client.get(base + '/versions/6').status_code == 404
    history = client.get(base + '/history').json()
    assert [event['revision'] for event in history['items']] == [8]
    assert history['baseline_snapshot']['revision'] == 7


def test_failed_event_rolls_back_document_and_snapshots(client, monkeypatch):
    created = client.post('/api/projects', json=payload()).json()
    def failure(*args, **kwargs):
        raise RuntimeError('controlled transaction failure')
    monkeypatch.setattr(projects, 'record_event', failure)
    with pytest.raises(RuntimeError, match='controlled transaction failure'):
        client.patch(f"/api/projects/{created['id']}", json=payload(revision=1, notes='Não salvar'))
    with client.db_factory() as db:
        assert db.query(projects.StudyVersion).count() == 1
        assert db.get(projects.LandStudy, created['id']).revision == 1
        assert json.loads(db.get(projects.LandStudy, created['id']).document)['notes'] == ''


def test_historical_values_revalidated_before_recovery(client):
    created = client.post('/api/projects', json=payload()).json()
    base = f"/api/projects/{created['id']}"
    client.patch(base, json=payload(revision=1, notes='Atual'))
    with client.db_factory() as db:
        version = db.query(projects.StudyVersion).filter_by(project_id=created['id'], revision=1).one()
        old = json.loads(version.document)
        old['premises']['lotArea'] = -10
        version.document = json.dumps(old)
        db.commit()
    assert client.post(base + '/versions/1/restore', json={'revision': 2}).status_code == 422
    assert client.get(base).json()['revision'] == 2
