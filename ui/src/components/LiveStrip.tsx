import type { WardenData } from "../types";

// Top-of-Fleet ticker of session events in mono (UI/UX §6).
export function LiveStrip({ data }: { data: WardenData }) {
  const evs = [
    `session ${data.session.id} ingested · ${data.session.steps.length} steps`,
    `⚑ INJECTION detected on ${data.agent.name} · call ${data.case.signature.sensitiveCall} frozen`,
    `diagnosis: 4 partitions · critic ranked #${data.case.verdict.rootCause}`,
    `counterfactual confirmed · run ${data.case.verdict.counterfactual.sandboxRunId}`,
    `◆ rehearsal seal signed KEY_A · ${data.case.rehearsal.tokenA.sigShort}`,
    `◆ human seal signed KEY_B · ${data.case.approval.approver}`,
    `guardrail ${data.case.guardrail.id} deployed · rollback issued`,
  ];
  const line = evs.join("      •      ");
  return (
    <div className="relative overflow-hidden rounded-card border border-line bg-panel/60">
      <div className="flex items-center gap-2 px-3 py-2">
        <span className="flex shrink-0 items-center gap-1.5 font-mono text-micro text-verified">
          <span className="relative h-1.5 w-1.5 rounded-full bg-verified">
            <span className="absolute inset-0 animate-ping rounded-full bg-verified opacity-70" />
          </span>
          live
        </span>
        <div className="relative flex-1 overflow-hidden">
          <div className="ticker whitespace-nowrap font-mono text-micro text-muted">
            {line}
            <span className="mx-8">•</span>
            {line}
          </div>
        </div>
      </div>
      <style>{`
        .ticker { display: inline-block; padding-left: 100%; animation: warden-ticker 34s linear infinite; }
        @keyframes warden-ticker { from { transform: translateX(0); } to { transform: translateX(-50%); } }
        @media (prefers-reduced-motion: reduce) { .ticker { animation: none; padding-left: 0; } }
      `}</style>
    </div>
  );
}
