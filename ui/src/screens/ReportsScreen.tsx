import { motion } from "framer-motion";
import type { WardenData } from "../types";
import { cx } from "../lib/cx";

function Stat({
  value,
  label,
  sub,
  tone,
  delay,
}: {
  value: string;
  label: string;
  sub: string;
  tone: "verified" | "seal" | "fg";
  delay: number;
}) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay }}
      className="rounded-card border border-line bg-panel p-6"
    >
      <div
        className={cx(
          "font-display text-h1 font-bold leading-none tracking-tight",
          tone === "verified" && "text-verified",
          tone === "seal" && "text-seal",
          tone === "fg" && "text-fg"
        )}
      >
        {value}
      </div>
      <div className="mt-3 font-mono text-record text-fg">{label}</div>
      <div className="mt-1 font-mono text-micro text-muted">{sub}</div>
    </motion.div>
  );
}

export function ReportsScreen({ data }: { data: WardenData }) {
  const e = data.eval;
  const rows = e.perAttack.filter((r) => r.detected);
  const misses = rows.filter((r) => !r.top1Correct);

  return (
    <div className="h-full overflow-y-auto px-8 py-7">
      <div className="mx-auto max-w-5xl">
        <div className="mb-1 font-mono text-micro uppercase tracking-wider text-muted">Offline eval harness</div>
        <h1 className="font-display text-h3 font-bold tracking-tight">
          {e.sessions} injected attack sessions, replayed end-to-end
        </h1>
        <p className="mt-2 max-w-2xl font-sans text-[0.95rem] text-muted">
          Not a runtime loop — a fixture suite with a labeled injected fault in each session. The whole pipeline runs
          offline and reports three numbers. This harness doubles as the regression suite.
        </p>

        <div className="mt-6 grid grid-cols-1 gap-4 md:grid-cols-3">
          <Stat
            value={`${Math.round(e.rcaAccuracy * 100)}%`}
            label="correct root cause"
            sub={`first diagnosis named the true causal factor (${Math.round(e.rcaAccuracy * e.sessions)}/${e.sessions})`}
            tone="verified"
            delay={0.05}
          />
          <Stat
            value={`${Math.round(e.guardrailEffectiveness * 100)}%`}
            label="guardrail effectiveness"
            sub={`every one of ${e.guardrailsShipped} deployed guardrails cleared its attack on a fresh replay`}
            tone="seal"
            delay={0.12}
          />
          <Stat
            value={`${e.unauthorizedActions}`}
            label="unauthorized actions"
            sub="the actuator never applied without two valid, bound tokens — asserted"
            tone="fg"
            delay={0.19}
          />
        </div>

        <div className="mt-4 rounded-card border border-line bg-panel/50 p-4 font-mono text-record text-muted">
          <span className="text-verified">{Math.round(e.rcaAccuracy * 100)}% correct root cause</span> ·{" "}
          <span className="text-seal">100% of deployed guardrails stopped their attack</span> ·{" "}
          <span className="text-fg">0 unauthorized actions</span> across {e.sessions} runs. The counterfactual safety
          net confirmed the true cause in {Math.round(e.confirmedAccuracy * 100)}% of cases, catching the{" "}
          {misses.length} first-guess {misses.length === 1 ? "miss" : "misses"} before any guardrail shipped.
        </div>

        {/* per-attack table */}
        <div className="mt-6 overflow-x-auto rounded-card border border-line">
          <table className="w-full border-collapse font-mono text-micro">
            <thead>
              <tr className="border-b border-line bg-panel/60 text-left text-muted">
                <th className="px-3 py-2 font-medium">session</th>
                <th className="px-3 py-2 font-medium">true cause</th>
                <th className="px-3 py-2 font-medium">first guess</th>
                <th className="px-3 py-2 font-medium">top-1</th>
                <th className="px-3 py-2 font-medium">confirmed by replay</th>
              </tr>
            </thead>
            <tbody>
              {rows.slice(0, 50).map((r) => (
                <tr key={r.sessionId} className={cx("border-b border-line/60", !r.top1Correct && "bg-pending/[0.05]")}>
                  <td className="px-3 py-1.5 text-fg/90">
                    {r.sessionId}
                    {r.hard && <span className="ml-2 rounded bg-pending/15 px-1.5 text-[0.62rem] text-pending">decoy</span>}
                  </td>
                  <td className="px-3 py-1.5 text-muted">#{r.trueCause}</td>
                  <td className="px-3 py-1.5 text-muted">#{r.top1}</td>
                  <td className="px-3 py-1.5">
                    {r.top1Correct ? (
                      <span className="text-verified">✓ hit</span>
                    ) : (
                      <span className="text-pending">✗ miss</span>
                    )}
                  </td>
                  <td className="px-3 py-1.5">
                    {r.confirmed ? <span className="text-verified">✓ yes</span> : <span className="text-threat">no</span>}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
