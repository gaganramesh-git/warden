import type { ScenarioData } from "../types";

// Top-of-Fleet ticker of session events in mono (UI/UX §6).
export function LiveStrip({ scenario }: { scenario: ScenarioData }) {
  const c = scenario.case;
  const evs = [
    `session ${scenario.session.id} ingested · ${scenario.session.steps.length} steps`,
    `⚑ ${c.type.toUpperCase()} detected on ${scenario.agent.name} · call ${c.signature.sensitiveCall} frozen`,
    `diagnosis: 4 partitions · critic ranked #${c.verdict.rootCause}`,
    `counterfactual confirmed · run ${c.verdict.counterfactual.sandboxRunId}`,
    `◆ rehearsal seal signed KEY_A · ${c.rehearsal.tokenA.sigShort}`,
    `◆ human seal signed KEY_B · ${c.approval.approver}`,
    `guardrail ${c.guardrail.id} deployed · rollback issued`,
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
