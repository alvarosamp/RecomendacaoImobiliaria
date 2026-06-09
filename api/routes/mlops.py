from __future__ import annotations

import datetime
import os

from fastapi import APIRouter

router = APIRouter()

TRACKING_URI = os.getenv("MLFLOW_TRACKING_URI", "http://localhost:5000")


@router.get("/mlops/runs")
def get_runs():
    try:
        import mlflow

        mlflow.set_tracking_uri(TRACKING_URI)
        client = mlflow.tracking.MlflowClient()
        experiments = client.search_experiments()
        if not experiments:
            return []

        all_runs = []
        for exp in experiments:
            runs = client.search_runs(
                experiment_ids=[exp.experiment_id],
                order_by=["start_time DESC"],
                max_results=5,
            )
            for run in runs:
                ts = run.info.start_time
                start = (
                    datetime.datetime.fromtimestamp(ts / 1000).strftime("%Y-%m-%d %H:%M")
                    if ts
                    else None
                )
                all_runs.append(
                    {
                        "run_id": run.info.run_id,
                        "experiment": exp.name,
                        "start_time": start,
                        "status": run.info.status,
                        "metrics": dict(run.data.metrics),
                        "params": dict(run.data.params),
                    }
                )

        all_runs.sort(key=lambda r: r["start_time"] or "", reverse=True)
        return all_runs[:10]

    except Exception as exc:
        return {"error": str(exc), "runs": []}
