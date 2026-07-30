import type { WardenData } from "../types";
import raw from "./warden_data.json";

// Real artifacts, produced by the live pipeline (real Ed25519 signatures, real
// counterfactual, real refusal). Regenerate with `npm run data`.
export const data = raw as unknown as WardenData;

export function stepById(id: number) {
  return data.session.steps.find((s) => s.i === id);
}

export const money = (n: unknown) =>
  typeof n === "number" ? "$" + n.toLocaleString("en-US") : String(n);
