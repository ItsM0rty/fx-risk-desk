import hashlib
from pathlib import Path
from zipfile import ZipFile

import numpy as np
import pandas as pd

ECB_URL = "https://www.ecb.europa.eu/stats/eurofxref/eurofxref-hist.zip"
NRB_URL = "https://www.nrb.org.np/api/forex/v1/rates"
ECB_TIMEZONE = "Europe/Berlin"
ECB_START = "2010-01-01"
ECB_END = "2025-12-31"


def _manifest(path: Path, url: str, dates: pd.DatetimeIndex) -> dict:
    return {
        "url": url,
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "observations": len(dates),
        "first_date": dates[0].date().isoformat(),
        "last_date": dates[-1].date().isoformat(),
    }


def load_ecb(path: Path) -> tuple[pd.DataFrame, dict]:
    with ZipFile(path) as archive, archive.open("eurofxref-hist.csv") as csv:
        quotes = pd.read_csv(csv, usecols=["Date", "USD", "JPY"], na_values=["N/A"])
    quotes["Date"] = pd.to_datetime(quotes["Date"], format="%Y-%m-%d")
    quotes = quotes.set_index("Date").sort_index().loc[ECB_START:ECB_END]
    if quotes.empty or quotes.index.has_duplicates:
        raise ValueError("ECB history is empty or has duplicate reference dates")
    values = quotes[["USD", "JPY"]].to_numpy(dtype=float)
    if not np.isfinite(values).all() or (values <= 0).any():
        raise ValueError("ECB history has an invalid quote")
    marks = pd.DataFrame(
        {"EURUSD": quotes["USD"], "JPYUSD": quotes["USD"] / quotes["JPY"]},
        index=quotes.index,
    )
    # An explicit conservative as-of convention for the daily research replay.
    marks["available_at"] = (
        (marks.index + pd.Timedelta(hours=17)).tz_localize(ECB_TIMEZONE).tz_convert("UTC")
    )
    return marks, _manifest(path, ECB_URL, marks.index)


def load_nrb(path: Path) -> tuple[pd.DataFrame, dict]:
    import json

    snapshot = json.loads(path.read_text(encoding="utf-8"))
    if snapshot["source"] != NRB_URL:
        raise ValueError("Unexpected NRB snapshot source")
    quotes = pd.DataFrame(snapshot["records"], columns=["date", "buy", "sell", "unit"])
    quotes["date"] = pd.to_datetime(quotes["date"], format="%Y-%m-%d")
    for field in ("buy", "sell", "unit"):
        quotes[field] = pd.to_numeric(quotes[field], errors="raise")
    quotes = quotes.drop_duplicates().set_index("date").sort_index()
    if quotes.empty or quotes.index.has_duplicates:
        raise ValueError("NRB history is empty or has conflicting quotes on a date")
    if not quotes.index.to_series().between(snapshot["from"], snapshot["to"]).all():
        raise ValueError("NRB history contains dates outside its requested range")
    if not np.isfinite(quotes.to_numpy()).all() or (quotes <= 0).any().any():
        raise ValueError("NRB history has an invalid quote or unit")
    if (quotes["sell"] < quotes["buy"]).any():
        raise ValueError("NRB history has an inverted spread")
    normalized = quotes[["buy", "sell"]].div(quotes["unit"], axis=0)
    normalized["mid"] = normalized[["buy", "sell"]].mean(axis=1)
    return normalized, _manifest(path, NRB_URL, normalized.index)


def nrb_payout(quotes: pd.DataFrame, npr_amount: float = 10_000_000) -> dict:
    quote = quotes.iloc[-1]
    # The bank buys the operator's USD and provides NPR in this illustrative payout.
    return {
        "date": quotes.index[-1].date().isoformat(),
        "npr_amount": npr_amount,
        "buy_npr_per_usd": float(quote["buy"]),
        "sell_npr_per_usd": float(quote["sell"]),
        "mid_npr_per_usd": float(quote["mid"]),
        "usd_at_buy": npr_amount / quote["buy"],
        "usd_at_mid": npr_amount / quote["mid"],
    }
