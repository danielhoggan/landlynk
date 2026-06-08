import type { DataValue } from "./types/battlecard";

// Formatting helpers that honour ONS suppression: a suppressed or null cell
// shows as "Not available", never coerced to zero (house-standards.md).

export function fmtValue(
  dv: DataValue,
  opts?: Intl.NumberFormatOptions,
): string {
  if (dv.value === null) {
    return dv.suppressed ? "Suppressed" : "Not available";
  }
  return new Intl.NumberFormat("en-GB", opts).format(dv.value);
}

export function fmtCurrency(dv: DataValue): string {
  return fmtValue(dv, {
    style: "currency",
    currency: "GBP",
    maximumFractionDigits: 0,
  });
}

export function fmtPercent(dv: DataValue): string {
  if (dv.value === null) {
    return dv.suppressed ? "Suppressed" : "Not available";
  }
  return `${dv.value.toFixed(1)}%`;
}
