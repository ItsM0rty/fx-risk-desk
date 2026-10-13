import numpy as np
import pandas as pd
import xgboost as xgb

QUANTILES = np.array([0.1, 0.5, 0.9])
FIRST_EVALUATION_YEAR = 2020
BASELINE_WINDOW = 250
ROUNDS = 100
SEED = 42


def forecast_frame(marks: pd.DataFrame) -> tuple[pd.DataFrame, pd.Series, pd.Series]:
    eur = marks["EURUSD"].pct_change()
    jpy = marks["JPYUSD"].pct_change()
    features = pd.DataFrame({
        "eur_1d": eur,
        "eur_5d": marks["EURUSD"].pct_change(5),
        "eur_20d": marks["EURUSD"].pct_change(20),
        "eur_vol_20d": eur.rolling(20).std(),
        "eur_vol_60d": eur.rolling(60).std(),
        "jpy_1d": jpy,
        "jpy_vol_20d": jpy.rolling(20).std(),
    })
    outcomes = pd.Series(marks.index, index=marks.index).shift(-1)
    return features, eur.shift(-1), outcomes


def _pinball(actual: np.ndarray, predicted: np.ndarray) -> list[float]:
    error = actual[:, None] - predicted
    return np.maximum(QUANTILES * error, (QUANTILES - 1) * error).mean(axis=0).tolist()


def evaluate_forecasts(marks: pd.DataFrame) -> tuple[dict, list[dict]]:
    features, target, outcome_dates = forecast_frame(marks)
    prior_returns = marks["EURUSD"].pct_change()
    baseline = np.column_stack([
        prior_returns.rolling(BASELINE_WINDOW).quantile(q).to_numpy() for q in QUANTILES
    ])
    ready = features.notna().all(axis=1) & target.notna()
    predicted_parts, baseline_parts, actual_parts, results = [], [], [], []
    crossing_count = 0

    for year in range(FIRST_EVALUATION_YEAR, marks.index[-1].year + 1):
        cut = pd.Timestamp(year=year, month=1, day=1)
        train = ready & (outcome_dates < cut)
        test = ready & (outcome_dates.dt.year == year)
        if not test.any():
            continue
        if train.sum() < BASELINE_WINDOW:
            raise ValueError("Insufficient history for annual walk-forward training")
        train_matrix = xgb.QuantileDMatrix(features.loc[train].to_numpy(), label=target.loc[train].to_numpy(), nthread=2)
        model = xgb.train(
            {
                "objective": "reg:quantileerror", "tree_method": "hist",
                "quantile_alpha": QUANTILES, "seed": SEED, "nthread": 2,
                "max_depth": 3, "eta": 0.05,
            },
            train_matrix,
            num_boost_round=ROUNDS,
        )
        raw = model.inplace_predict(features.loc[test].to_numpy())
        crossing_count += int((np.diff(raw, axis=1) < 0).any(axis=1).sum())
        prediction = np.sort(raw, axis=1)
        actual = target.loc[test].to_numpy()
        base = baseline[test.to_numpy()]
        if not np.isfinite(prediction).all() or not np.isfinite(base).all():
            raise ValueError("Quantile evaluation contains a non-finite forecast")
        predicted_parts.append(prediction)
        baseline_parts.append(base)
        actual_parts.append(actual)
        for origin, outcome, value, (low, median, high) in zip(
            features.index[test], outcome_dates.loc[test], actual, prediction, strict=True
        ):
            results.append({
                "date": outcome.date().isoformat(),
                "issued_at": marks.at[origin, "available_at"].isoformat(),
                "actual": float(value),
                "low": float(low),
                "median": float(median),
                "high": float(high),
            })

    if not results:
        raise ValueError("No walk-forward evaluation observations")
    prediction = np.concatenate(predicted_parts)
    base = np.concatenate(baseline_parts)
    actual = np.concatenate(actual_parts)
    final_count = len(actual_parts[-1])
    return {
        **_scores(actual, prediction, base, results),
        "quantiles": QUANTILES.tolist(),
        "raw_crossing_rate": crossing_count / len(actual),
        "baseline_window": BASELINE_WINDOW,
        "final_year": _scores(
            actual_parts[-1], predicted_parts[-1], baseline_parts[-1], results[-final_count:]
        ),
    }, results


def _scores(actual: np.ndarray, prediction: np.ndarray, base: np.ndarray, points: list[dict]) -> dict:
    coverage = (prediction[:, 0] <= actual) & (actual <= prediction[:, 2])
    base_coverage = (base[:, 0] <= actual) & (actual <= base[:, 2])
    return {
        "observations": len(actual),
        "first_date": points[0]["date"],
        "last_date": points[-1]["date"],
        "pinball": _pinball(actual, prediction),
        "baseline_pinball": _pinball(actual, base),
        "coverage": float(coverage.mean()),
        "baseline_coverage": float(base_coverage.mean()),
        "mean_width": float(np.mean(prediction[:, 2] - prediction[:, 0])),
        "baseline_width": float(np.mean(base[:, 2] - base[:, 0])),
    }
