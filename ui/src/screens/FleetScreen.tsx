import type { WardenData } from "../types";
import type { Machine } from "../lib/useDemoMachine";
import { LiveStrip } from "../components/LiveStrip";
import { StatusBadge, type StatusKind } from "../components/ui/StatusBadge";
import { cx } from "../lib/cx";

interface Agent {
  name: string;
  purpose: string;
  tools: string[];
  status: StatusKind;
  lastCase: string;
  real?: boolean;
}

function heroStatus(m: Machine): StatusKind {
  if (m.isRefusal) return "attack";
  if (m.reached("deployed")) return "resolved";
  if (m.reached("rehearsal")) return "sealed";
  if (m.reached("catch")) return "attack";
  return "watching";
}

export function FleetScreen({ data, m, onOpenCase }: { data: WardenData; m: Machine; onOpenCase: () => void }) {
  const agents: Agent[] = [
    {
      name: data.agent.name,
      purpose: data.agent.purpose,
      tools: data.agent.tools,
      status: heroStatus(m),
      lastCase: data.case.id,
      real: true,
    },
    { name: "billing-agent", purpose: "Handles invoices and payment status.", tools: ["get_invoice", "charge_card"], status: "watching", lastCase: "—" },
    { name: "ops-copilot", purpose: "Runbook automation for on-call.", tools: ["restart_service", "read_logs"], status: "healthy", lastCase: "—" },
    { name: "data-analyst", purpose: "Answers questions over the warehouse.", tools: ["run_query", "export_csv"], status: "healthy", lastCase: "—" },
  ];

  return (
    <div className="h-full overflow-y-auto px-8 py-7">
      <div className="mx-auto max-w-5xl">
        <div className="mb-4 flex items-end justify-between">
          <div>
            <div className="font-mono text-micro uppercase tracking-wider text-muted">Fleet</div>
            <h1 className="font-display text-h3 font-bold tracking-tight">Monitored agents</h1>
          </div>
          <span className="font-mono text-micro text-muted">4 agents · 1 active case</span>
        </div>

        <LiveStrip data={data} />

        <div className="mt-5 grid grid-cols-1 gap-4 sm:grid-cols-2">
          {agents.map((a) => {
            const attack = a.status === "attack";
            return (
              <button
                key={a.name}
                onClick={a.real ? onOpenCase : undefined}
                className={cx(
                  "group relative overflow-hidden rounded-card border bg-panel p-4 text-left transition-colors",
                  attack ? "border-threat/50" : "border-line hover:border-seal/40",
                  !a.real && "cursor-default opacity-80"
                )}
              >
                {attack && <span className="absolute inset-x-0 top-0 h-[2px] animate-pulse bg-threat" />}
                <div className="flex items-start justify-between">
                  <div className="flex items-center gap-2">
                    <div
                      className={cx(
                        "grid h-9 w-9 place-items-center rounded-[6px] font-mono text-micro",
                        attack ? "bg-threat/15 text-threat" : "bg-panel-2 text-muted"
                      )}
                    >
                      {a.name.slice(0, 2).toUpperCase()}
                    </div>
                    <div>
                      <div className="font-sans text-[0.98rem] font-medium text-fg">{a.name}</div>
                      <div className="font-mono text-[0.68rem] text-muted">
                        {a.tools.join(" · ")}
                      </div>
                    </div>
                  </div>
                  <StatusBadge kind={a.status} pulse={attack} />
                </div>
                <p className="mt-3 text-[0.86rem] leading-relaxed text-muted">{a.purpose}</p>
                <div className="mt-3 flex items-center justify-between border-t border-line pt-2 font-mono text-[0.68rem] text-muted">
                  <span>last case: {a.lastCase}</span>
                  {a.real && <span className="text-seal opacity-0 transition-opacity group-hover:opacity-100">open →</span>}
                </div>
              </button>
            );
          })}
        </div>

        <p className="mt-5 font-mono text-[0.68rem] text-muted/60">
          support-agent carries the live demo case. The other three are illustrative monitored agents (no active
          incidents) to show the fleet surface.
        </p>
      </div>
    </div>
  );
}
