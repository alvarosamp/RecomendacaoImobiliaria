from __future__ import annotations

import asyncio
import sys
from typing import Any

from fastapi import APIRouter, BackgroundTasks, HTTPException

router = APIRouter()

_state: dict[str, Any] = {
    "running": False,
    "steps": [],
    "done": False,
    "success": None,
}

STEPS = [
    ("fetch-boundary",        "Buscando limite do município"),
    ("build-grid",            "Gerando grade H3"),
    ("fetch-pois",            "Coletando POIs do OpenStreetMap"),
    ("build-features",        "Calculando features de acessibilidade"),
    ("update-index-features", "Processando índices Sentinel-2"),
    ("score-db",              "Calculando e salvando scores"),
]


async def _execute_pipeline() -> None:
    _state["running"] = True
    _state["steps"] = []
    _state["done"] = False
    _state["success"] = None

    for cmd, label in STEPS:
        step: dict[str, Any] = {
            "cmd": cmd,
            "label": label,
            "status": "running",
            "output": "",
        }
        _state["steps"].append(step)

        proc = await asyncio.create_subprocess_exec(
            sys.executable, "-m", "recomendacao_imobiliaria.cli", cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await proc.communicate()
        output = ((stdout or b"") + (stderr or b"")).decode("utf-8", errors="replace")
        step["status"] = "done" if proc.returncode == 0 else "error"
        step["output"] = output[-500:]

        if proc.returncode != 0:
            _state["running"] = False
            _state["done"] = True
            _state["success"] = False
            return

    _state["running"] = False
    _state["done"] = True
    _state["success"] = True


@router.post("/pipeline/run", status_code=202)
async def run_pipeline(background_tasks: BackgroundTasks):
    if _state["running"]:
        raise HTTPException(409, "Pipeline já em execução")
    background_tasks.add_task(_execute_pipeline)
    return {"status": "accepted"}


@router.get("/pipeline/status")
def get_pipeline_status():
    return _state
