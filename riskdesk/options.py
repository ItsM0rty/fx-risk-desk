from fx_options.garman_kohlhagen import gk_price
from fx_options.greeks import analytic_greeks

SHOCKS = (-5, -2, 0, 2, 5)
DOMESTIC_RATE = 0.04
FOREIGN_RATE = 0.025


def price_scenario(
    spot: float, strike: float, maturity_days: int, volatility: float, notional: int,
    option_type: str,
) -> dict:
    expiry = maturity_days / 365
    premium = gk_price(spot, strike, expiry, DOMESTIC_RATE, FOREIGN_RATE, volatility, option_type)
    greeks = None
    if volatility > 0:
        g = analytic_greeks(spot, strike, expiry, DOMESTIC_RATE, FOREIGN_RATE, volatility, option_type)
        greeks = {"delta": g.delta_spot, "gamma": g.gamma, "vega_per_point": g.vega / 100}
    values = []
    for shock in SHOCKS:
        shifted_spot = spot * (1 + shock / 100)
        shifted_price = gk_price(
            shifted_spot, strike, expiry, DOMESTIC_RATE, FOREIGN_RATE, volatility, option_type
        )
        values.append({
            "shock_pct": shock, "spot": shifted_spot,
            "value_usd": shifted_price * notional,
            "pnl_usd": (shifted_price - premium) * notional,
        })
    return {
        "spot": spot, "strike": strike, "maturity_days": maturity_days, "volatility": volatility,
        "option_type": option_type, "notional_eur": notional, "premium_per_eur": premium,
        "premium_usd": premium * notional, "domestic_rate": DOMESTIC_RATE,
        "foreign_rate": FOREIGN_RATE, "greeks": greeks, "shocks": values,
    }
