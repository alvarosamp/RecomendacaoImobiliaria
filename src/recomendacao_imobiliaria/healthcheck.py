from __future__ import annotations

import dataclasses
from pathlib import Path

from sqlalchemy import text

from .config import Settings, load_settings
from .db import db_engine
from .official_sources import validate_official_data


@dataclasses.dataclass(frozen=True)
class CheckItem:
    name: str
    status: str
    details: str


@dataclasses.dataclass(frozen=True)
class HealthcheckResult:
    status: str
    checks: list[CheckItem]

    def as_dict(self) -> dict[str, object]:
        return {
            "status": self.status,
            "checks": [dataclasses.asdict(check) for check in self.checks],
        }


EXPECTED_TABLES = [
    "geo.city_boundary",
    "geo.grid_h3",
    "geo.osm_pois",
    "geo.indices",
    "geo.features",
    "geo.scores",
    "geo.zoning",
]


def run_healthcheck(settings: Settings | None = None) -> HealthcheckResult:
    settings = settings or load_settings()
    checks: list[CheckItem] = []
    checks.extend(_filesystem_checks())
    checks.extend(_official_data_checks())
    checks.extend(_database_checks(settings))

    status = "ok"
    if any(check.status == "fail" for check in checks):
        status = "fail"
    elif any(check.status == "warn" for check in checks):
        status = "warn"

    return HealthcheckResult(status=status, checks=checks)


def _filesystem_checks() -> list[CheckItem]:
    checks = []
    for path in ["config/scoring_weights.json", "config/plan_director_pouso_alegre.json", "app/streamlit_app.py"]:
        exists = Path(path).exists()
        checks.append(
            CheckItem(
                name=f"file:{path}",
                status="ok" if exists else "fail",
                details="encontrado" if exists else "arquivo ausente",
            )
        )
    return checks


def _official_data_checks() -> list[CheckItem]:
    status = validate_official_data()
    if status.ready_for_zoning_import:
        return [CheckItem("official_data", "ok", "zoneamento oficial encontrado")]
    return [
        CheckItem(
            "official_data",
            "warn",
            "zoneamento oficial ainda nao encontrado em data/official",
        )
    ]


def _database_checks(settings: Settings) -> list[CheckItem]:
    checks: list[CheckItem] = []
    try:
        with db_engine(settings) as engine:
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
                checks.append(CheckItem("database", "ok", "conexao com PostGIS estabelecida"))

                for table_name in EXPECTED_TABLES:
                    schema, table = table_name.split(".")
                    exists = conn.execute(
                        text(
                            """
                            SELECT EXISTS (
                                SELECT 1
                                FROM information_schema.tables
                                WHERE table_schema = :schema
                                  AND table_name = :table
                            )
                            """
                        ),
                        {"schema": schema, "table": table},
                    ).scalar()
                    if not exists:
                        checks.append(CheckItem(table_name, "fail", "tabela ausente"))
                        continue

                    count = conn.execute(text(f"SELECT COUNT(*) FROM {table_name}")).scalar()
                    status = "ok" if int(count or 0) > 0 else "warn"
                    details = f"{count} registros" if status == "ok" else "tabela existe, mas esta vazia"
                    checks.append(CheckItem(table_name, status, details))
    except Exception as exc:
        checks.append(CheckItem("database", "warn", f"PostGIS indisponivel: {exc}"))
    return checks
