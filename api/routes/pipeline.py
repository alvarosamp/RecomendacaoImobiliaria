from __future__ import annotations

import asyncio
import sys
from typing import Any

from fastapi import APIRouter, BackgroundTasks, HTTPException

router = APIRouter()

Command = str | tuple[str, ...]

_state: dict[str, Any] = {
    "running": False,
    "steps": [],
    "done": False,
    "success": None,
    "mode": None,
}

FULL_STEPS: list[tuple[Command, str]] = [
    ("fetch-boundary", "Buscando limite do municipio"),
    ("build-grid", "Gerando grade H3"),
    ("sync-official-layers", "Consolidando bairros e zoneamento oficiais"),
    ("sync-listings", "Atualizando anúncios e preços de mercado"),
    ("fetch-pois", "Coletando POIs do OpenStreetMap"),
    ("fetch-cnes", "Buscando estabelecimentos de saude (CNES)"),
    ("sync-hydrology", "Atualizando hidrografia e distancia de drenagem"),
    ("sync-official-susceptibility", "Atualizando carta oficial SGB/CPRM"),
    (("collect-land-cover", "--year", "2024"), "Atualizando cobertura do solo MapBiomas"),
    ("build-features", "Calculando features de acessibilidade"),
    ("estimate-population", "Estimando populacao por celula (IBGE)"),
    (("sync-sentinel2", "--months", "12"), "Coletando e importando série temporal Sentinel-2"),
    ("update-index-features", "Processando indices Sentinel-2"),
    ("calculate-risk-signals", "Calculando alertas territoriais"),
    ("score-db", "Calculando e salvando scores"),
    (("calibrate-priorities", "--apply"), "Calibrando faixas de prioridade"),
]

REFRESH_STEPS: list[tuple[Command, str]] = [
    ("sync-official-layers", "Atualizando bairros e zoneamento oficiais"),
    ("sync-listings", "Atualizando anúncios e preços de mercado"),
    ("fetch-pois", "Atualizando POIs do OpenStreetMap"),
    ("fetch-cnes", "Atualizando dados de saude (CNES)"),
    ("sync-hydrology", "Atualizando hidrografia e drenagem"),
    ("sync-official-susceptibility", "Atualizando carta oficial SGB/CPRM"),
    (("collect-land-cover", "--year", "2024"), "Atualizando uso do solo MapBiomas"),
    ("build-features", "Recalculando features de acessibilidade"),
    ("estimate-population", "Atualizando estimativa populacional (IBGE)"),
    (("sync-sentinel2", "--months", "3"), "Atualizando série temporal Sentinel-2"),
    ("update-index-features", "Recalculando indices Sentinel-2"),
    ("calculate-risk-signals", "Atualizando alertas territoriais"),
    ("score-db", "Atualizando scores das celulas"),
    (("calibrate-priorities", "--apply"), "Recalibrando faixas de prioridade"),
]


async def _run_steps(steps: list[tuple[Command, str]]) -> None:
    _state["running"] = True
    _state["steps"] = []
    _state["done"] = False
    _state["success"] = None

    for cmd, label in steps:
        args = [cmd] if isinstance(cmd, str) else list(cmd)
        step: dict[str, Any] = {
            "cmd": " ".join(args),
            "label": label,
            "status": "running",
            "output": "",
        }
        _state["steps"].append(step)

        proc = await asyncio.create_subprocess_exec(
            sys.executable,
            "-m",
            "recomendacao_imobiliaria.cli",
            *args,
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
    """Pipeline completo: usar na primeira execucao ou para reset total."""
    if _state["running"]:
        raise HTTPException(409, "Pipeline ja em execucao")
    _state["mode"] = "full"
    background_tasks.add_task(_run_steps, FULL_STEPS)
    return {"status": "accepted", "mode": "full", "total_steps": len(FULL_STEPS)}


@router.post("/pipeline/refresh", status_code=202)
async def refresh_pipeline(background_tasks: BackgroundTasks):
    """Atualizacao rapida: atualiza POIs, features e scores sem refazer o grid."""
    if _state["running"]:
        raise HTTPException(409, "Pipeline ja em execucao")
    _state["mode"] = "refresh"
    background_tasks.add_task(_run_steps, REFRESH_STEPS)
    return {"status": "accepted", "mode": "refresh", "total_steps": len(REFRESH_STEPS)}


@router.post("/pipeline/reset", status_code=200)
async def reset_pipeline_state():
    """Reseta o estado do pipeline."""
    if _state["running"]:
        raise HTTPException(409, "Pipeline em execucao; aguarde terminar")
    _state.update({"running": False, "steps": [], "done": False, "success": None, "mode": None})
    return {"status": "reset"}


@router.get("/pipeline/status")
def get_pipeline_status():
    return _state
