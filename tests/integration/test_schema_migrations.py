import os
import shutil
import uuid
from dataclasses import replace

import pytest
from sqlalchemy import text

from recomendacao_imobiliaria.config import load_settings
from recomendacao_imobiliaria.db import make_engine
from recomendacao_imobiliaria.schema_migrations import MIGRATIONS, migrate_database

pytestmark = pytest.mark.skipif(os.getenv("RUN_POSTGIS_INTEGRATION") != "1", reason="requer PostGIS isolado")


@pytest.fixture
def empty_database():
    settings = load_settings()
    name = "migration_test_" + uuid.uuid4().hex
    admin = make_engine(settings).execution_options(isolation_level="AUTOCOMMIT")
    with admin.connect() as conn:
        conn.exec_driver_sql(f'CREATE DATABASE "{name}"')
    try:
        yield replace(settings, pg_db=name)
    finally:
        with admin.connect() as conn:
            conn.exec_driver_sql(f'DROP DATABASE "{name}" WITH (FORCE)')
        admin.dispose()


def test_new_database_repeat_and_checksum(empty_database, tmp_path):
    result = migrate_database(empty_database)
    assert len(result["applied"]) == 12
    assert migrate_database(empty_database)["applied"] == []
    engine = make_engine(empty_database)
    try:
        with engine.begin() as conn:
            conn.execute(text("INSERT INTO users(name,email,password_hash) VALUES ('fixture','fixture@urbia.test','hash')"))
        migrate_database(empty_database)
        with engine.connect() as conn:
            assert conn.execute(text("SELECT COUNT(*) FROM users")).scalar() == 1
        shutil.copytree(MIGRATIONS, tmp_path / "sql")
        altered = tmp_path / "sql" / "011_application_tables.sql"
        altered.write_text(altered.read_text() + "\n-- changed")
        with pytest.raises(RuntimeError, match="alterada"):
            migrate_database(empty_database, directory=altered.parent)
    finally:
        engine.dispose()


def test_refuses_untracked_database(empty_database):
    engine = make_engine(empty_database)
    try:
        with engine.begin() as conn:
            conn.execute(text("CREATE TABLE users(id INT)"))
        with pytest.raises(RuntimeError, match="baseline"):
            migrate_database(empty_database)
        with engine.connect() as conn:
            assert conn.execute(text("SELECT to_regclass('ops.schema_migrations')")).scalar() is None
    finally:
        engine.dispose()


def test_failed_migration_rolls_back(empty_database, tmp_path):
    (tmp_path / "001_broken.sql").write_text("CREATE TABLE marker(id INT); SELECT missing_column;")
    with pytest.raises(Exception):
        migrate_database(empty_database, directory=tmp_path)
    engine = make_engine(empty_database)
    try:
        with engine.connect() as conn:
            assert conn.execute(text("SELECT to_regclass('public.marker')")).scalar() is None
            assert conn.execute(text("SELECT to_regclass('ops.schema_migrations')")).scalar() is None
    finally:
        engine.dispose()
