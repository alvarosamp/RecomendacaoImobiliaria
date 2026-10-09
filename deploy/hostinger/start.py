"""Seed public reference files into persistent storage, then start the API."""
import os
import shutil
from pathlib import Path
from recomendacao_imobiliaria.data_registry import ensure_data_schema

source = Path('/app/reference-data/official')
target = Path('/app/storage/official')
if Path('/app/storage').exists():
    shutil.copytree(source, target, dirs_exist_ok=True)
    if not Path('/app/data').is_symlink():
        Path('/app/data').rmdir()
        os.symlink('/app/storage', '/app/data')
ensure_data_schema()
os.execvp('uvicorn', ['uvicorn', 'api.main:app', '--host', '0.0.0.0', '--port', '8000', '--proxy-headers', '--forwarded-allow-ips', '*'])
