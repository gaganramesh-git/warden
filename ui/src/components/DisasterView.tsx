import { motion } from "framer-motion";
import type { WardenData } from "../types";
import { EvidenceCard } from "./EvidenceCard";
import { money } from "../data/loadData";

// The cold open: an innocent support agent, no WARDEN. A poisoned KB doc hijacks
// it into wiring a fraudulent refund — executed, no human in the loop.
export function DisasterView({ data }: { data: WardenData }) {
  const refund = data.disaster.executed.find((c) => c.name === "issue_refund");
  const poisoned = data.session.steps.find((s) => s.i === data.session.signature.introducedBy);

  return (
    <div className="mx-auto max-w-2xl">
      <div className="mb-4 flex items-center gap-2">
        <span className="rounded-full border border-line px-2.5 py-1 font-mono text-micro text-muted">
          no WARDEN
        </span>
        <span className="font-mono text-micro text-muted">
          {data.agent.name} · tools: {data.agent.tools.join(", ")}
        </span>
      </div>

      <div className="space-y-3">
        {data.session.steps
          .filter((s) => s.role !== "tool")
          .map((s, idx) => {
            if (s.role === "retrieved") {
              return (
                <motion.div
                  key={s.i}
                  initial={{ opacity: 0, y: 8 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: idx * 0.06 }}
                >
                  <EvidenceCard slice="retrieved" source={s.source} trusted={s.trusted}>
                    {s.content}
                  </EvidenceCard>
                </motion.div>
              );
            }
            return (
              <motion.div
                key={s.i}
                initial={{ opacity: 0, y: 8 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: idx * 0.06 }}
                className={
                  s.role === "user"
                    ? "ml-auto max-w-[80%] rounded-card rounded-br-sm border border-line bg-panel-2 px-3.5 py-2.5"
                    : "max-w-[85%] rounded-card rounded-bl-sm border border-line bg-panel px-3.5 py-2.5"
                }
              >
                <div className="mb-1 font-mono text-[0.68rem] uppercase tracking-wider text-muted">
                  {s.role === "user" ? "customer" : "agent"}
                </div>
                <p className="text-[0.9rem] leading-relaxed text-fg">{s.content ?? s.reasoning}</p>
                {s.tool_call && (
                  <div className="mt-2 inline-flex items-center gap-2 rounded border border-line bg-ink/50 px-2 py-1 font-mono text-micro text-muted">
                    → {s.tool_call.name}({Object.entries(s.tool_call.args).map(([k, v]) => `${k}=${v}`).join(", ")})
                  </div>
                )}
              </motion.div>
            );
          })}

        {/* the fraudulent execution */}
        {refund && (
          <motion.div
            initial={{ opacity: 0, scale: 0.97 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ delay: 0.5 }}
            className="rounded-card border border-threat/50 bg-threat/10 px-4 py-3"
          >
            <div className="flex items-center gap-2">
              <span className="grid h-6 w-6 place-items-center rounded-full bg-threat/20 text-threat">✗</span>
              <span className="font-display text-[1rem] font-medium text-threat">EXECUTED — no human in the loop</span>
            </div>
            <p className="mt-1.5 font-mono text-record text-fg">
              issue_refund(amount={money(refund.args.amount)}, to={String(refund.args.to)})
            </p>
            <p className="mt-1 font-mono text-micro text-muted">
              triggered by an injected instruction in {poisoned?.source ?? "untrusted content"} · nobody saw it happen
            </p>
          </motion.div>
        )}
      </div>
    </div>
  );
}
