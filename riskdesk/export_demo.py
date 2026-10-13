"""Export bounded, derived results for the static portfolio demo."""
import argparse
import json
from itertools import product
from pathlib import Path

from .options import price_scenario
from .run import DEFAULT_OUTPUT, write_run

KINDS = ("put", "call")
EXPIRIES = (30, 90, 180)
VOL_PCTS = (6, 9, 12, 15)
MONEYNESS_PCTS = (95, 100, 105)
RISK_POINTS = 252
FORECAST_POINTS = 120


def export_demo(run: dict) -> dict:
    summary = run["summary"]
    spot = summary["spot"]
    presets = {
        f"{kind}:{days}:{vol}:{strike_pct}": price_scenario(
            spot, spot * strike_pct / 100, days, vol / 100, 1_000_000, kind
        )
        for kind, days, vol, strike_pct in product(KINDS, EXPIRIES, VOL_PCTS, MONEYNESS_PCTS)
    }

    return {
        "run_id": summary["run_id"],
        "as_of": summary["as_of"],
        "risk_window": summary["risk_window"],
        "hedge_fee_bps": summary["hedge_fee_bps"],
        "policies": summary["policies"],
        "positions": summary["positions"],
        "forecast": summary["forecast"],
        "nrb_payout": {
            key: summary["nrb_payout"][key]
            for key in ("date", "npr_amount", "usd_at_buy", "usd_at_mid")
        },
        "ecb_observations": summary["sources"]["ecb"]["observations"],
        "risk_series": {
            ratio: [
                [point["date"], round(point["pnl"], 2), round(point["unhedged_pnl"], 2),
                 -round(point["var"], 2), point["breach"]]
                for point in points[-RISK_POINTS:]
            ]
            for ratio, points in run["risk_series"].items()
        },
        "forecast_series": [
            [point["date"], point["actual"], point["low"], point["median"], point["high"]]
            for point in run["forecast_series"][-FORECAST_POINTS:]
        ],
        "option_presets": presets,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    snapshot = json.loads(args.run.read_text(encoding="utf-8"))
    write_run(args.output, export_demo(snapshot))


if __name__ == "__main__":
    main()
