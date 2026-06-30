from __future__ import annotations

import dataclasses
from pathlib import Path

import pandas as pd

from .decision import enrich_opportunities
from .demo_data import sample_areas
from .reporting import explain_to_text, load_score_table
from .scoring import score_area


@dataclasses.dataclass(frozen=True)
class ReportResult:
    markdown_path: str
    csv_path: str
    rows: int
    source: str


def export_report(
    output_dir: str = "reports",
    source: str = "auto",
    top_n: int = 10,
) -> ReportResult:
    frame, resolved_source = _load_report_frame(source)
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    csv_path = output_path / "opportunity_report.csv"
    md_path = output_path / "opportunity_report.md"
    frame.to_csv(csv_path, index=False)
    md_path.write_text(_render_markdown(frame, resolved_source, top_n=top_n), encoding="utf-8")
    return ReportResult(
        markdown_path=str(md_path),
        csv_path=str(csv_path),
        rows=len(frame),
        source=resolved_source,
    )


def _load_report_frame(source: str) -> tuple[pd.DataFrame, str]:
    if source in {"auto", "postgis"}:
        try:
            table = load_score_table()
            table["explicacao"] = table["explain_json"].apply(explain_to_text)
            table["best_score"] = table[["score_residencial", "score_comercial"]].max(axis=1)
            return table, "postgis"
        except Exception:
            if source == "postgis":
                raise

    rows = []
    for area in sample_areas():
        result = score_area(area)
        rows.append(
            {
                "h3_id": result.h3_id,
                "score_residencial": result.score_residencial,
                "score_comercial": result.score_comercial,
                "best_score": max(result.score_residencial, result.score_comercial),
                "zona": result.explain["zoning"].get("zona"),
                "explain_json": result.explain,
                "explicacao": explain_to_text(result.explain),
            }
        )
    return enrich_opportunities(pd.DataFrame(rows)), "demo"


def _render_markdown(frame: pd.DataFrame, source: str, top_n: int) -> str:
    lines = [
        "# Relatorio de Oportunidades",
        "",
        f"Fonte: `{source}`",
        f"Areas avaliadas: **{len(frame)}**",
        "",
        "## Resumo executivo",
        "",
        f"- Maior score residencial: **{_max_value(frame, 'score_residencial'):.2f}**",
        f"- Maior score comercial: **{_max_value(frame, 'score_comercial'):.2f}**",
        f"- Areas com prioridade alta: **{_count_value(frame, 'priority', 'alta')}**",
        f"- Areas com risco alto: **{_count_value(frame, 'risk_level', 'alto')}**",
        "",
        "## Top oportunidades",
        "",
    ]

    columns = [
        "h3_id",
        "priority",
        "primary_use",
        "risk_level",
        "best_score",
        "score_residencial",
        "score_comercial",
        "summary",
    ]
    available = [column for column in columns if column in frame.columns]
    top = frame.sort_values("best_score", ascending=False).head(top_n)
    lines.append(_markdown_table(top[available]))
    lines.extend(["", "## Observacoes", ""])
    lines.append(
        "Este relatorio e um apoio analitico. Recomendacoes reais dependem de zoneamento oficial, "
        "Plano Diretor atualizado e validacao tecnica."
    )
    return "\n".join(lines)


def _max_value(frame: pd.DataFrame, column: str) -> float:
    if frame.empty or column not in frame.columns:
        return 0.0
    return float(pd.to_numeric(frame[column], errors="coerce").fillna(0).max())


def _count_value(frame: pd.DataFrame, column: str, value: str) -> int:
    if column not in frame.columns:
        return 0
    return int((frame[column] == value).sum())


def _markdown_table(frame: pd.DataFrame) -> str:
    if frame.empty:
        return "_Sem registros._"

    headers = list(frame.columns)
    rows = []
    rows.append("| " + " | ".join(headers) + " |")
    rows.append("| " + " | ".join("---" for _ in headers) + " |")
    for record in frame.to_dict(orient="records"):
        values = [str(record.get(header, "")).replace("\n", " ") for header in headers]
        rows.append("| " + " | ".join(values) + " |")
    return "\n".join(rows)
