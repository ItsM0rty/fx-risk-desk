import { createRiskDeskClient } from "@fx-risk-desk/client";

export const api = createRiskDeskClient();

export function requireData<T>(result: { data?: T; error?: unknown; response: Response }): T {
  if (result.data !== undefined) return result.data;
  const detail = result.error as { detail?: unknown } | undefined;
  throw new Error(typeof detail?.detail === "string"
    ? detail.detail
    : `The API returned HTTP ${result.response.status}.`);
}

export const errorText = (error: unknown) =>
  error instanceof Error ? error.message : "The request failed.";
