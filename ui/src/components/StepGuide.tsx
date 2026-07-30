import { motion } from "framer-motion";
import type { Machine } from "../lib/useDemoMachine";
import type { Beat } from "../types";
import { cx } from "../lib/cx";

type Kind = "primary" | "danger" | "reset";

interface Secondary {
  label: string;
  kind: "danger" | "back";
  run: (m: Machine) => void;
}

interface Step {
  n: number;
  title: string;
  status: string;
  actionLabel: string;
  kind: Kind;
  run: (m: Machine) => void;
  secondary?: Secondary;
}

// One clear action per step. You drive it; nothing auto-advances unless you
// press Auto-play. Each primary click advances the case by exactly one move and
// stamps the corresponding seal as a direct, visible result.
const STEPS: Record<Beat, Step> = {
  disaster: {
    n: 1, title: "The agent was hijacked",
    status: "A poisoned document made the agent wire a fraudulent refund — executed, no human in the loop.",
    actionLabel: "Turn WARDEN on & replay", kind: "primary", run: (m) => m.next(),
  },
  catch: {
    n: 2, title: "Injection caught",
    status: "WARDEN intercepted the refund the instant the agent acted on untrusted content. It's frozen, not executed.",
    actionLabel: "Investigate — gather the evidence", kind: "primary", run: (m) => m.next(),
  },
  evidence: {
    n: 3, title: "Four generators disagree",
    status: "Each generator blames a different step. We don't trust any of them — the replay will decide.",
    actionLabel: "Prove the cause by replay", kind: "primary", run: (m) => m.next(),
  },
  proof: {
    n: 4, title: "Cause confirmed",
    status: "Remove the poisoned input, replay the exact session, and the attack vanishes. That's a proof, not a guess.",
    actionLabel: "Propose the fix", kind: "primary", run: (m) => m.next(),
  },
  fix: {
    n: 5, title: "Guardrail written",
    status: "WARDEN proposes a guardrail. Rehearse it in the sandbox to earn the KEY_A signature.",
    actionLabel: "Rehearse fix → sign KEY_A", kind: "primary", run: (m) => m.next(),
  },
  rehearsal: {
    n: 6, title: "Rehearsal passed · KEY_A signed",
    status: "Attack cleared and the legit task still works, so the sandbox signed the rehearsal seal. Now a human must approve.",
    actionLabel: "Approve fix → sign KEY_B", kind: "primary", run: (m) => m.next(),
  },
  approval: {
    n: 7, title: "Human approved · KEY_B signed",
    status: "Both signatures are now present and bound to the same plan and the same rehearsal.",
    actionLabel: "Deploy the guardrail", kind: "primary", run: (m) => m.next(),
  },
  deployed: {
    n: 8, title: "Guardrail deployed ✓",
    status: "Done. The actuator verified BOTH signatures and applied the fix — the attack is now blocked and your approved guardrail is live. That's the full safe path.",
    actionLabel: "↺ Run through again", kind: "reset", run: (m) => m.restart(),
    secondary: {
      label: "Optional: try a tampered deploy with NO rehearsal →",
      kind: "danger", run: (m) => m.gotoRefusal(),
    },
  },
  refusal: {
    n: 9, title: "Refused — exactly as intended",
    status: "This was a SEPARATE, tampered deploy with the rehearsal signature stripped out. The actuator hard-refused and changed nothing — the guardrail you approved earlier is still live and untouched. It can check proof; it can't forge it.",
    actionLabel: "↺ Start over", kind: "reset", run: (m) => m.restart(),
    secondary: {
      label: "‹ Back to the deployed fix",
      kind: "back", run: (m) => m.goto("deployed"),
    },
  },
};

const TOTAL = 9;

function SealChip({ label, on }: { label: string; on: boolean }) {
  return (
    <span
      className={cx(
        "inline-flex items-center gap-1.5 rounded-full border px-2 py-0.5 font-mono text-[0.68rem] transition-colors",
        on ? "border-seal/50 bg-seal/10 text-seal" : "border-line text-muted/60"
      )}
    >
      <span className={cx("h-1.5 w-1.5 rounded-full", on ? "bg-seal" : "bg-muted/40")} />
      {label} {on ? "✓" : "·"}
    </span>
  );
}

export function StepGuide({ m }: { m: Machine }) {
  const step = STEPS[m.beat];
  const keyA = m.reached("rehearsal") && !m.isRefusal;
  const keyB = m.reached("approval");

  return (
    <div className="rounded-card border border-seal/30 bg-panel p-4 shadow-panel">
      {/* progress */}
      <div className="mb-3 flex items-center justify-between">
        <span className="font-mono text-[0.7rem] uppercase tracking-wider text-muted">
          Step {step.n} of {TOTAL}
        </span>
        <div className="flex gap-1">
          {Array.from({ length: TOTAL }).map((_, i) => (
            <span
              key={i}
              className={cx(
                "h-1.5 w-3.5 rounded-full transition-colors",
                i + 1 < step.n && "bg-seal/50",
                i + 1 === step.n && (step.kind === "danger" ? "bg-threat" : step.kind === "reset" ? "bg-muted" : "bg-seal"),
                i + 1 > step.n && "bg-line"
              )}
            />
          ))}
        </div>
      </div>

      <motion.h2
        key={m.beat + "-t"}
        initial={{ opacity: 0, y: 4 }}
        animate={{ opacity: 1, y: 0 }}
        className={cx(
          "font-display text-h4 font-medium leading-tight",
          m.isRefusal ? "text-threat" : m.reached("deployed") ? "text-verified" : "text-fg"
        )}
      >
        {step.title}
      </motion.h2>
      <motion.p
        key={m.beat + "-s"}
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        className="mt-1.5 text-[0.86rem] leading-relaxed text-muted"
      >
        {step.status}
      </motion.p>

      {/* seal feedback */}
      <div className="mt-3 flex gap-2">
        <SealChip label="Rehearsal · KEY_A" on={keyA} />
        <SealChip label="Human · KEY_B" on={keyB} />
      </div>

      {/* the single primary action */}
      <button
        onClick={() => step.run(m)}
        className={cx(
          "mt-4 flex w-full items-center justify-center gap-2 rounded-[6px] px-4 py-3 font-sans text-[0.95rem] font-medium transition-transform active:scale-[0.99]",
          step.kind === "primary" && "bg-seal text-white hover:bg-seal/90",
          step.kind === "danger" && "border border-threat/50 bg-threat/10 text-threat hover:bg-threat/15",
          step.kind === "reset" && "bg-panel-2 text-fg ring-1 ring-line hover:bg-panel-2/70"
        )}
      >
        {step.actionLabel}
        {step.kind === "primary" && <span aria-hidden>▸</span>}
      </button>

      {/* optional, clearly-separate secondary action (e.g. the refusal demo) */}
      {step.secondary && (
        <button
          onClick={() => step.secondary!.run(m)}
          className={cx(
            "mt-2 flex w-full items-center justify-center rounded-[6px] px-3 py-2 font-mono text-[0.72rem] transition-colors",
            step.secondary.kind === "danger" && "border border-threat/30 bg-threat/[0.05] text-threat/90 hover:bg-threat/10",
            step.secondary.kind === "back" && "border border-line text-muted hover:text-fg"
          )}
        >
          {step.secondary.label}
        </button>
      )}

      {/* quiet secondary controls */}
      <div className="mt-3 flex items-center justify-between font-mono text-[0.7rem] text-muted">
        <button
          onClick={m.prev}
          disabled={m.atStart}
          className="rounded px-1.5 py-1 transition-colors hover:text-fg disabled:opacity-30"
        >
          ‹ Back
        </button>
        <button
          onClick={m.togglePlay}
          className={cx("rounded px-2 py-1 transition-colors hover:text-fg", m.playing && "text-seal")}
        >
          {m.playing ? "❚❚ Pause auto-play" : "▶ Auto-play"}
        </button>
      </div>
    </div>
  );
}
