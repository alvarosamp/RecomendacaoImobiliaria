import datetime
import logging
import hashlib
import secrets
import time
import jwt
from functools import lru_cache
from typing import Optional
from passlib.context import CryptContext
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import Column, Integer, String, Float, ForeignKey, create_engine, update
from sqlalchemy.orm import declarative_base, sessionmaker

from recomendacao_imobiliaria.config import load_settings

# --- Config & Setup ---
settings = load_settings()
SECRET_KEY = settings.jwt_secret
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7 # 7 days

log = logging.getLogger(__name__)

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")

engine = create_engine(settings.database_url, future=True, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

PROFILE_IDS = {"investidor", "corretor", "incorporadora", "governo", "construtora", "empreendedor"}

# --- DB Models ---
class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=False)
    role = Column(String, default="client")

    @property
    def is_admin(self) -> bool:
        # A preferência de ambiente é separada; preserva o papel legado e ADMIN_EMAILS.
        return self.role == "admin" or (self.email or "").lower() in settings.admin_emails

class UserWorkspace(Base):
    __tablename__ = 'user_workspaces'
    user_id = Column(Integer, ForeignKey('users.id'), primary_key=True)
    profile = Column(String(32), nullable=False)


class PasswordRecovery(Base):
    __tablename__ = 'password_recoveries'
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False, index=True)
    token_hash = Column(String(64), unique=True, nullable=False)
    expires_at = Column(Float, nullable=False)
    used_at = Column(Float, nullable=True)


class UserSessionState(Base):
    __tablename__ = 'user_session_state'
    user_id = Column(Integer, ForeignKey('users.id'), primary_key=True)
    valid_after_epoch = Column(Float, nullable=False)


def user_response(user, db):
    workspace = db.get(UserWorkspace, user.id)
    profile = workspace.profile if workspace else user.role if user.role in PROFILE_IDS else 'investidor'
    return {'id': user.id, 'name': user.name, 'email': user.email, 'role': profile, 'is_admin': user.is_admin}


@lru_cache(maxsize=1)
def ensure_auth_schema() -> None:
    """Cria a tabela de contas na primeira requisicao que precisa do banco.

    Evita que importar a API bloqueie quando o PostGIS estiver temporariamente
    indisponivel, algo comum em testes, healthchecks e inicializacao de containers.
    """
    Base.metadata.create_all(bind=engine)

# --- Pydantic Models ---
class UserCreate(BaseModel):
    name: str
    email: str
    password: str
    # Mantem compatibilidade com integracoes e contas legadas que ainda nao
    # enviam o perfil; o frontend, por sua vez, exige a escolha explicita.
    profile: str = "investidor"
    invitation_code: str = Field('', max_length=200)

class UserProfileUpdate(BaseModel):
    profile: str

class UserLogin(BaseModel):
    email: str
    password: str

class UserResponse(BaseModel):
    id: int
    name: str
    email: str
    role: str
    is_admin: bool = False

class Token(BaseModel):
    access_token: str
    token_type: str

# --- Utils ---
def get_db():
    try:
        ensure_auth_schema()
    except Exception as exc:
        log.warning("Nao foi possivel criar/verificar tabelas no Postgres: %s", exc)
        raise HTTPException(status_code=503, detail="Banco de dados indisponivel") from exc
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: Optional[datetime.timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.datetime.utcnow() + expires_delta
    else:
        expire = datetime.datetime.utcnow() + datetime.timedelta(minutes=15)
    to_encode.update({"exp": expire, 'iat': time.time()})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def get_current_user(token: str = Depends(oauth2_scheme), db = Depends(get_db)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Nao foi possivel validar as credenciais",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception
    except jwt.PyJWTError:
        raise credentials_exception
    
    user = db.query(User).filter(User.email == email).first()
    if user is None:
        raise credentials_exception
    state = db.get(UserSessionState, user.id)
    if state and float(payload.get('iat', 0)) < state.valid_after_epoch:
        raise credentials_exception
    return user


def require_admin(current_user: User = Depends(get_current_user)):
    if not current_user.is_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Acao restrita a administradores")
    return current_user

# --- Routes ---
router = APIRouter()

@router.post("/auth/register", response_model=UserResponse)
def register(user_data: UserCreate, db = Depends(get_db)):
    if settings.demo_registration_code:
        accepted = secrets.compare_digest(user_data.invitation_code.encode(),settings.demo_registration_code.encode())
        allowed = settings.demo_allowed_emails + settings.admin_emails
        if not accepted or (allowed and user_data.email.strip().lower() not in allowed):
            raise HTTPException(403,'Demonstração reservada a parceiros. Confira o código e o email autorizados com o responsável.')
    existing_user = db.query(User).filter(User.email == user_data.email).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="Email ja cadastrado")
    
    if user_data.profile not in PROFILE_IDS:
        raise HTTPException(status_code=422, detail="Perfil de acesso invalido")

    hashed_pw = get_password_hash(user_data.password)
    db_user = User(name=user_data.name, email=user_data.email, password_hash=hashed_pw, role='client')
    db.add(db_user)
    db.flush()
    db.add(UserWorkspace(user_id=db_user.id, profile=user_data.profile))
    db.commit()
    db.refresh(db_user)
    return user_response(db_user, db)

@router.post("/auth/login", response_model=Token)
def login(user_data: UserLogin, db = Depends(get_db)):
    user = db.query(User).filter(User.email == user_data.email).first()
    if not user or not verify_password(user_data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email ou senha incorretos",
        )
    
    access_token_expires = datetime.timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.email, "role": user.role}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}

@router.get("/auth/me", response_model=UserResponse)
def read_users_me(current_user: User = Depends(get_current_user), db = Depends(get_db)):
    return user_response(current_user, db)


@router.patch("/auth/me/profile", response_model=UserResponse)
def update_my_profile(profile_data: UserProfileUpdate, current_user: User = Depends(get_current_user), db = Depends(get_db)):
    if profile_data.profile not in PROFILE_IDS:
        raise HTTPException(status_code=422, detail="Perfil de acesso invalido")

    workspace = db.get(UserWorkspace, current_user.id)
    if workspace is None:
        db.add(UserWorkspace(user_id=current_user.id, profile=profile_data.profile))
    else:
        workspace.profile = profile_data.profile
    db.commit()
    return user_response(current_user, db)


class RecoveryIssue(BaseModel):
    email: str = Field(min_length=3, max_length=320)


class RecoveryComplete(BaseModel):
    token: str = Field(min_length=32, max_length=128)
    password: str = Field(min_length=10, max_length=72)

    @field_validator('password')
    @classmethod
    def password_bytes(cls, value):
        if len(value.encode('utf-8')) > 72: raise ValueError('Senha deve ter até 72 bytes')
        return value


@router.post('/auth/recovery/issue')
def issue_recovery(payload: RecoveryIssue, admin: User = Depends(require_admin), db = Depends(get_db)):
    account = db.query(User).filter_by(email=payload.email.strip()).first()
    if account is None: raise HTTPException(404, 'Conta não encontrada')
    token = secrets.token_urlsafe(32)
    db.query(PasswordRecovery).filter_by(user_id=account.id).delete()
    db.add(PasswordRecovery(user_id=account.id, token_hash=hashlib.sha256(token.encode()).hexdigest(), expires_at=time.time()+900))
    db.commit()
    return dict(token=token, expires_in_seconds=900, instruction='Código de uso único. Entregue ao titular por um canal verificado; a plataforma não envia mensagens.')


@router.post('/auth/recovery/complete', status_code=204)
def complete_recovery(payload: RecoveryComplete, db = Depends(get_db)):
    recovery = db.query(PasswordRecovery).filter_by(token_hash=hashlib.sha256(payload.token.encode()).hexdigest()).first()
    timestamp = time.time()
    if recovery is None or recovery.used_at is not None or recovery.expires_at <= timestamp:
        raise HTTPException(400, 'Código inválido ou expirado. Solicite um novo código ao responsável pela demonstração.')
    hashed = get_password_hash(payload.password)
    changed = db.execute(update(PasswordRecovery).where(PasswordRecovery.id==recovery.id, PasswordRecovery.used_at.is_(None), PasswordRecovery.expires_at>timestamp).values(used_at=timestamp))
    if changed.rowcount != 1:
        db.rollback()
        raise HTTPException(400, 'Código inválido ou expirado')
    account = db.get(User, recovery.user_id)
    account.password_hash = hashed
    state = db.get(UserSessionState, account.id)
    if state: state.valid_after_epoch = timestamp
    else: db.add(UserSessionState(user_id=account.id, valid_after_epoch=timestamp))
    db.commit()
