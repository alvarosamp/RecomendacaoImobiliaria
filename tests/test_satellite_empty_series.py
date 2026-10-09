import tempfile
from pathlib import Path
from unittest.mock import patch
import pandas as pd
from recomendacao_imobiliaria import satellite_collector as collector


def test_empty_months_preserve_schema_and_do_not_abort_series():
    with tempfile.TemporaryDirectory() as directory:
        output = str(Path(directory) / "indices.csv")
        def collect(start, end, temporary, *args):
            Path(temporary).write_text("\n")
            return collector.SatelliteCollectResult(711, 0, 0, temporary, ["No usable scenes"])
        with patch.object(collector, "collect_for_grid", side_effect=collect) as mocked:
            result = collector.collect_time_series_for_grid(12, output)
        assert mocked.call_count == 12
        assert result.rows_written == 0
        assert result.h3_cells == 711
        assert result.errors == ["No usable scenes"] * 12
        assert list(pd.read_csv(output).columns) == collector.INDEX_COLUMNS
        assert not list(Path(directory).glob(".indices-*.csv"))


def test_nonempty_month_survives_an_empty_month():
    with tempfile.TemporaryDirectory() as directory:
        output = str(Path(directory) / "indices.csv")
        calls = []
        def collect(start, end, temporary, *args):
            calls.append(start)
            if len(calls) == 1:
                Path(temporary).write_text("\n")
                return collector.SatelliteCollectResult(1, 0, 0, temporary)
            pd.DataFrame([{"h3_id":"test-cell", "date":start, "ndvi":0.2, "ndbi":0.1, "bai":None, "cloud_pct":10}]).to_csv(temporary,index=False)
            return collector.SatelliteCollectResult(1, 1, 1, temporary)
        with patch.object(collector, "collect_for_grid", side_effect=collect):
            result = collector.collect_time_series_for_grid(2, output)
        assert result.rows_written == 1
        assert result.scenes_processed == 1
        assert pd.read_csv(output).iloc[0]["h3_id"] == "test-cell"
