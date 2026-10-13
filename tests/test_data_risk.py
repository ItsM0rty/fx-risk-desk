import json
from zipfile import ZipFile

import numpy as np
import pandas as pd
import pytest

from riskdesk.data import NRB_URL, load_ecb, load_nrb, nrb_payout
from riskdesk.forecast import forecast_frame
from riskdesk.risk import ALPHA, evaluate_policy, policy_pnl, rolling_risk


def test_ecb_inversion_sort_and_reference_cutoff(tmp_path):
    archive = tmp_path / "reference.zip"
    with ZipFile(archive, "w") as z:
        z.writestr("eurofxref-hist.csv", "Date,USD,JPY\n2026-01-02,1,150\n"
                   "2025-07-02,1.2,180\n2025-01-02,1.1,165\n")
    marks, provenance = load_ecb(archive)
    assert provenance["observations"] == 2
    assert provenance["last_date"] == "2025-07-02"
    assert len(provenance["sha256"]) == 64
    assert marks["JPYUSD"].tolist() == pytest.approx([1.1 / 165, 1.2 / 180])
    assert marks["available_at"].dt.hour.tolist() == [16, 15]


def test_nrb_unit_order_and_payout_side(tmp_path):
    snapshot = tmp_path / "nrb.json"
    entries = [
        {"date": "2025-12-31", "buy": "13600", "sell": "13700", "unit": 100},
        {"date": "2025-12-30", "buy": "134", "sell": "135", "unit": 1},
    ]
    snapshot.write_text(json.dumps({
        "source": NRB_URL, "from": "2025-12-30", "to": "2025-12-31",
        "records": [*entries, entries[-1]],
    }))
    quotes, provenance = load_nrb(snapshot)
    assert provenance["observations"] == 2
    payout = nrb_payout(quotes, npr_amount=136_000)
    assert payout["usd_at_buy"] == 1000
    assert payout["usd_at_mid"] < payout["usd_at_buy"]


def test_nrb_refuses_conflicting_quotes(tmp_path):
    snapshot = tmp_path / "nrb.json"
    record = {"date": "2025-12-31", "buy": 136, "sell": 137, "unit": 1}
    snapshot.write_text(json.dumps({
        "source": NRB_URL, "from": "2025-12-30", "to": "2025-12-31",
        "records": [record, {**record, "buy": 135}],
    }))
    with pytest.raises(ValueError, match="conflicting quotes"):
        load_nrb(snapshot)


def test_hedge_cancels_eur_leg_and_charges_prior_notional_across_gap():
    marks = pd.DataFrame(
        {"EURUSD": [1.1, 1.12], "JPYUSD": [0.006, 0.0061]},
        index=pd.to_datetime(["2025-01-03", "2025-01-06"]),
    )
    base = policy_pnl(marks, 0).iloc[0]
    hedge = policy_pnl(marks, 100).iloc[0]
    assert base.pnl == pytest.approx(20_000 - 9_000)
    assert hedge.fee == pytest.approx(16.5)
    assert hedge.pnl == pytest.approx(-9_000 - 16.5)


def test_rolling_risk_does_not_use_the_realized_day():
    initial = np.array([-10.0, -20.0, -5.0, -999.0, 0.0])
    scores = rolling_risk(initial, window=3, alpha=ALPHA)
    assert scores[:, 0].tolist() == [20, 999]
    assert scores[:, 1].tolist() == pytest.approx([20, 999])


def test_policy_exposes_coverage_stats_from_upstream():
    rng = np.random.default_rng(42)
    marks = pd.DataFrame(
        {"EURUSD": 1.12 + rng.normal(0, .003, 300).cumsum(),
         "JPYUSD": .0068 + rng.normal(0, .00002, 300).cumsum()},
        index=pd.bdate_range("2020-01-01", periods=300),
    )
    summary, points = evaluate_policy(marks, 75)
    assert summary["observations"] == len(points) == 49
    assert summary["breaches"] == sum(point["breach"] for point in points)
    assert all(0 <= summary[key] <= 1 for key in
               ("kupiec_p", "independence_p", "conditional_coverage_p"))


def test_forecast_features_are_invariant_to_future_marks():
    days = pd.bdate_range("2020-01-01", periods=75)
    marks = pd.DataFrame(
        {"EURUSD": np.linspace(1, 1.2, len(days)), "JPYUSD": np.linspace(.006, .007, len(days))},
        index=days,
    )
    original, outcome, date = forecast_frame(marks)
    altered = marks.copy()
    altered.loc[days[70]:, "EURUSD"] *= 2
    revised, revised_outcome, _ = forecast_frame(altered)
    pd.testing.assert_frame_equal(original.loc[:days[69]], revised.loc[:days[69]])
    assert date.loc[days[69]] == days[70]
    assert outcome.loc[days[69]] != revised_outcome.loc[days[69]]
