from __future__ import annotations

import argparse
import getpass
import os
import secrets
import string
import sys
from pathlib import Path

from passlib.context import CryptContext
from sqlalchemy import Column, Integer, String, create_engine
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import declarative_base, sessionmaker

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
sys.path.insert(0, str(SRC))

from recomendacao_imobiliaria.config import load_settings  # noqa: E402

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
Base = declarative_base()


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=False)
    role = Column(String, default="client")


def generate_password(length: int = 14) -> str:
    alphabet = string.ascii_letters + string.digits + "!@#$%&*"
    while True:
      password = "".join(secrets.choice(alphabet) for _ in range(length))
      if (
          any(ch.islower() for ch in password)
          and any(ch.isupper() for ch in password)
          and any(ch.isdigit() for ch in password)
          and any(ch in "!@#$%&*" for ch in password)
      ):
          return password


def main() -> int:
    parser = argparse.ArgumentParser(description="Cria ou atualiza um login local da Urbia.")
    parser.add_argument("--name", default="Vish", help="Nome do usuario.")
    parser.add_argument("--email", default="vish@urbia.local", help="Email de login.")
    parser.add_argument("--password", help="Senha. Se omitida, sera solicitada.")
    parser.add_argument("--generate-password", action="store_true", help="Gera uma senha forte automaticamente.")
    parser.add_argument("--role", default="admin", choices=["admin", "client"], help="Perfil de acesso.")
    parser.add_argument("--pg-port", type=int, default=None, help="Porta do Postgres local, ex.: 5433 quando usar docker-compose.")
    args = parser.parse_args()

    if args.pg_port:
        os.environ["PG_PORT"] = str(args.pg_port)

    password = args.password
    if args.generate_password:
        password = generate_password()
    elif not password:
        password = getpass.getpass("Senha: ")

    if not password or len(password) < 6:
        print("A senha precisa ter pelo menos 6 caracteres.")
        return 2

    settings = load_settings()
    engine = create_engine(settings.database_url, future=True, pool_pre_ping=True)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    try:
        Base.metadata.create_all(bind=engine)
        with SessionLocal() as db:
            email = args.email.strip().lower()
            user = db.query(User).filter(User.email == email).first()
            password_hash = pwd_context.hash(password)

            if user:
                user.name = args.name
                user.password_hash = password_hash
                user.role = args.role
                action = "atualizado"
            else:
                user = User(
                    name=args.name,
                    email=email,
                    password_hash=password_hash,
                    role=args.role,
                )
                db.add(user)
                action = "criado"

            db.commit()
    except OperationalError as exc:
        print("Nao consegui conectar ao Postgres.")
        print(f"Banco configurado: {settings.pg_host}:{settings.pg_port}/{settings.pg_db}")
        print(str(exc).splitlines()[0])
        return 1

    print(f"Login {action} com sucesso.")
    print(f"Email: {args.email.strip().lower()}")
    if args.generate_password:
        print(f"Senha: {password}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
