import { useEffect, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import type { WardenData } from "../types";
import type { Machine } from "../lib/useDemoMachine";
import { EvidenceCard } from "./EvidenceCard";
import { Seal } from "./Seal";
import { cx } from "../lib/cx";
import { money, stepById } from "../data/loadData";

type DotKind = "system" | "evidence" | "seal" | "threat" | "verified";

const DOT: Record<DotKind, string> = {
  system: "border-line bg-panel-2",
  evidence: "border-paper/60 bg-paper",
  seal: "border-seal bg-seal",
  threat: "border-threat bg-threat",
  verified: "border-verified bg-verified",
};

function Node({
  reached,
  dot,
  active,
  stamp,
  title,
  status,
  children,
}: {
  reached: boolean;
  dot: DotKind;
  active?: boolean;
  stamp: string;
  title: React.ReactNode;
  status?: React.ReactNode;
  children?: React.ReactNode;
}) {
  return (
    <li className={cx("relative pl-11 pb-6 transition-opacity duration-500", !reached && "opacity-35")}>
      {/* marker on the spine */}
      <span
        className={cx(
          "absolute left-[7px] top-1 grid h-[18px] w-[18px] place-items-center rounded-full border-2",
          reached ? DOT[dot] : "border-line bg-ink",
          active && "ring-4 ring-seal/20"
        )}
      >
        {!reached && <span className="h-1 w-1 rounded-full bg-muted/50" />}
      </span>

      <div className="flex items-center justify-between">
        <h3 className="font-display text-[1.02rem] font-medium tracking-tight text-fg">{title}</h3>
        <span className="font-mono text-[0.68rem] text-muted">{stamp}</span>
      </div>
      {status && <div className="mt-0.5">{status}</div>}
      {reached && children && <div className="mt-2.5">{children}</div>}
    </li>
  );
}

export function ChainOfCustody({ data, m }: { data: WardenData; m: Machine }) {
  const c = data.case;
  const poisoned = stepById(c.signature.introducedBy);
  const refund = data.disaster.executed.find((x) => x.name === "issue_refund");

  // The counterfactual reveal timeline (the intellectual "aha").
  const reachedProof = m.reached("proof");
  const [struck, setStruck] = useState(false);
  const [faded, setFaded] = useState(false);
  useEffect(() => {
    if (!reachedProof) {
      setStruck(false);
      setFaded(false);
      return;
    }
    if (m.beat === "proof") {
      setStruck(false);
      setFaded(false);
      const t1 = window.setTimeout(() => setStruck(true), 420);
      const t2 = window.setTimeout(() => setFaded(true), 980);
      return () => {
        window.clearTimeout(t1);
        window.clearTimeout(t2);
      };
    }
    setStruck(true);
    setFaded(true);
  }, [m.beat, reachedProof]);

  const dimOthers = m.beat === "proof"; // dim everything else, let the reveal own the frame

  return (
    <ol className="spine relative">
      {/* 1 · DETECTION */}
      <Node
        reached={m.reached("catch")}
        dot="threat"
        active={m.beat === "catch"}
        stamp="t+0:40"
        title="Detection"
        status={
          <span className="inline-flex items-center gap-1.5 font-mono text-micro text-threat">
            <span className="h-1.5 w-1.5 rounded-full bg-threat" />
            injection · refund call frozen
          </span>
        }
      >
        <div className={cx("transition-opacity", dimOthers && "opacity-40")}>
          <p className="font-mono text-record text-muted">
            sensitive call <span className="text-threat">{c.signature.sensitiveCall}</span> introduced by untrusted
            input <span className="text-fg">#{c.signature.introducedBy}</span> — intercepted before execution.
          </p>
        </div>
      </Node>

      {/* 2 · EVIDENCE — four disjoint partitions */}
      <Node
        reached={m.reached("evidence")}
        dot="evidence"
        active={m.beat === "evidence"}
        stamp="t+1:00"
        title="Evidence"
        status={<span className="font-mono text-micro text-muted">four generators, each on a disjoint slice</span>}
      >
        <div className={cx("grid grid-cols-2 gap-2 transition-opacity", dimOthers && "opacity-40")}>
          {c.hypotheses.map((h, i) => {
            const winner = h.suspectFactor === c.verdict.rootCause && h.evidenceSlice === "retrieved";
            return (
              <motion.div
                key={h.gen}
                initial={{ opacity: 0, y: 6 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: m.beat === "evidence" ? i * 0.14 : 0 }}
                className={cx(
                  "rounded-[6px] border px-2.5 py-2",
                  winner ? "border-seal/50 bg-seal/[0.07]" : "border-line bg-ink/40"
                )}
              >
                <div className="flex items-center justify-between font-mono text-[0.68rem]">
                  <span className="text-muted">
                    [{h.gen}] {h.evidenceSlice}
                  </span>
                  <span className={cx(winner ? "text-seal" : "text-muted/70")}>{h.confidence.toFixed(2)}</span>
                </div>
                <p className="mt-1 text-[0.78rem] leading-snug text-fg/85">blames #{h.suspectFactor}</p>
              </motion.div>
            );
          })}
        </div>
      </Node>

      {/* 3 · PROOF — the counterfactual (money moment) */}
      <Node
        reached={reachedProof}
        dot={faded ? "verified" : "evidence"}
        active={m.beat === "proof"}
        stamp="t+1:05"
        title={
          <AnimatePresence mode="wait">
            {faded ? (
              <motion.span
                key="confirmed"
                initial={{ opacity: 0, y: 4 }}
                animate={{ opacity: 1, y: 0 }}
                className="font-display font-bold tracking-tight text-verified"
              >
                CAUSE CONFIRMED
              </motion.span>
            ) : (
              <motion.span key="proving" initial={{ opacity: 1 }} exit={{ opacity: 0 }}>
                Proof — counterfactual replay
              </motion.span>
            )}
          </AnimatePresence>
        }
      >
        <div className="space-y-3">
          {/* the suspect line, struck through on reveal */}
          <EvidenceCard slice="untrusted" source={poisoned?.source} trusted={false} struck={struck}>
            {poisoned?.content}
          </EvidenceCard>

          {/* replayed outcome: the malicious action fades out of the timeline */}
          <div className="rounded-[6px] border border-line bg-ink/40 px-3 py-2.5">
            <div className="mb-1.5 font-mono text-[0.68rem] uppercase tracking-wider text-muted">
              replay without input #{c.verdict.counterfactual.factor}
            </div>
            <AnimatePresence>
              {!faded ? (
                <motion.div
                  key="mal"
                  initial={{ opacity: 1 }}
                  animate={{ opacity: struck ? 0.35 : 1 }}
                  exit={{ opacity: 0, height: 0, marginTop: 0 }}
                  transition={{ duration: 0.4 }}
                  className="flex items-center gap-2 font-mono text-record text-threat"
                >
                  <span>✗</span> issue_refund(amount={money(refund?.args.amount)}, to={String(refund?.args.to)})
                </motion.div>
              ) : (
                <motion.div
                  key="clean"
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  className="flex items-center gap-2 font-mono text-record text-verified"
                >
                  <span>✓</span> the malicious call never appears — attack vanished
                </motion.div>
              )}
            </AnimatePresence>
            <div className="mt-1.5 font-mono text-record text-muted">
              ✓ lookup_account — legitimate task still completes
            </div>
          </div>
        </div>
      </Node>

      {/* 4 · REHEARSAL SEAL */}
      <SealNode
        reached={m.reached("rehearsal")}
        active={m.beat === "rehearsal"}
        state={m.sealA}
        stamp="t+1:55"
        title="Rehearsal seal"
        sub={
          m.sealA === "cracked"
            ? "signature stripped"
            : m.reached("rehearsal")
              ? `KEY_A · ${c.rehearsal.tokenA.sigShort}`
              : "awaiting rehearsal"
        }
      />

      {/* 5 · HUMAN SEAL */}
      <SealNode
        reached={m.reached("approval")}
        active={m.beat === "approval"}
        state={m.sealB === "sealed" ? "sealed" : "empty"}
        stamp="t+2:15"
        title="Human seal"
        sub={m.reached("approval") ? `KEY_B · ${c.approval.approver}` : "awaiting approval"}
      />

      {/* 6 · ACTUATION */}
      <Node
        reached={m.reached("deployed")}
        dot={m.isRefusal ? "threat" : "verified"}
        active={m.beat === "deployed" || m.isRefusal}
        stamp="t+2:35"
        title={
          m.isRefusal ? (
            <span className="font-display font-bold tracking-tight text-threat">ACTUATION REFUSED</span>
          ) : (
            "Actuation"
          )
        }
        status={
          m.isRefusal ? (
            <span className="font-mono text-micro text-threat">missing rehearsal signature — nothing deployed</span>
          ) : m.reached("deployed") ? (
            <span className="font-mono text-micro text-verified">guardrail deployed · attack now blocked</span>
          ) : (
            <span className="font-mono text-micro text-muted">verify A + B, then apply</span>
          )
        }
      >
        {m.reached("deployed") && !m.isRefusal && (
          <div className="rounded-[6px] border border-verified/30 bg-verified/[0.06] px-3 py-2.5 font-mono text-record">
            <span className="text-muted">re-run attack vs live policy:</span>{" "}
            <span className="text-verified">blocked ✓</span>
            <span className="ml-2 text-muted">· executed {JSON.stringify(c.rerun.executed)}</span>
          </div>
        )}
      </Node>
    </ol>
  );
}

function SealNode({
  reached,
  active,
  state,
  stamp,
  title,
  sub,
}: {
  reached: boolean;
  active?: boolean;
  state: "empty" | "sealed" | "cracked";
  stamp: string;
  title: string;
  sub: string;
}) {
  return (
    <li className={cx("relative pl-11 pb-6 transition-opacity duration-500", !reached && "opacity-35")}>
      <span className={cx("absolute left-[1px] top-0 rounded-full", active && "ring-4 ring-seal/20")}>
        <Seal state={reached ? state : "empty"} glyph={title.startsWith("Rehearsal") ? "R" : "H"} size={30} />
      </span>
      <div className="flex items-center justify-between">
        <h3
          className={cx(
            "font-display text-[1.02rem] font-medium tracking-tight",
            state === "cracked" ? "text-threat" : reached ? "text-seal" : "text-fg"
          )}
        >
          {title}
        </h3>
        <span className="font-mono text-[0.68rem] text-muted">{stamp}</span>
      </div>
      <p className={cx("mt-0.5 font-mono text-micro", state === "cracked" ? "text-threat" : "text-muted")}>{sub}</p>
    </li>
  );
}
