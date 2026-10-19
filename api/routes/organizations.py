"""Team permissions are independent of the user's workspace profile."""
from typing import Literal
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import Column, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from .auth import Base, User, get_current_user, get_db

router = APIRouter(tags=['organizations'])


class Organization(Base):
    __tablename__ = 'organizations'
    id = Column(Integer, primary_key=True)
    name = Column(String(160), nullable=False)
    owner_id = Column(Integer, ForeignKey('users.id'), nullable=False)


class Membership(Base):
    __tablename__ = 'organization_members'
    id = Column(Integer, primary_key=True)
    organization_id = Column(Integer, ForeignKey('organizations.id'), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False, index=True)
    role = Column(String(16), nullable=False)
    __table_args__ = (UniqueConstraint('organization_id', 'user_id'),)


class ProjectOrganization(Base):
    __tablename__ = 'project_organizations'
    project_id = Column(Integer, ForeignKey('land_studies.id'), primary_key=True)
    organization_id = Column(Integer, ForeignKey('organizations.id'), nullable=False, index=True)


class OrganizationInput(BaseModel):
    name: str = Field(min_length=1, max_length=160)

    @field_validator('name')
    @classmethod
    def clean_name(cls, value):
        if not value.strip(): raise ValueError('Informe o nome da equipe')
        return value.strip()


class MemberRole(BaseModel):
    role: Literal['editor', 'viewer']


class MemberInput(MemberRole):
    email: str = Field(min_length=3, max_length=320)


def membership(db, organization_id, user_id, write=False, owner=False):
    member = db.query(Membership).filter_by(organization_id=organization_id, user_id=user_id).first()
    if member is None: raise HTTPException(404, 'Equipe não encontrada')
    if owner and member.role != 'owner': raise HTTPException(403, 'Somente o responsável pode gerenciar membros')
    if write and member.role not in {'owner', 'editor'}: raise HTTPException(403, 'Acesso somente para leitura')
    return member


def commit(db):
    try: db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(409, 'Membro já cadastrado ou registro alterado. Atualize a equipe.') from exc


@router.get('/organizations')
def list_organizations(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return [{'id': org.id, 'name': org.name, 'role': member.role} for org, member in
            db.query(Organization, Membership).join(Membership, Membership.organization_id == Organization.id)
            .filter(Membership.user_id == user.id).order_by(Organization.name).all()]


@router.post('/organizations', status_code=201)
def create_organization(payload: OrganizationInput, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    org = Organization(name=payload.name, owner_id=user.id)
    db.add(org); db.flush()
    db.add(Membership(organization_id=org.id, user_id=user.id, role='owner'))
    commit(db)
    return {'id': org.id, 'name': org.name, 'role': 'owner'}


@router.get('/organizations/{organization_id}/members')
def list_members(organization_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    membership(db, organization_id, user.id, owner=True)
    return [{'user_id': account.id, 'name': account.name, 'email': account.email, 'role': member.role} for member, account in
            db.query(Membership, User).join(User, User.id == Membership.user_id).filter(Membership.organization_id == organization_id).all()]


@router.post('/organizations/{organization_id}/members', status_code=201)
def add_member(organization_id: int, payload: MemberInput, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    membership(db, organization_id, user.id, owner=True)
    # Account lookup matches the authentication system's exact email semantics.
    account = db.query(User).filter_by(email=payload.email.strip()).first()
    if account is None: raise HTTPException(404, 'Conta não encontrada. O membro precisa se cadastrar primeiro.')
    db.add(Membership(organization_id=organization_id, user_id=account.id, role=payload.role))
    commit(db)
    return {'user_id': account.id, 'name': account.name, 'email': account.email, 'role': payload.role}


@router.patch('/organizations/{organization_id}/members/{user_id}')
def change_member(organization_id: int, user_id: int, payload: MemberRole, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    membership(db, organization_id, user.id, owner=True)
    target = membership(db, organization_id, user_id)
    if target.role == 'owner': raise HTTPException(409, 'O responsável da equipe não pode ser rebaixado')
    target.role = payload.role
    commit(db)
    return {'user_id': user_id, 'role': target.role}


@router.delete('/organizations/{organization_id}/members/{user_id}', status_code=204)
def remove_member(organization_id: int, user_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    membership(db, organization_id, user.id, owner=True)
    target = membership(db, organization_id, user_id)
    if target.role == 'owner': raise HTTPException(409, 'O responsável da equipe não pode ser removido')
    db.delete(target)
    commit(db)
