import numpy as np
import pandas as pd
from fx_var.backtesting import evaluate_var_backtest
from fx_var.expected_shortfall import empirical_var_es

POSITIONS = {"EURUSD": 1_000_000, "JPYUSD": -90_000_000}
HEDGE_PCTS = (0, 25, 50, 75, 100)
HEDGE_FEE_BPS = 0.15
WINDOW = 250
ALPHA = 0.01


def policy_pnl(marks: pd.DataFrame, hedge_pct: int) -> pd.DataFrame:
    if hedge_pct not in HEDGE_PCTS:
        raise ValueError("Unsupported hedge percentage")
    moves = marks[list(POSITIONS)].diff()
    legs = moves.mul(POSITIONS)
    unhedged = legs.sum(axis=1, min_count=len(POSITIONS))
    eur_notional = marks["EURUSD"].shift(1) * POSITIONS["EURUSD"] * hedge_pct / 100
    fees = eur_notional * HEDGE_FEE_BPS / 10_000
    pnl = unhedged - legs["EURUSD"] * hedge_pct / 100 - fees
    return pd.DataFrame({"unhedged": unhedged, "pnl": pnl, "fee": fees}).iloc[1:]


def rolling_risk(pnl: np.ndarray, window: int = WINDOW, alpha: float = ALPHA) -> np.ndarray:
    if len(pnl) <= window or window < 1:
        raise ValueError("More than one estimation window of P&L is required")
    past = np.lib.stride_tricks.sliding_window_view(pnl[:-1], window)
    return np.array([empirical_var_es(sample, alpha=alpha) for sample in past])


def evaluate_policy(marks: pd.DataFrame, hedge_pct: int) -> tuple[dict, list[dict]]:
    history = policy_pnl(marks, hedge_pct)
    var_es = rolling_risk(history["pnl"].to_numpy())
    evaluation = history.iloc[WINDOW:]
    realized = evaluation["pnl"].to_numpy()
    result = evaluate_var_backtest(realized, var_es[:, 0], alpha=ALPHA)
    next_var, next_es = empirical_var_es(history["pnl"].to_numpy()[-WINDOW:], alpha=ALPHA)
    summary = {
        "hedge_pct": hedge_pct,
        "next_var": next_var,
        "next_es": next_es,
        "observations": len(realized),
        "breaches": int(result.n_exceptions),
        "breach_rate": float(result.exception_rate),
        "mean_daily_fee": float(evaluation["fee"].mean()),
        "kupiec_p": float(result.kupiec_p),
        "independence_p": float(result.independence_p),
        "conditional_coverage_p": float(result.cc_p),
        "worst_day": float(realized.min()),
    }
    series = [
        {
            "date": day.date().isoformat(),
            "pnl": float(pnl),
            "unhedged_pnl": float(unhedged),
            "var": float(var),
            "es": float(es),
            "breach": bool(breach),
        }
        for (day, unhedged, pnl, _fee), (var, es), breach
        in zip(evaluation.itertuples(), var_es, result.exceedances, strict=True)
    ]
    return summary, series
