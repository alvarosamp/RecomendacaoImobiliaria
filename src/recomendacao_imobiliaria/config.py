from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv


@dataclass(frozen=True)
class Settings:
    pg_host: str = "localhost"
    pg_port: int = 5432
    pg_db: str = "ImobiliariaDB"
    pg_user: str = "admin"
    pg_pass: str = "admin123"
    city_name: str = "Pouso Alegre, Minas Gerais, Brazil"
    city_lat: float = -22.230278
    city_lon: float = -45.948889
    h3_res: int = 8
    app_env: str = "development"
    jwt_secret: str = "development-only-change-me"
    cors_origins: tuple[str, ...] = ("http://localhost:5173", "http://localhost:3000")

    @property
    def database_url(self) -> str:
        return (
            f"postgresql+psycopg2://{self.pg_user}:{self.pg_pass}"
            f"@{self.pg_host}:{self.pg_port}/{self.pg_db}"
        )


def load_settings(env_file: str | None = None) -> Settings:
    if env_file:
        load_dotenv(env_file)
    else:
        load_dotenv()

    cors_origins = tuple(
        origin.strip()
        for origin in os.getenv("CORS_ORIGINS", "http://localhost:5173,http://localhost:3000").split(",")
        if origin.strip()
    )

    return Settings(
        pg_host=os.getenv("PG_HOST", Settings.pg_host),
        pg_port=int(os.getenv("PG_PORT", Settings.pg_port)),
        pg_db=os.getenv("PG_DB", Settings.pg_db),
        pg_user=os.getenv("PG_USER", Settings.pg_user),
        pg_pass=os.getenv("PG_PASS", Settings.pg_pass),
        city_name=os.getenv("CITY_NAME", Settings.city_name),
        city_lat=float(os.getenv("CITY_LAT", Settings.city_lat)),
        city_lon=float(os.getenv("CITY_LON", Settings.city_lon)),
        h3_res=int(os.getenv("H3_RES", Settings.h3_res)),
        app_env=os.getenv("APP_ENV", Settings.app_env).lower(),
        jwt_secret=os.getenv("JWT_SECRET", Settings.jwt_secret),
        cors_origins=cors_origins,
    )
