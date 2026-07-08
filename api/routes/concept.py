from __future__ import annotations

import base64
import hashlib
import io
import json
import os
import textwrap
from datetime import date
from pathlib import Path
from typing import Any

import requests
from fastapi import APIRouter, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel, Field

router = APIRouter()

ROOT = Path(__file__).resolve().parents[2]
CACHE_DIR = ROOT / "cache" / "concept_images"
USAGE_FILE = CACHE_DIR / "usage.json"
DAILY_LIMIT = int(os.getenv("HF_DAILY_IMAGE_LIMIT", "8"))
HF_MODEL = os.getenv("HF_IMAGE_MODEL", "stabilityai/stable-diffusion-xl-base-1.0")

FINISH_COST = {
    "economico": 2300,
    "medio": 3200,
    "alto": 4700,
}

SCENARIOS = {
    "casa": {"area_factor": 0.55, "floors": 1, "rent_factor": 0.0048, "sale_factor": 1.18},
    "predio_pequeno": {"area_factor": 1.65, "floors": 4, "rent_factor": 0.0062, "sale_factor": 1.34},
    "uso_misto": {"area_factor": 1.2, "floors": 3, "rent_factor": 0.0072, "sale_factor": 1.42},
}


class ConceptInput(BaseModel):
    lotArea: float = Field(300, ge=40)
    frontage: float = Field(10, ge=3)
    buildArea: float = Field(165, ge=20)
    floors: int = Field(2, ge=1, le=30)
    typology: str = "casa"
    finish: str = "medio"
    style: str = "contemporaneo"
    zone: str | None = None
    residentialScore: float | None = None
    commercialScore: float | None = None
    riskLevel: str | None = None
    growthSignal: float | None = None
    exteriorImage: str | None = None
    interiorImage: str | None = None


class ImageRequest(ConceptInput):
    view: str = Field("exterior", pattern="^(exterior|interior)$")
    variation: bool = False


def _money(value: float) -> str:
    return f"R$ {value:,.0f}".replace(",", ".")


def _build_prompt(data: ConceptInput, view: str = "exterior", variation: bool = False) -> str:
    base = [
        f"conceito arquitetonico para {data.typology}",
        f"lote urbano de {data.lotArea:.0f} m2 com frente de {data.frontage:.0f} m",
        f"{data.buildArea:.0f} m2 construidos em {data.floors} pavimento(s)",
        f"padrao {data.finish}, estilo {data.style}",
        "arquitetura brasileira realista, materiais viaveis, proporcoes construtivas coerentes",
    ]
    if data.zone:
        base.append(f"zoneamento {data.zone}")
    if view == "interior":
        base.extend([
            "visualizacao interna, sala integrada, cozinha, circulacao clara",
            "luz natural, escala humana, moveis simples, render arquitetonico",
        ])
    else:
        base.extend([
            "fachada e volumetria externa, implantacao no terreno, jardim frontal",
            "render arquitetonico profissional, rua urbana brasileira",
        ])
    if variation:
        base.append("segunda alternativa visual, composicao diferente da anterior")
    return ", ".join(base)


def _plan(data: ConceptInput) -> dict[str, Any]:
    lot_area = max(float(data.lotArea or 1), 1)
    build_area = max(float(data.buildArea or 1), 1)
    cost_m2 = FINISH_COST.get(data.finish, FINISH_COST["medio"])
    construction = build_area * cost_m2
    soft = construction * 0.14
    contingency = construction * 0.1
    total = construction + soft + contingency
    months = max(6, round(build_area / 28) + int(data.floors or 1))
    occupancy = min(85, (build_area / lot_area) * 100)
    potential = ((data.residentialScore or 55) * 0.55) + ((data.commercialScore or 45) * 0.35)
    if data.riskLevel == "alto":
        potential *= 0.82
    viability = max(0, min(100, (potential * 0.72) + ((100 - min(100, occupancy)) * 0.18) + 10))
    sale_value = total * (1 + (potential / 100) * 0.42)
    monthly_rent = sale_value * (0.0045 + (data.commercialScore or 0) / 100 * 0.002)

    return {
        "costPerM2": cost_m2,
        "constructionCost": round(construction),
        "softCosts": round(soft),
        "contingency": round(contingency),
        "total": round(total),
        "months": months,
        "occupancy": round(occupancy, 1),
        "viabilityScore": round(viability, 1),
        "saleValue": round(sale_value),
        "monthlyRent": round(monthly_rent),
        "paybackYears": round(total / max(monthly_rent * 12, 1), 1),
        "schedule": [
            {"label": "Estudo e anteprojeto", "weeks": "2-4 semanas"},
            {"label": "Projetos e aprovacoes", "weeks": "6-10 semanas"},
            {"label": "Fundacao e estrutura", "weeks": f"{max(6, round(months * 1.1))} semanas"},
            {"label": "Instalacoes e fechamento", "weeks": f"{max(8, round(months * 1.4))} semanas"},
            {"label": "Acabamento e entrega", "weeks": f"{max(6, round(months * 1.1))} semanas"},
        ],
        "promptExterior": _build_prompt(data, "exterior"),
        "promptInterior": _build_prompt(data, "interior"),
    }


def _scenario(data: ConceptInput, key: str, cfg: dict[str, float]) -> dict[str, Any]:
    build_area = max(45, data.lotArea * cfg["area_factor"])
    raw = data.dict()
    raw.update({
        "typology": key.replace("_", " "),
        "buildArea": build_area,
        "floors": int(cfg["floors"]),
    })
    local = ConceptInput(**raw)
    plan = _plan(local)
    total = plan["total"]
    sale = total * cfg["sale_factor"]
    rent = sale * cfg["rent_factor"]
    return {
        "id": key,
        "label": {"casa": "Casa", "predio_pequeno": "Predio pequeno", "uso_misto": "Uso misto"}[key],
        "buildArea": round(build_area),
        "floors": int(cfg["floors"]),
        "cost": plan["total"],
        "months": plan["months"],
        "estimatedSale": round(sale),
        "estimatedRent": round(rent),
        "roiYear": round((rent * 12) / max(total, 1) * 100, 1),
        "viabilityScore": plan["viabilityScore"],
    }


def _usage() -> dict[str, int]:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    if not USAGE_FILE.exists():
        return {}
    try:
        return json.loads(USAGE_FILE.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _save_usage(usage: dict[str, int]) -> None:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    USAGE_FILE.write_text(json.dumps(usage, indent=2), encoding="utf-8")


def _cache_key(prompt: str, view: str) -> str:
    return hashlib.sha256(f"{HF_MODEL}|{view}|{prompt}".encode("utf-8")).hexdigest()


def _image_to_data_url(path: Path) -> str:
    return "data:image/png;base64," + base64.b64encode(path.read_bytes()).decode("ascii")


@router.post("/concept/analyze")
def analyze_concept(payload: ConceptInput):
    plan = _plan(payload)
    scenarios = [_scenario(payload, key, cfg) for key, cfg in SCENARIOS.items()]
    return {"plan": plan, "scenarios": scenarios}


@router.post("/concept/generate-image")
def generate_image(payload: ImageRequest):
    prompt = _build_prompt(payload, payload.view, payload.variation)
    key = _cache_key(prompt, payload.view)
    path = CACHE_DIR / f"{key}.png"
    if path.exists() and not payload.variation:
        return {
            "status": "cached",
            "model": HF_MODEL,
            "view": payload.view,
            "prompt": prompt,
            "image": _image_to_data_url(path),
            "remainingToday": max(0, DAILY_LIMIT - _usage().get(date.today().isoformat(), 0)),
        }

    usage = _usage()
    today = date.today().isoformat()
    used = usage.get(today, 0)
    if used >= DAILY_LIMIT:
        return {
            "status": "limited",
            "model": HF_MODEL,
            "view": payload.view,
            "prompt": prompt,
            "image": None,
            "remainingToday": 0,
            "message": "Limite diario de imagens atingido. Use o prompt ou tente novamente amanha.",
        }

    token = os.getenv("HF_TOKEN")
    if not token:
        return {
            "status": "missing_token",
            "model": HF_MODEL,
            "view": payload.view,
            "prompt": prompt,
            "image": None,
            "remainingToday": max(0, DAILY_LIMIT - used),
            "message": "Defina HF_TOKEN no ambiente para ativar a geracao pelo Hugging Face.",
        }

    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    url = f"https://api-inference.huggingface.co/models/{HF_MODEL}"
    response = requests.post(
        url,
        headers={"Authorization": f"Bearer {token}", "Accept": "image/png"},
        json={
            "inputs": prompt,
            "parameters": {
                "negative_prompt": "texto ilegivel, baixa resolucao, deformado, perspectiva impossivel, pessoas distorcidas",
                "num_inference_steps": 24,
                "guidance_scale": 7,
                "width": 1024,
                "height": 768,
            },
        },
        timeout=120,
    )
    if not response.ok:
        raise HTTPException(status_code=502, detail=response.text[:500])
    path.write_bytes(response.content)
    usage[today] = used + 1
    _save_usage(usage)
    return {
        "status": "generated",
        "model": HF_MODEL,
        "view": payload.view,
        "prompt": prompt,
        "image": _image_to_data_url(path),
        "remainingToday": max(0, DAILY_LIMIT - usage[today]),
    }


def _pdf_escape(text: str) -> str:
    return text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def _decode_data_image(data_url: str | None) -> tuple[bytes, int, int] | None:
    if not data_url:
        return None
    try:
        from PIL import Image

        raw = data_url.split(",", 1)[1] if "," in data_url else data_url
        image = Image.open(io.BytesIO(base64.b64decode(raw))).convert("RGB")
        image.thumbnail((230, 170))
        out = io.BytesIO()
        image.save(out, format="JPEG", quality=82)
        return out.getvalue(), image.width, image.height
    except Exception:
        return None


def _simple_pdf(lines: list[str], image: tuple[bytes, int, int] | None = None) -> bytes:
    stream_lines = ["BT", "/F1 12 Tf", "50 790 Td", "16 TL"]
    for line in lines:
        for part in textwrap.wrap(str(line), 86) or [""]:
            stream_lines.append(f"({_pdf_escape(part)}) Tj")
            stream_lines.append("T*")
    stream_lines.append("ET")
    if image:
        stream_lines.append(f"q {image[1]} 0 0 {image[2]} 315 610 cm /Im1 Do Q")
    content = "\n".join(stream_lines).encode("latin-1", errors="replace")
    resources = b"<< /Font << /F1 4 0 R >> >>"
    objects = []
    if image:
        resources = b"<< /Font << /F1 4 0 R >> /XObject << /Im1 6 0 R >> >>"
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] /Resources " + resources + b" /Contents 5 0 R >>",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
        b"<< /Length " + str(len(content)).encode() + b" >>\nstream\n" + content + b"\nendstream",
    ]
    if image:
        jpg, width, height = image
        objects.append(
            b"<< /Type /XObject /Subtype /Image /Width " + str(width).encode()
            + b" /Height " + str(height).encode()
            + b" /ColorSpace /DeviceRGB /BitsPerComponent 8 /Filter /DCTDecode /Length "
            + str(len(jpg)).encode() + b" >>\nstream\n" + jpg + b"\nendstream"
        )
    out = io.BytesIO()
    out.write(b"%PDF-1.4\n")
    offsets = []
    for idx, obj in enumerate(objects, start=1):
        offsets.append(out.tell())
        out.write(f"{idx} 0 obj\n".encode())
        out.write(obj)
        out.write(b"\nendobj\n")
    xref = out.tell()
    out.write(f"xref\n0 {len(objects) + 1}\n0000000000 65535 f \n".encode())
    for offset in offsets:
        out.write(f"{offset:010d} 00000 n \n".encode())
    out.write(f"trailer << /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF".encode())
    return out.getvalue()


@router.post("/concept/report")
def concept_report(payload: ConceptInput):
    plan = _plan(payload)
    scenarios = [_scenario(payload, key, cfg) for key, cfg in SCENARIOS.items()]
    lines = [
        "Relatorio de oportunidade imobiliaria",
        "",
        f"Tipologia base: {payload.typology}",
        f"Terreno: {payload.lotArea:.0f} m2 | Frente: {payload.frontage:.0f} m | Zona: {payload.zone or '-'}",
        f"Area construida: {payload.buildArea:.0f} m2 | Pavimentos: {payload.floors}",
        f"Score de viabilidade construtiva: {plan['viabilityScore']}/100",
        f"Custo total estimado: {_money(plan['total'])}",
        f"Prazo estimado: {plan['months']} meses",
        f"Valor potencial de venda: {_money(plan['saleValue'])}",
        f"Aluguel potencial mensal: {_money(plan['monthlyRent'])}",
        f"Payback estimado: {plan['paybackYears']} anos",
        "",
        "Comparador de cenarios:",
    ]
    for item in scenarios:
        lines.append(
            f"- {item['label']}: custo {_money(item['cost'])}, prazo {item['months']} meses, "
            f"ROI anual {item['roiYear']}%, score {item['viabilityScore']}/100"
        )
    lines.extend([
        "",
        "Justificativa tecnica:",
        f"Score residencial: {payload.residentialScore if payload.residentialScore is not None else '-'}",
        f"Score comercial: {payload.commercialScore if payload.commercialScore is not None else '-'}",
        f"Risco: {payload.riskLevel or '-'}",
        f"Crescimento urbano: {payload.growthSignal if payload.growthSignal is not None else '-'}",
        "",
        "Prompt exterior:",
        plan["promptExterior"],
        "",
        "Prompt interior:",
        plan["promptInterior"],
    ])
    return Response(
        content=_simple_pdf(lines, _decode_data_image(payload.exteriorImage or payload.interiorImage)),
        media_type="application/pdf",
        headers={"Content-Disposition": "attachment; filename=relatorio-oportunidade.pdf"},
    )
