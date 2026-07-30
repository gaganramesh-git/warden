import { AnimatePresence, motion } from "framer-motion";
import type { WardenData } from "../types";
import type { Machine } from "../lib/useDemoMachine";
import { StepGuide } from "../components/StepGuide";
import { DisasterView } from "../components/DisasterView";
import { ChainOfCustody } from "../components/ChainOfCustody";
import { VerdictCard } from "../components/VerdictCard";
import { SealSlots } from "../components/SealSlots";
import { ApprovalPanel } from "../components/ApprovalPanel";
import { RefusalBanner } from "../components/RefusalBanner";
import { StatusBadge, type StatusKind } from "../components/ui/StatusBadge";

function caseStatus(m: Machine): { kind: StatusKind; label: string } {
  if (m.isRefusal) return { kind: "attack", label: "Deploy refused" };
  if (m.reached("deployed")) return { kind: "resolved", label: "Resolved" };
  if (m.reached("rehearsal")) return { kind: "sealed", label: "Sealing the fix" };
  if (m.reached("proof")) return { kind: "awaiting", label: "Fixing" };
  if (m.reached("catch")) return { kind: "attack", label: "Under attack" };
  return { kind: "watching", label: "Live" };
}

export function CaseScreen({ data, m }: { data: WardenData; m: Machine }) {
  const st = caseStatus(m);
  const showChain = m.beat !== "disaster";

  return (
    <div className="flex h-full overflow-hidden">
      {/* CENTER — the chain of custody */}
      <section className="flex-1 overflow-y-auto px-6 py-5">
        <AnimatePresence>
          {m.isRefusal && (
            <motion.div className="mb-5" initial={{ opacity: 0 }} animate={{ opacity: 1 }}>
              <RefusalBanner reason={data.case.refusal.reason} stateUnchanged={data.case.refusal.stateUnchanged} />
            </motion.div>
          )}
        </AnimatePresence>

        <div className="mb-5 flex items-center justify-between">
          <div>
            <div className="flex items-center gap-2 font-mono text-micro text-muted">
              <span>{showChain ? data.case.id : "cold open"}</span>
              <span className="text-muted/40">·</span>
              <span>{data.agent.name}</span>
            </div>
            <h1 className="mt-0.5 font-display text-h3 font-bold tracking-tight">
              {showChain ? "Chain of custody" : "Agent running in production"}
            </h1>
          </div>
          <StatusBadge kind={st.kind} label={st.label} pulse={st.kind === "attack"} />
        </div>

        <AnimatePresence mode="wait">
          {showChain ? (
            <motion.div key="chain" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}>
              <ChainOfCustody data={data} m={m} />
            </motion.div>
          ) : (
            <motion.div key="disaster" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}>
              <DisasterView data={data} />
            </motion.div>
          )}
        </AnimatePresence>
      </section>

      {/* RIGHT — the control rail: one clear action, then the evidence it produces */}
      <aside className="w-[372px] shrink-0 space-y-4 overflow-y-auto border-l border-line bg-panel/30 px-4 py-5">
        <StepGuide m={m} />

        <VerdictCard verdict={data.case.verdict} revealed={m.reached("proof")} />

        <AnimatePresence>
          {m.reached("fix") && (
            <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }}>
              <ApprovalPanel data={data} approved={m.reached("approval")} />
            </motion.div>
          )}
        </AnimatePresence>

        <SealSlots
          sealA={m.sealA}
          sealB={m.sealB}
          deployState={m.deployState}
          tokenA={data.case.rehearsal.tokenA}
          tokenB={data.case.approval.tokenB}
        />

        <div className="rounded-card border border-line bg-panel/60 p-3">
          <p className="font-mono text-[0.68rem] leading-relaxed text-muted">
            The actuator holds <span className="text-fg">verify-only</span> keys. It checks both signatures over the
            same plan &amp; rehearsal — it cannot forge either. Strip one and it refuses.
          </p>
        </div>
      </aside>
    </div>
  );
}
