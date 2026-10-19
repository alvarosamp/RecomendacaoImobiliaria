import hashlib
import pytest
from api.routes import auth
from test_land_projects import client,as_user

def test_recovery_requires_admin_is_single_use_and_revokes_sessions(client):
    as_user(client,1)
    assert client.post('/api/auth/recovery/issue',json={'email':'2@test.local'}).status_code==403
    as_user(client,1,'admin')
    response=client.post('/api/auth/recovery/issue',json={'email':'2@test.local'})
    assert response.status_code==200
    token=response.json()['token']
    with client.db_factory() as db:
        recovery=db.query(auth.PasswordRecovery).one()
        assert recovery.token_hash==hashlib.sha256(token.encode()).hexdigest()
        account=db.get(auth.User,2);account.password_hash=auth.get_password_hash('previous-password');db.commit()
    client.test_app.dependency_overrides.pop(auth.get_current_user)
    old=client.post('/api/auth/login',json={'email':'2@test.local','password':'previous-password'}).json()['access_token']
    assert client.get('/api/auth/me',headers={'Authorization':'Bearer '+old}).status_code==200
    completed=client.post('/api/auth/recovery/complete',json={'token':token,'password':'new-strong-password'})
    assert completed.status_code==204
    assert client.post('/api/auth/recovery/complete',json={'token':token,'password':'other-password'}).status_code==400
    assert client.get('/api/auth/me',headers={'Authorization':'Bearer '+old}).status_code==401
    assert client.post('/api/auth/login',json={'email':'2@test.local','password':'previous-password'}).status_code==401
    new=client.post('/api/auth/login',json={'email':'2@test.local','password':'new-strong-password'}).json()['access_token']
    assert client.get('/api/auth/me',headers={'Authorization':'Bearer '+new}).status_code==200

def test_new_code_invalidates_old_and_expired_code_is_rejected(client):
    as_user(client,1,'admin')
    old=client.post('/api/auth/recovery/issue',json={'email':'2@test.local'}).json()['token']
    new=client.post('/api/auth/recovery/issue',json={'email':'2@test.local'}).json()['token']
    assert client.post('/api/auth/recovery/complete',json={'token':old,'password':'valid-password'}).status_code==400
    with client.db_factory() as db:
        row=db.query(auth.PasswordRecovery).one();row.expires_at=0;db.commit()
    assert client.post('/api/auth/recovery/complete',json={'token':new,'password':'valid-password'}).status_code==400
    assert client.post('/api/auth/recovery/complete',json={'token':new,'password':'short'}).status_code==422

def test_partner_registration_code_and_allowlist(client,monkeypatch):
    from dataclasses import replace
    monkeypatch.setattr(auth,'settings',replace(auth.settings,demo_registration_code='private-test-code',demo_allowed_emails=('partner@test.local',)))
    data={'name':'Parceiro','email':'partner@test.local','password':'testing-password','profile':'investidor'}
    assert client.post('/api/auth/register',json=data).status_code==403
    assert client.post('/api/auth/register',json={**data,'email':'other@test.local','invitation_code':'private-test-code'}).status_code==403
    assert client.post('/api/auth/register',json={**data,'invitation_code':'private-test-code'}).status_code==200
