from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel

Hedge = Literal[0, 25, 50, 75, 100]
OptionKind = Literal["call", "put"]


class DataSource(BaseModel):
    url: str
    sha256: str
    observations: int
    first_date: date
    last_date: date


class Sources(BaseModel):
    ecb: DataSource
    nrb: DataSource


class Position(BaseModel):
    pair: str
    currency: str
    quantity: int
    usd_mark: float


class Policy(BaseModel):
    hedge_pct: Hedge
    next_var: float
    next_es: float
    observations: int
    breaches: int
    breach_rate: float
    mean_daily_fee: float
    kupiec_p: float
    independence_p: float
    conditional_coverage_p: float
    worst_day: float


class ForecastScores(BaseModel):
    observations: int
    first_date: date
    last_date: date
    pinball: list[float]
    baseline_pinball: list[float]
    coverage: float
    baseline_coverage: float
    mean_width: float
    baseline_width: float


class ForecastSummary(ForecastScores):
    quantiles: list[float]
    raw_crossing_rate: float
    baseline_window: int
    final_year: ForecastScores


class Payout(BaseModel):
    date: date
    npr_amount: float
    buy_npr_per_usd: float
    sell_npr_per_usd: float
    mid_npr_per_usd: float
    usd_at_buy: float
    usd_at_mid: float


class RunSummary(BaseModel):
    run_id: str
    as_of: date
    reporting_currency: Literal["USD"]
    spot: float
    positions: list[Position]
    tail_probability: float
    risk_window: int
    hedge_fee_bps: float
    sources: Sources
    policies: list[Policy]
    forecast: ForecastSummary
    nrb_payout: Payout


class RiskPoint(BaseModel):
    date: date
    pnl: float
    unhedged_pnl: float
    var: float
    es: float
    breach: bool


class RiskSeries(BaseModel):
    run_id: str
    hedge_pct: Hedge
    points: list[RiskPoint]


class ForecastPoint(BaseModel):
    date: date
    issued_at: datetime
    actual: float
    low: float
    median: float
    high: float


class ForecastSeries(BaseModel):
    run_id: str
    points: list[ForecastPoint]


class Greeks(BaseModel):
    delta: float
    gamma: float
    vega_per_point: float


class SpotShock(BaseModel):
    shock_pct: int
    spot: float
    value_usd: float
    pnl_usd: float


class OptionScenario(BaseModel):
    spot: float
    strike: float
    maturity_days: int
    volatility: float
    option_type: OptionKind
    notional_eur: int
    premium_per_eur: float
    premium_usd: float
    domestic_rate: float
    foreign_rate: float
    greeks: Greeks | None
    shocks: list[SpotShock]


class UnavailableRun(BaseModel):
    detail: str
