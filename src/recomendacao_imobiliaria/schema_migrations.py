"""Explicit, transactional SQL migrations for new databases.

Existing databases without a migration ledger are refused until audited.
"""
from hashlib import sha256
from pathlib import Path

from sqlalchemy import text

from .config import load_settings
from .db import make_engine


MIGRATIONS = Path(__file__).with_name("migrations")


def migrate_database(settings=None, *, directory=MIGRATIONS):
    files = sorted(Path(directory).glob("*.sql"))
    if not files:
        raise ValueError("Nenhuma migration SQL encontrada")
    engine = make_engine(settings or load_settings())
    applied = []
    try:
        with engine.begin() as conn:
            conn.execute(text("SELECT pg_advisory_xact_lock(3152501005)"))
            ledger = conn.execute(text("SELECT to_regclass('ops.schema_migrations')")).scalar()
            if ledger is None:
                tables = conn.execute(text("""
                    SELECT schemaname, tablename FROM pg_tables
                    WHERE schemaname IN ('geo', 'market', 'ops')
                       OR (schemaname='public' AND tablename IN ('users', 'leads', 'regs'))
                """)).all()
                if tables:
                    raise RuntimeError("Banco existente sem baseline auditada; migracao recusada")
                conn.execute(text("CREATE SCHEMA IF NOT EXISTS ops"))
                conn.execute(text("""
                    CREATE TABLE ops.schema_migrations (
                        version TEXT PRIMARY KEY, checksum_sha256 TEXT NOT NULL,
                        applied_at TIMESTAMPTZ NOT NULL DEFAULT now()
                    )
                """))
            recorded = dict(conn.execute(text("SELECT version, checksum_sha256 FROM ops.schema_migrations")).all())
            available = {file.name: sha256(file.read_bytes()).hexdigest() for file in files}
            for version, checksum in recorded.items():
                if available.get(version) != checksum:
                    raise RuntimeError(f"Migration aplicada ausente ou alterada: {version}")
            for file in files:
                if file.name in recorded:
                    continue
                if recorded and file.name < max(recorded):
                    raise RuntimeError(f"Migration fora de ordem: {file.name}")
                conn.exec_driver_sql(file.read_text(encoding="utf-8-sig"))
                conn.execute(text("INSERT INTO ops.schema_migrations (version, checksum_sha256) VALUES (:v, :c)"),
                             {"v": file.name, "c": available[file.name]})
                applied.append(file.name)
    finally:
        engine.dispose()
    return {"applied": applied, "schema_version": files[-1].name}
