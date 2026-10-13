import argparse
import hashlib
import json
import os
import tempfile
from pathlib import Path

from .data import load_ecb, load_nrb, nrb_payout
from .forecast import evaluate_forecasts
from .risk import ALPHA, HEDGE_FEE_BPS, HEDGE_PCTS, POSITIONS, WINDOW, evaluate_policy

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = ROOT / "data" / "runs" / "latest.json"


def create_run(raw: Path) -> dict:
    marks, ecb = load_ecb(raw / "ecb-eurofxref-hist.zip")
    nrb_quotes, nrb = load_nrb(raw / "nrb-usd-npr.json")
    policies, series = [], {}
    for ratio in HEDGE_PCTS:
        policy, series[str(ratio)] = evaluate_policy(marks, ratio)
        policies.append(policy)
    forecast, forecast_series = evaluate_forecasts(marks)
    contents = {
        "summary": {
            "as_of": ecb["last_date"],
            "reporting_currency": "USD",
            "spot": float(marks["EURUSD"].iloc[-1]),
            "positions": [
                {"pair": "EUR/USD", "currency": "EUR", "quantity": POSITIONS["EURUSD"],
                 "usd_mark": float(marks["EURUSD"].iloc[-1])},
                {"pair": "JPY/USD", "currency": "JPY", "quantity": POSITIONS["JPYUSD"],
                 "usd_mark": float(marks["JPYUSD"].iloc[-1])},
            ],
            "tail_probability": ALPHA,
            "risk_window": WINDOW,
            "hedge_fee_bps": HEDGE_FEE_BPS,
            "sources": {"ecb": ecb, "nrb": nrb},
            "policies": policies,
            "forecast": forecast,
            "nrb_payout": nrb_payout(nrb_quotes),
        },
        "risk_series": series,
        "forecast_series": forecast_series,
    }
    canonical = json.dumps(contents, sort_keys=True, separators=(",", ":"), allow_nan=False)
    contents["summary"]["run_id"] = hashlib.sha256(canonical.encode()).hexdigest()[:16]
    return contents


def write_run(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        "w", encoding="utf-8", dir=path.parent, suffix=".tmp", delete=False
    ) as stream:
        temp = Path(stream.name)
        try:
            json.dump(data, stream, separators=(",", ":"), allow_nan=False)
        except Exception:
            stream.close()
            temp.unlink(missing_ok=True)
            raise
    try:
        os.replace(temp, path)
    finally:
        temp.unlink(missing_ok=True)


def main() -> None:
    parser = argparse.ArgumentParser(description="Compute the public-data FX risk snapshot.")
    parser.add_argument("--raw", type=Path, default=ROOT / "data" / "raw")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    result = create_run(args.raw)
    write_run(args.output, result)
    print(f"Saved run {result['summary']['run_id']} to {args.output}")


if __name__ == "__main__":
    main()
