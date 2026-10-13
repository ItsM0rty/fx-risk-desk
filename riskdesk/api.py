import json
import os
from functools import lru_cache
from pathlib import Path
from typing import Annotated, Literal

from fastapi import FastAPI, HTTPException, Query
from fastapi.staticfiles import StaticFiles

from .options import price_scenario
from .schema import (
    ForecastSeries, OptionKind, OptionScenario, RiskSeries, RunSummary, UnavailableRun,
)

app = FastAPI(title="FX Risk Desk", version="0.1.0", description="Public-data FX research desk.")
PREFIX = "/api/v1"
NO_RUN = {503: {"model": UnavailableRun, "description": "The local risk snapshot is unavailable."}}
RUN_FILE = Path(__file__).resolve().parents[1] / "data" / "runs" / "latest.json"
HedgeQuery = Literal["0", "25", "50", "75", "100"]
PointLimit = Annotated[int, Query(ge=1, le=5000)]


@lru_cache(maxsize=1)
def _read_snapshot(path: Path, modified_ns: int, size: int) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def current_run() -> dict:
    path = Path(os.environ.get("FX_RISK_RUN", RUN_FILE)).resolve()
    try:
        state = path.stat()
        return _read_snapshot(path, state.st_mtime_ns, state.st_size)
    except (OSError, ValueError) as error:
        raise HTTPException(503, "Generate a local snapshot with python -m riskdesk.run.") from error


@app.get(f"{PREFIX}/runs/latest", response_model=RunSummary, responses=NO_RUN, operation_id="getRun")
def get_run() -> dict:
    return current_run()["summary"]


@app.get(f"{PREFIX}/runs/latest/risk", response_model=RiskSeries, responses=NO_RUN, operation_id="getRisk")
def get_risk(hedge_pct: HedgeQuery = "75", limit: PointLimit = 252) -> dict:
    snapshot = current_run()
    return {
        "run_id": snapshot["summary"]["run_id"],
        "hedge_pct": int(hedge_pct),
        "points": snapshot["risk_series"][hedge_pct][-limit:],
    }


@app.get(f"{PREFIX}/runs/latest/forecast", response_model=ForecastSeries, responses=NO_RUN,
         operation_id="getForecast")
def get_forecast(limit: PointLimit = 120) -> dict:
    snapshot = current_run()
    return {"run_id": snapshot["summary"]["run_id"], "points": snapshot["forecast_series"][-limit:]}


@app.get(f"{PREFIX}/options/scenario", response_model=OptionScenario, responses=NO_RUN,
         operation_id="getOptionScenario")
def get_option_scenario(
    strike: Annotated[float | None, Query(gt=0, le=10)] = None,
    maturity_days: Annotated[int, Query(ge=1, le=730)] = 90,
    volatility: Annotated[float, Query(ge=0, le=2)] = 0.09,
    notional: Annotated[int, Query(ge=1, le=100_000_000)] = 1_000_000,
    option_type: OptionKind = "put",
) -> dict:
    spot = current_run()["summary"]["spot"]
    return price_scenario(spot, spot if strike is None else strike, maturity_days,
                          volatility, notional, option_type)

DASHBOARD = Path(__file__).resolve().parents[1] / "apps" / "dashboard" / "dist"
if (DASHBOARD / "index.html").is_file():
    app.mount("/", StaticFiles(directory=DASHBOARD, html=True), name="dashboard")
