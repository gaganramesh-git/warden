import { motion } from "framer-motion";
import type { Verdict } from "../types";
import { cx } from "../lib/cx";

// Space Grotesk cause line, confidence, counterfactual result chip (UI/UX §6).
export function VerdictCard({ verdict, revealed }: { verdict: Verdict; revealed: boolean }) {
  return (
    <div className="rounded-card border border-line bg-panel p-4">
      <div className="mb-2 flex items-center justify-between">
        <span className="font-mono text-[0.7rem] uppercase tracking-wider text-muted">Root cause</span>
        {revealed && verdict.counterfactual.confirmed && (
          <motion.span
            initial={{ scale: 0.8, opacity: 0 }}
            animate={{ scale: 1, opacity: 1 }}
            className="inline-flex items-center gap-1 rounded-full border border-verified/40 bg-verified/10 px-2 py-0.5 font-mono text-micro font-medium text-verified"
          >
            ✓ confirmed by replay
          </motion.span>
        )}
      </div>

      {revealed ? (
        <motion.p
          initial={{ opacity: 0, y: 6 }}
          animate={{ opacity: 1, y: 0 }}
          className="font-display text-h4 font-medium leading-tight text-fg"
        >
          {verdict.rootCauseText}
        </motion.p>
      ) : (
        <p className="font-display text-h4 font-medium leading-tight text-muted/50">— analyzing —</p>
      )}

      <div className="mt-3 flex items-center gap-3">
        <div className="flex-1">
          <div className="mb-1 flex items-center justify-between font-mono text-micro text-muted">
            <span>confidence</span>
            <span className={cx(revealed ? "text-fg" : "text-muted/50")}>
              {revealed ? verdict.confidence.toFixed(2) : "—"}
            </span>
          </div>
          <div className="h-1.5 overflow-hidden rounded-full bg-ink">
            <motion.div
              className="h-full rounded-full bg-seal"
              initial={{ width: 0 }}
              animate={{ width: revealed ? `${verdict.confidence * 100}%` : 0 }}
              transition={{ duration: 0.6, ease: "easeOut" }}
            />
          </div>
        </div>
      </div>

      {revealed && (
        <p className="mt-3 border-t border-line pt-2 font-mono text-micro text-muted">
          counterfactual: strike input #{verdict.counterfactual.factor} → misbehavior signature no longer fires ·{" "}
          <span className="text-muted/70">run {verdict.counterfactual.sandboxRunId}</span>
        </p>
      )}
    </div>
  );
}
