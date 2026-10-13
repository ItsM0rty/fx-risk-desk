import { useEffect, useState } from "react";
import type { ForecastSeries, HedgeChoice, RiskSeries, RunSummary } from "@fx-risk-desk/client";
import { api, errorText, requireData } from "./api";
import { ForecastChart, RiskChart } from "./charts";
import { day, number, percent, usd } from "./format";
import { Options } from "./Options";

const HEDGES = ["0", "25", "50", "75", "100"] as const;

function Legend({ entries }: { entries: Array<[string, string]> }) {
  return (
    <ul className="legend" aria-label="Chart legend">
      {entries.map(([color, label]) => <li key={label}><i className={color} />{label}</li>)}
    </ul>
  );
}

function Metric({ label, value, note }: { label: string; value: string; note: string }) {
  return <div className="metric"><span>{label}</span><strong>{value}</strong><small>{note}</small></div>;
}

export function App() {
  const [hedge, setHedge] = useState<NonNullable<HedgeChoice>>("75");
  const [loaded, setLoaded] = useState<{ run: RunSummary; forecast: ForecastSeries }>();
  const [risk, setRisk] = useState<RiskSeries>();
  const [error, setError] = useState("");
  const [riskError, setRiskError] = useState("");

  useEffect(() => {
    const controller = new AbortController();
    Promise.all([
      api.GET("/api/v1/runs/latest", { signal: controller.signal }).then(requireData),
      api.GET("/api/v1/runs/latest/forecast", { signal: controller.signal }).then(requireData),
    ]).then(([run, forecast]) => {
      if (run.run_id !== forecast.run_id) throw new Error("The run changed. Reload to get the new snapshot.");
      if (!controller.signal.aborted) setLoaded({ run, forecast });
    }).catch((failure: unknown) => {
      if (!controller.signal.aborted) setError(errorText(failure));
    });
    return () => controller.abort();
  }, []);

  const runId = loaded?.run.run_id;
  useEffect(() => {
    if (!runId) return;
    const controller = new AbortController();
    setRiskError("");
    api.GET("/api/v1/runs/latest/risk", {
      params: { query: { hedge_pct: hedge } }, signal: controller.signal,
    }).then(requireData).then((series) => {
      if (series.run_id !== runId) throw new Error("The run changed. Reload to get the new snapshot.");
      if (!controller.signal.aborted) setRisk(series);
    }).catch((failure: unknown) => {
      if (!controller.signal.aborted) setRiskError(errorText(failure));
    });
    return () => controller.abort();
  }, [hedge, runId]);

  const run = loaded?.run;
  const policy = run?.policies.find(({ hedge_pct }) => String(hedge_pct) === hedge);
  const base = run?.policies.find(({ hedge_pct }) => hedge_pct === 0);
  const final = run?.forecast.final_year;

  return (
    <>
      <header className="topbar">
        <div className="topbar-inner">
          <a className="brand" href="#portfolio"><span className="brand-icon" aria-hidden="true"><i /><i /><i /></span>FX Risk Desk</a>
          <nav aria-label="Desk sections"><a href="#portfolio">Portfolio</a><a href="#forecast">Forecast</a><a href="#options">Options</a></nav>
          <span className="market-status"><i />Public reference data</span>
        </div>
      </header>
      <main id="portfolio">
        <div className="heading">
          <div><h1>Portfolio risk</h1><p>Hypothetical EUR and JPY book · USD reporting</p></div>
          {run && <div className="asof"><span>Reference date</span><strong>{day(run.as_of)}</strong></div>}
        </div>
        {error && <p className="panel empty error" role="alert">{error}</p>}
        {!error && !run && <p className="panel empty" role="status">Loading the risk snapshot…</p>}
        {run && policy && base && final && loaded && (
          <>
            <div className="hedge-bar">
              <div><label id="hedge-label">EUR exposure hedged</label><span>JPY exposure stays open</span></div>
              <div className="hedge-options" role="group" aria-labelledby="hedge-label">
                {HEDGES.map((ratio) => <button key={ratio} aria-pressed={hedge === ratio}
                  onClick={() => setHedge(ratio)}>{ratio}%</button>)}
              </div>
            </div>
            <section className="metrics" aria-label="Selected hedge policy metrics">
              <Metric label="Next-day 99% VaR" value={usd(policy.next_var)} note={`${usd(base.next_var)} unhedged`} />
              <Metric label="Next-day 99% ES" value={usd(policy.next_es)} note={`${usd(base.next_es)} unhedged`} />
              <Metric label="Observed breaches" value={percent(policy.breach_rate, 2)}
                note={`${number(policy.breaches)} of ${number(policy.observations)} days`} />
              <Metric label="Mean daily hedge cost" value={usd(policy.mean_daily_fee)} note={`${run.hedge_fee_bps} bps of covered notional`} />
            </section>
            <div className="risk-grid">
              <section className="panel" aria-labelledby="risk-heading">
                <div className="panel-head chart-head">
                  <div><h2 id="risk-heading">P&L and loss threshold</h2><p>Last 252 observations · USD</p></div>
                  <Legend entries={[["mint", "Selected policy"], ["blue", "Unhedged"], ["orange", "99% VaR"]]}/>
                </div>
                {riskError ? <p className="inline-state error" role="alert">{riskError}</p>
                  : risk?.hedge_pct === Number(hedge) ? <RiskChart points={risk.points} />
                    : <p className="chart risk-chart empty" role="status">Loading policy history…</p>}
                <p className="note">Daily P&L includes the stated hedge cost. The loss threshold uses the previous {run.risk_window} observations. Dots mark breaches.</p>
              </section>
              <aside className="panel book-panel" aria-labelledby="book-heading">
                <div className="panel-head"><div><h2 id="book-heading">Hypothetical book</h2><p>Signed FX exposure</p></div></div>
                <table className="data-table">
                  <thead><tr><th>Pair</th><th>Units</th><th>USD value</th></tr></thead>
                  <tbody>{run.positions.map((position) => <tr key={position.pair}>
                    <td>{position.pair}</td><td className={position.quantity < 0 ? "loss" : "gain"}>
                      {position.quantity > 0 ? "+" : ""}{number(position.quantity)}
                    </td><td>{usd(position.quantity * position.usd_mark)}</td>
                  </tr>)}</tbody>
                </table>
                <h3>Coverage backtest</h3>
                <dl className="stat-list">
                  <div><dt>Kupiec p-value</dt><dd>{policy.kupiec_p.toFixed(3)}</dd></div>
                  <div><dt>Independence p-value</dt><dd>{policy.independence_p.toFixed(3)}</dd></div>
                  <div><dt>Conditional coverage p-value</dt><dd>{policy.conditional_coverage_p.toFixed(3)}</dd></div>
                  <div><dt>Worst observed day</dt><dd className="loss">{usd(policy.worst_day)}</dd></div>
                </dl>
              </aside>
            </div>
            <div className="research-grid">
              <section className="panel forecast-panel" id="forecast" aria-labelledby="forecast-heading">
                <div className="panel-head chart-head">
                  <div><h2 id="forecast-heading">EUR/USD quantile forecast</h2><p>Next-observation return · last 120 predictions</p></div>
                  <Legend entries={[["blue", "P10–P90"], ["mint", "Observed"]]}/>
                </div>
                <ForecastChart points={loaded.forecast.points} />
                <h3>Final-year holdout</h3>
                <table className="data-table">
                  <thead><tr><th>Metric</th><th>XGBoost</th><th>Rolling baseline</th></tr></thead>
                  <tbody>
                    <tr><td>80% interval coverage</td><td>{percent(final.coverage)}</td><td>{percent(final.baseline_coverage)}</td></tr>
                    <tr><td>Mean interval width</td><td>{percent(final.mean_width, 2)}</td><td>{percent(final.baseline_width, 2)}</td></tr>
                    {run.forecast.quantiles.map((q, index) => <tr key={q}>
                      <td>P{Math.round(q * 100)} pinball loss (bps)</td>
                      <td>{(final.pinball[index] * 10_000).toFixed(2)}</td>
                      <td>{(final.baseline_pinball[index] * 10_000).toFixed(2)}</td>
                    </tr>)}
                  </tbody>
                </table>
                <p className="note">{number(final.observations)} holdout observations · {run.forecast.baseline_window}-observation baseline · {percent(run.forecast.raw_crossing_rate, 2)} raw crossing rate across all evaluation years.</p>
              </section>
              <Options spot={run.spot} />
            </div>
            <section className="panel remittance" aria-labelledby="payout-heading">
              <div><h2 id="payout-heading">USD to NPR payout</h2><p>Illustrative remittance scenario · NRB reference rates · {day(run.nrb_payout.date)}</p></div>
              <dl className="stat-list">
                <div><dt>NPR payout</dt><dd>{number(run.nrb_payout.npr_amount)} NPR</dd></div>
                <div><dt>Bank buys USD at</dt><dd>{run.nrb_payout.buy_npr_per_usd.toFixed(2)} NPR</dd></div>
                <div><dt>USD needed at buy rate</dt><dd>{usd(run.nrb_payout.usd_at_buy)}</dd></div>
                <div><dt>USD needed at midpoint</dt><dd>{usd(run.nrb_payout.usd_at_mid)}</dd></div>
              </dl>
            </section>
            <footer className="source-footer">
              <div><a href={run.sources.ecb.url}>ECB snapshot</a><span>{number(run.sources.ecb.observations)} marks</span></div>
              <div><a href="https://www.nrb.org.np/api-docs-v1/">NRB API</a><span>{number(run.sources.nrb.observations)} quotes</span></div>
              <span className="run-id">Run {run.run_id}</span>
            </footer>
          </>
        )}
      </main>
    </>
  );
}
