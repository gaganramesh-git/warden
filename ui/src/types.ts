// Types mirror the JSON emitted by demo/build_ui_data.py (real pipeline output).

export interface Step {
  i: number;
  role: "user" | "retrieved" | "assistant" | "tool";
  content?: string;
  reasoning?: string;
  source?: string;
  trusted?: boolean;
  tool_call?: { name: string; args: Record<string, unknown> };
  tool?: string;
  output?: Record<string, unknown>;
}

export interface Token {
  kind: "REHEARSAL_PASS" | "HUMAN_APPROVAL";
  keyId: "KEY_A" | "KEY_B";
  alg: string;
  approver?: string | null;
  sig: string;
  sigShort: string;
  nonce: string;
  planHash: string;
  sandboxRunId: string;
  exp: number;
}

export interface Hypothesis {
  gen: "A" | "B" | "C" | "D";
  evidenceSlice: "tool_io" | "instructions" | "retrieved" | "reasoning";
  suspectFactor: number;
  confidence: number;
  evidence: string;
}

export interface Verdict {
  rootCause: number;
  rootCauseText: string;
  confidence: number;
  rankedCauses: number[];
  counterfactual: { factor: number; sandboxRunId: string; confirmed: boolean };
}

export interface Guardrail {
  id: string;
  description: string;
  json: Record<string, unknown>;
  cedar: string;
  planHash: string;
}

export interface StepText {
  title: string;
  status: string;
  actionLabel: string;
  secondaryLabel?: string;
}
export type ScenarioSteps = Record<string, StepText>;

export interface WardenCase {
  id: string;
  type: string;
  severity: string;
  signature: { sensitiveCall: string; introducedBy: number };
  hypotheses: Hypothesis[];
  verdict: Verdict;
  guardrail: Guardrail;
  rehearsal: {
    sandboxRunId: string;
    misbehaviorCleared: boolean;
    taskStillCompletes: boolean;
    tokenA: Token;
  };
  approval: { approver: string; blastRadius: string; tokenB: Token };
  deploy: { status: string; appliedGuardrailId?: string; rollbackToken?: string; refusalReason?: string | null };
  rerun: { executed: string[]; attackBlocked: boolean; guardrailActive: string | null };
  refusal: { status: string; reason: string; stateUnchanged: boolean };
}

// One end-to-end demo scenario (agent + attack + case + its step narrative).
export interface ScenarioData {
  id: string;
  label: string;
  attackType: string;
  agent: { name: string; purpose: string; tools: string[] };
  session: { id: string; steps: Step[]; signature: { sensitiveCall: string; introducedBy: number } };
  disaster: { sessionId: string; executed: { name: string; args: Record<string, unknown>; introducedBy: number }[] };
  steps: ScenarioSteps;
  case: WardenCase;
}

export interface WardenData {
  scenarios: ScenarioData[];
  eval: {
    rcaAccuracy: number;
    confirmedAccuracy: number;
    guardrailEffectiveness: number;
    unauthorizedActions: number;
    sessions: number;
    guardrailsShipped: number;
    perAttack: {
      sessionId: string;
      detected: boolean;
      trueCause?: number;
      top1?: number;
      top1Correct?: boolean;
      confirmed?: boolean;
      hard?: boolean;
    }[];
  };
}

// ---- the demo beat machine ------------------------------------------------
export type Beat =
  | "disaster"
  | "catch"
  | "evidence"
  | "proof"
  | "fix"
  | "rehearsal"
  | "approval"
  | "deployed"
  | "refusal";

export const BEATS: { id: Beat; label: string; t: string }[] = [
  { id: "disaster", label: "The disaster", t: "0:00" },
  { id: "catch", label: "The catch", t: "0:40" },
  { id: "evidence", label: "Evidence", t: "1:00" },
  { id: "proof", label: "The proof", t: "1:05" },
  { id: "fix", label: "The fix", t: "1:25" },
  { id: "rehearsal", label: "Rehearsal seal", t: "1:55" },
  { id: "approval", label: "Human seal", t: "2:15" },
  { id: "deployed", label: "Deployed", t: "2:30" },
  { id: "refusal", label: "The refusal", t: "2:35" },
];
