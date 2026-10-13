import createClient from "openapi-fetch";
import type { components, paths } from "./schema.js";

export type { components, paths } from "./schema.js";
export type RunSummary = components["schemas"]["RunSummary"];
export type RiskSeries = components["schemas"]["RiskSeries"];
export type ForecastSeries = components["schemas"]["ForecastSeries"];
export type OptionScenario = components["schemas"]["OptionScenario"];
export type HedgeChoice = NonNullable<
  paths["/api/v1/runs/latest/risk"]["get"]["parameters"]["query"]
>["hedge_pct"];

export function createRiskDeskClient(baseUrl = "", fetcher?: typeof fetch) {
  return createClient<paths>({ baseUrl, fetch: fetcher });
}
