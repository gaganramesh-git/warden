import { motion } from "framer-motion";
import type { Machine } from "../lib/useDemoMachine";
import type { Beat, ScenarioData } from "../types";
import { cx } from "../lib/cx";

type Kind = "primary" | "reset";

// Action wiring is fixed per beat; the TEXT comes from the active scenario, so
// injection / loop / code-tampering each narrate the same 9 beats their own way.
interface Action {
  n: number;
  kind: Kind;
  run: (m: Machine) => void;
  secondaryKind?: "danger" | "back";
  secondaryRun?: (m: Machine) => void;
}

const ACTIONS: Record<Beat, Action> = {
  disaster: { n: 1, kind: "primary", run: (m) => m.next() },
  catch: { n: 2, kind: "primary", run: (m) => m.next() },
  evidence: { n: 3, kind: "primary", run: (m) => m.next() },
  proof: { n: 4, kind: "primary", run: (m) => m.next() },
  fix: { n: 5, kind: "primary", run: (m) => m.next() },
  rehearsal: { n: 6, kind: "primary", run: (m) => m.next() },
  approval: { n: 7, kind: "primary", run: (m) => m.next() },
  deployed: {
    n: 8, kind: "reset", run: (m) => m.restart(),
    secondaryKind: "danger", secondaryRun: (m) => m.gotoRefusal(),
  },
  refusal: {
    n: 9, kind: "reset", run: (m) => m.restart(),
    secondaryKind: "back", secondaryRun: (m) => m.goto("deployed"),
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

export function StepGuide({ m, scenario }: { m: Machine; scenario: ScenarioData }) {
  const a = ACTIONS[m.beat];
  const text = scenario.steps[m.beat];
  const keyA = m.reached("rehearsal") && !m.isRefusal;
  const keyB = m.reached("approval");

  return (
    <div className="rounded-card border border-seal/30 bg-panel p-4 shadow-panel">
      {/* progress */}
      <div className="mb-3 flex items-center justify-between">
        <span className="font-mono text-[0.7rem] uppercase tracking-wider text-muted">
          Step {a.n} of {TOTAL}
        </span>
        <div className="flex gap-1">
          {Array.from({ length: TOTAL }).map((_, i) => (
            <span
              key={i}
              className={cx(
                "h-1.5 w-3.5 rounded-full transition-colors",
                i + 1 < a.n && "bg-seal/50",
                i + 1 === a.n && (m.isRefusal ? "bg-threat" : m.reached("deployed") ? "bg-verified" : "bg-seal"),
                i + 1 > a.n && "bg-line"
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
        {text.title}
      </motion.h2>
      <motion.p
        key={m.beat + "-s"}
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        className="mt-1.5 text-[0.86rem] leading-relaxed text-muted"
      >
        {text.status}
      </motion.p>

      {/* seal feedback */}
      <div className="mt-3 flex gap-2">
        <SealChip label="Rehearsal · KEY_A" on={keyA} />
        <SealChip label="Human · KEY_B" on={keyB} />
      </div>

      {/* the single primary action */}
      <button
        onClick={() => a.run(m)}
        className={cx(
          "mt-4 flex w-full items-center justify-center gap-2 rounded-[6px] px-4 py-3 font-sans text-[0.95rem] font-medium transition-transform active:scale-[0.99]",
          a.kind === "primary" && "bg-seal text-white hover:bg-seal/90",
          a.kind === "reset" && "bg-panel-2 text-fg ring-1 ring-line hover:bg-panel-2/70"
        )}
      >
        {text.actionLabel}
        {a.kind === "primary" && <span aria-hidden>▸</span>}
      </button>

      {/* optional, clearly-separate secondary action (e.g. the refusal demo) */}
      {a.secondaryKind && text.secondaryLabel && (
        <button
          onClick={() => a.secondaryRun!(m)}
          className={cx(
            "mt-2 flex w-full items-center justify-center rounded-[6px] px-3 py-2 font-mono text-[0.72rem] transition-colors",
            a.secondaryKind === "danger" && "border border-threat/30 bg-threat/[0.05] text-threat/90 hover:bg-threat/10",
            a.secondaryKind === "back" && "border border-line text-muted hover:text-fg"
          )}
        >
          {text.secondaryLabel}
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
