import datetime
import logging
import jwt
from functools import lru_cache
from typing import Optional
from passlib.context import CryptContext
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from pydantic import BaseModel
from sqlalchemy import Column, Integer, String, create_engine
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

PROFILE_IDS = {"investidor", "corretor", "incorporadora", "governo"}

# --- DB Models ---
class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=False)
    role = Column(String, default="client")

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
    to_encode.update({"exp": expire})
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
    return user

# --- Routes ---
router = APIRouter()

@router.post("/auth/register", response_model=UserResponse)
def register(user_data: UserCreate, db = Depends(get_db)):
    existing_user = db.query(User).filter(User.email == user_data.email).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="Email ja cadastrado")
    
    if user_data.profile not in PROFILE_IDS:
        raise HTTPException(status_code=422, detail="Perfil de acesso invalido")

    hashed_pw = get_password_hash(user_data.password)
    # O campo role tambem representa o perfil de uso nesta primeira versao.
    db_user = User(name=user_data.name, email=user_data.email, password_hash=hashed_pw, role=user_data.profile)
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

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
def read_users_me(current_user: User = Depends(get_current_user)):
    return current_user


@router.patch("/auth/me/profile", response_model=UserResponse)
def update_my_profile(profile_data: UserProfileUpdate, current_user: User = Depends(get_current_user), db = Depends(get_db)):
    if profile_data.profile not in PROFILE_IDS:
        raise HTTPException(status_code=422, detail="Perfil de acesso invalido")

    current_user.role = profile_data.profile
    db.commit()
    db.refresh(current_user)
    return current_user
