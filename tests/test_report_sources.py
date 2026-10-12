import pandas as pd
import pytest

from recomendacao_imobiliaria import reports


@pytest.mark.parametrize("source", ["auto", "postgis"])
def test_database_failure_cannot_produce_demo(source, tmp_path, monkeypatch):
    def fail():
        raise ConnectionError("database unavailable")
    monkeypatch.setattr(reports, "load_score_table", fail)
    monkeypatch.setattr(reports, "sample_areas", lambda: pytest.fail("demo was used"))
    with pytest.raises(reports.ReportDataUnavailable):
        reports.export_report(str(tmp_path), source=source)
    assert list(tmp_path.iterdir()) == []


def test_empty_database_is_not_a_demo(monkeypatch):
    monkeypatch.setattr(reports, "load_score_table", lambda: pd.DataFrame())
    with pytest.raises(reports.ReportDataUnavailable, match="Sem scores"):
        reports._load_report_frame("auto")


def test_explicit_demo_is_identified_in_markdown_and_csv(tmp_path):
    result = reports.export_report(str(tmp_path), source="demo")
    assert result.source == "demo" and result.rows > 0
    assert "DADOS SINTETICOS" in (tmp_path / "opportunity_report.md").read_text(encoding="utf-8")
    frame = pd.read_csv(result.csv_path)
    assert set(frame.data_source) == {"demo"}


def test_invalid_source_does_not_select_demo():
    with pytest.raises(ValueError):
        reports._load_report_frame("typo")
