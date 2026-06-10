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
    "mode": None,
}

# Pipeline completo: primeira vez ou reset total
FULL_STEPS = [
    ("fetch-boundary",        "Buscando limite do município"),
    ("build-grid",            "Gerando grade H3"),
    ("fetch-pois",            "Coletando POIs do OpenStreetMap"),
    ("fetch-cnes",            "Buscando estabelecimentos de saúde (CNES)"),
    ("build-features",        "Calculando features de acessibilidade"),
    ("estimate-population",   "Estimando população por célula (IBGE)"),
    ("update-index-features", "Processando índices Sentinel-2"),
    ("score-db",              "Calculando e salvando scores"),
]

# Atualização rápida: não refaz o grid, só atualiza POIs e scores
REFRESH_STEPS = [
    ("fetch-pois",            "Atualizando POIs do OpenStreetMap"),
    ("fetch-cnes",            "Atualizando dados de saúde (CNES)"),
    ("build-features",        "Recalculando features de acessibilidade"),
    ("estimate-population",   "Atualizando estimativa populacional (IBGE)"),
    ("score-db",              "Atualizando scores das células"),
]


async def _run_steps(steps: list[tuple[str, str]]) -> None:
    _state["running"] = True
    _state["steps"] = []
    _state["done"] = False
    _state["success"] = None

    for cmd, label in steps:
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
    """Pipeline completo — usar na primeira execução ou para reset total."""
    if _state["running"]:
        raise HTTPException(409, "Pipeline já em execução")
    _state["mode"] = "full"
    background_tasks.add_task(_run_steps, FULL_STEPS)
    return {"status": "accepted", "mode": "full", "total_steps": len(FULL_STEPS)}


@router.post("/pipeline/refresh", status_code=202)
async def refresh_pipeline(background_tasks: BackgroundTasks):
    """Atualização rápida — atualiza POIs, features e scores sem refazer o grid."""
    if _state["running"]:
        raise HTTPException(409, "Pipeline já em execução")
    _state["mode"] = "refresh"
    background_tasks.add_task(_run_steps, REFRESH_STEPS)
    return {"status": "accepted", "mode": "refresh", "total_steps": len(REFRESH_STEPS)}


@router.post("/pipeline/reset", status_code=200)
async def reset_pipeline_state():
    """Reseta o estado do pipeline (útil se travou)."""
    if _state["running"]:
        raise HTTPException(409, "Pipeline em execução — aguarde terminar")
    _state.update({"running": False, "steps": [], "done": False, "success": None, "mode": None})
    return {"status": "reset"}


@router.get("/pipeline/status")
def get_pipeline_status():
    return _state
