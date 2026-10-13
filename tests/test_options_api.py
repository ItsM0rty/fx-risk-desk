import json
import math

import pytest
from fastapi.testclient import TestClient

from riskdesk.api import app
from riskdesk.options import DOMESTIC_RATE, FOREIGN_RATE, price_scenario
from riskdesk.run import write_run


def test_option_parity_zero_vol_and_greeks():
    spot, strike, days, notional = 1.1, 1.09, 90, 100_000
    call = price_scenario(spot, strike, days, .09, notional, "call")
    put = price_scenario(spot, strike, days, .09, notional, "put")
    expiry = days / 365
    parity = spot * math.exp(-FOREIGN_RATE * expiry) - strike * math.exp(-DOMESTIC_RATE * expiry)
    assert call["premium_per_eur"] - put["premium_per_eur"] == pytest.approx(parity)
    assert call["premium_usd"] == pytest.approx(call["premium_per_eur"] * notional)
    assert next(s for s in put["shocks"] if s["shock_pct"] == 0)["pnl_usd"] == 0
    assert price_scenario(spot, strike, days, 0, notional, "put")["greeks"] is None
    bump = 1e-5
    up = price_scenario(spot + bump, strike, days, .09, notional, "put")["premium_per_eur"]
    down = price_scenario(spot - bump, strike, days, .09, notional, "put")["premium_per_eur"]
    assert put["greeks"]["delta"] == pytest.approx((up - down) / (2 * bump), abs=1e-6)


def test_api_validates_query_and_reports_missing_run(monkeypatch, tmp_path):
    monkeypatch.setenv("FX_RISK_RUN", str(tmp_path / "absent.json"))
    with TestClient(app) as client:
        assert client.get("/api/v1/runs/latest").status_code == 503
        assert client.get("/api/v1/runs/latest/risk?hedge_pct=33").status_code == 422
        assert client.get("/api/v1/runs/latest/forecast?limit=0").status_code == 422
        assert client.get("/api/v1/options/scenario?volatility=nan").status_code == 422
        assert client.get("/openapi.json").json()["openapi"] == "3.1.0"


def test_api_option_price_and_risk_limit(monkeypatch, tmp_path):
    path = tmp_path / "test.json"
    row = {"date": "2025-12-31", "pnl": -100, "unhedged_pnl": -250,
           "var": 200, "es": 230, "breach": False}
    write_run(path, {"summary": {"spot": 1.10, "run_id": "fixture"},
                     "risk_series": {"75": [{**row, "date": "2025-12-30"}, row]}})
    monkeypatch.setenv("FX_RISK_RUN", str(path))
    with TestClient(app) as client:
        price = client.get("/api/v1/options/scenario?volatility=0").json()
        assert price["spot"] == 1.10
        assert price["greeks"] is None
        risk = client.get("/api/v1/runs/latest/risk?limit=1").json()
        assert risk == {"run_id": "fixture", "hedge_pct": 75, "points": [row]}


def test_snapshot_rejects_nonfinite_without_destroying_previous_run(tmp_path):
    path = tmp_path / "run.json"
    write_run(path, {"value": 42})
    with pytest.raises(ValueError):
        write_run(path, {"value": float("nan")})
    assert json.loads(path.read_text()) == {"value": 42}
    assert list(tmp_path.iterdir()) == [path]
