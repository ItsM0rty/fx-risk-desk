import pytest

from riskdesk.export_demo import FORECAST_POINTS, RISK_POINTS, export_demo
from riskdesk.options import price_scenario


def test_export_keeps_bounded_results_and_uses_exact_python_pricer():
    risk = {
        "date": "2025-12-31", "pnl": -123.456, "unhedged_pnl": -987.654,
        "var": 98.765, "es": 150.2, "breach": True,
    }
    forecast = {
        "date": "2025-12-31", "actual": .001, "low": -.01, "median": 0, "high": .01,
    }
    summary = {
        "run_id": "demo", "as_of": risk["date"], "spot": 1.175, "risk_window": 250,
        "hedge_fee_bps": .15, "policies": [], "positions": [], "forecast": {},
        "nrb_payout": {"date": risk["date"], "npr_amount": 10000000, "usd_at_buy": 69750, "usd_at_mid": 69604, "buy_npr_per_usd": 143.37},
        "sources": {"ecb": {"observations": 4097}, "nrb": {"observations": 1461}},
    }
    demo = export_demo({
        "summary": summary, "risk_series": {"50": [risk] * (RISK_POINTS + 3)},
        "forecast_series": [forecast] * (FORECAST_POINTS + 3),
        "raw_rows": ["not part of the published schema"],
    })
    assert len(demo["risk_series"]["50"]) == RISK_POINTS
    assert demo["risk_series"]["50"][0] == [risk["date"], -123.46, -987.65, -98.77, True]
    assert len(demo["forecast_series"]) == FORECAST_POINTS
    assert "raw_rows" not in demo and "sources" not in demo
    assert "buy_npr_per_usd" not in demo["nrb_payout"]
    assert len(demo["option_presets"]) == 72
    scenario = demo["option_presets"]["put:90:15:100"]
    direct = price_scenario(1.175, 1.175, 90, .15, 1_000_000, "put")
    assert scenario["premium_usd"] == pytest.approx(direct["premium_usd"])
    assert scenario["shocks"] == direct["shocks"]
