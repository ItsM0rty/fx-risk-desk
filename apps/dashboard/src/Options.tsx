import { useEffect, useState, type FormEvent } from "react";
import type { OptionScenario } from "@itsm0rty/fx-risk-desk-client";
import { api, errorText, requireData } from "./api";
import { percent, usd } from "./format";

export function Options({ spot }: { spot: number }) {
  const [scenario, setScenario] = useState<OptionScenario>();
  const [request, setRequest] = useState({
    option_type: "put" as "call" | "put", strike: spot, maturity_days: 90, volatility: 0.09,
  });
  const [error, setError] = useState("");
  const [pending, setPending] = useState(true);

  useEffect(() => {
    const controller = new AbortController();
    setPending(true);
    setError("");
    api.GET("/api/v1/options/scenario", { params: { query: request }, signal: controller.signal })
      .then(requireData)
      .then((value) => {
        if (!controller.signal.aborted) {
          setScenario(value);
          setPending(false);
        }
      })
      .catch((failure: unknown) => {
        if (!controller.signal.aborted) {
          setError(errorText(failure));
          setPending(false);
        }
      });
    return () => controller.abort();
  }, [request]);

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const fields = new FormData(event.currentTarget);
    setRequest({
      option_type: fields.get("kind") === "call" ? "call" : "put",
      strike: Number(fields.get("strike")),
      maturity_days: Number(fields.get("days")),
      volatility: Number(fields.get("volatility")) / 100,
    });
  }

  return (
    <section className="panel option-panel" id="options" aria-labelledby="option-heading">
      <div className="panel-head">
        <div><h2 id="option-heading">FX option scenario</h2><p>EUR/USD European option · €1m notional</p></div>
      </div>
      <form className="option-form" onSubmit={submit}>
        <label>Type<select name="kind" defaultValue="put"><option value="put">Put</option><option value="call">Call</option></select></label>
        <label>Strike<input name="strike" type="number" min="0.0001" max="10" step="0.0001" defaultValue={spot.toFixed(4)} required /></label>
        <label>Expiry (days)<input name="days" type="number" min="1" max="730" defaultValue="90" required /></label>
        <label>Volatility (%)<input name="volatility" type="number" min="0" max="200" step="0.1" defaultValue="9" required /></label>
        <button className="price-button" disabled={pending}>Reprice</button>
      </form>
      {pending && <p className="inline-state" role="status">Pricing scenario…</p>}
      {error && <p className="inline-state error" role="alert">{error}</p>}
      {scenario && !pending && !error && (
        <>
          <div className="option-values">
            <div><span>Premium</span><strong>{usd(scenario.premium_usd)}</strong></div>
            <div><span>Spot delta</span><strong>{scenario.greeks?.delta.toFixed(3) ?? "—"}</strong></div>
            <div><span>Gamma</span><strong>{scenario.greeks?.gamma.toFixed(3) ?? "—"}</strong></div>
            <div><span>Vega / vol pt.</span><strong>{scenario.greeks ? usd(scenario.greeks.vega_per_point * scenario.notional_eur) : "—"}</strong></div>
          </div>
          <table className="data-table">
            <thead><tr><th>Spot shock</th><th>USD option value</th><th>USD change</th></tr></thead>
            <tbody>{scenario.shocks.map((shock) => (
              <tr key={shock.shock_pct}>
                <td>{shock.shock_pct > 0 ? "+" : ""}{shock.shock_pct}%</td>
                <td>{usd(shock.value_usd)}</td>
                <td className={shock.pnl_usd < 0 ? "loss" : shock.pnl_usd > 0 ? "gain" : ""}>{usd(shock.pnl_usd)}</td>
              </tr>
            ))}</tbody>
          </table>
          <p className="note">The shocks hold expiry, volatility and rates fixed. Assumed rates are {percent(scenario.domestic_rate)} USD and {percent(scenario.foreign_rate)} EUR.</p>
        </>
      )}
    </section>
  );
}
