import { Seal, type SealState } from "./Seal";
import type { Token } from "../types";
import { cx } from "../lib/cx";

interface Props {
  sealA: SealState;
  sealB: "empty" | "sealed";
  deployState: "locked" | "ready" | "deployed" | "refused";
  tokenA: Token;
  tokenB: Token;
}

function SlotRow({
  state,
  title,
  signer,
  hash,
  keyId,
}: {
  state: SealState;
  title: string;
  signer: string;
  hash: string;
  keyId: string;
}) {
  const filled = state === "sealed";
  const cracked = state === "cracked";
  return (
    <div
      className={cx(
        "flex items-center gap-3 rounded-[6px] border px-3 py-2.5 transition-colors",
        filled && "border-seal/40 bg-seal/[0.06]",
        cracked && "animate-threatpulse border-threat/50 bg-threat/[0.06]",
        state === "empty" && "border-line bg-ink/30"
      )}
    >
      <Seal state={state} glyph={title.startsWith("Rehearsal") ? "R" : "H"} size={42} />
      <div className="min-w-0 flex-1">
        <div className="flex items-center justify-between">
          <span className="font-sans text-[0.9rem] text-fg">{title}</span>
          <span
            className={cx(
              "font-mono text-[0.68rem]",
              filled ? "text-seal" : cracked ? "text-threat" : "text-muted"
            )}
          >
            {keyId}
          </span>
        </div>
        {filled ? (
          <p className="truncate font-mono text-[0.68rem] text-muted">
            {signer} · <span className="text-seal/90">{hash}</span>
          </p>
        ) : cracked ? (
          <p className="font-mono text-[0.68rem] text-threat">signature missing — stripped</p>
        ) : (
          <p className="font-mono text-[0.68rem] text-muted/60">awaiting signature</p>
        )}
      </div>
    </div>
  );
}

// Passive display of the two seals + the gate's verdict. The action that fills
// them lives in the StepGuide — this panel just shows the state that results.
export function SealSlots({ sealA, sealB, deployState, tokenA, tokenB }: Props) {
  const status = {
    locked: { text: "Locked — both signatures required", cls: "border-line bg-ink/40 text-muted" },
    ready: { text: "Both seals present — ready to deploy", cls: "border-seal/40 bg-seal/[0.07] text-seal" },
    deployed: { text: "✓ Deployed — actuator verified A + B", cls: "border-verified/40 bg-verified/10 text-verified" },
    refused: { text: "⛒ Refused — missing rehearsal signature", cls: "border-threat/50 bg-threat/10 text-threat" },
  }[deployState];

  return (
    <div className="rounded-card border border-line bg-panel p-4">
      <div className="mb-3 flex items-center justify-between">
        <span className="font-mono text-[0.7rem] uppercase tracking-wider text-muted">Seal slots</span>
        <span className="font-mono text-[0.68rem] text-muted/70">two signatures required</span>
      </div>

      <div className="space-y-2">
        <SlotRow state={sealA} title="Rehearsal seal" signer="sandbox" hash={tokenA.sigShort} keyId="KEY_A" />
        <SlotRow state={sealB} title="Human seal" signer={tokenB.approver ?? "operator"} hash={tokenB.sigShort} keyId="KEY_B" />
      </div>

      <div className={cx("mt-3 rounded-[6px] border px-3 py-2 text-center font-mono text-[0.72rem]", status.cls)}>
        {status.text}
      </div>
    </div>
  );
}
