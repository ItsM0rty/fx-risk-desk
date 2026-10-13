const usdFormatter = new Intl.NumberFormat("en-US", {
  style: "currency", currency: "USD", maximumFractionDigits: 0,
});
const numberFormatter = new Intl.NumberFormat("en-US");
const monthFormatter = new Intl.DateTimeFormat("en-US", { month: "short", timeZone: "UTC" });
const dayFormatter = new Intl.DateTimeFormat("en-US", {
  day: "numeric", month: "short", year: "numeric", timeZone: "UTC",
});

export const usd = (value: number) => usdFormatter.format(value);
export const number = (value: number) => numberFormatter.format(value);
export const percent = (value: number, digits = 1) => `${(value * 100).toFixed(digits)}%`;
export const day = (date: string) => dayFormatter.format(new Date(`${date}T00:00:00Z`));
export const month = (date: string) => monthFormatter.format(new Date(`${date}T00:00:00Z`));
