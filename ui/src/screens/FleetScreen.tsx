import type { ScenarioData } from "../types";
import type { Machine } from "../lib/useDemoMachine";
import { LiveStrip } from "../components/LiveStrip";
import { StatusBadge, type StatusKind } from "../components/ui/StatusBadge";
import { cx } from "../lib/cx";

// Each real scenario is a monitored agent you can open. The active one reflects
// where the demo machine currently is; the others sit idle until selected.
function statusFor(active: boolean, m: Machine): StatusKind {
  if (!active) return "watching";
  if (m.isRefusal) return "attack";
  if (m.reached("deployed")) return "resolved";
  if (m.reached("rehearsal")) return "sealed";
  if (m.reached("catch")) return "attack";
  return "watching";
}

export function FleetScreen({
  scenarios,
  activeId,
  m,
  onOpenCase,
}: {
  scenarios: ScenarioData[];
  activeId: string;
  m: Machine;
  onOpenCase: (id: string) => void;
}) {
  const active = scenarios.find((s) => s.id === activeId) ?? scenarios[0];

  return (
    <div className="h-full overflow-y-auto px-8 py-7">
      <div className="mx-auto max-w-5xl">
        <div className="mb-4 flex items-end justify-between">
          <div>
            <div className="font-mono text-micro uppercase tracking-wider text-muted">Fleet</div>
            <h1 className="font-display text-h3 font-bold tracking-tight">Monitored agents</h1>
          </div>
          <span className="font-mono text-micro text-muted">
            {scenarios.length} agent{scenarios.length === 1 ? "" : "s"} · {scenarios.length} case
            {scenarios.length === 1 ? "" : "s"}
          </span>
        </div>

        <LiveStrip scenario={active} />

        <div className="mt-5 grid grid-cols-1 gap-4 sm:grid-cols-2">
          {scenarios.map((s) => {
            const isActive = s.id === activeId;
            const kind = statusFor(isActive, m);
            const attack = kind === "attack";
            return (
              <button
                key={s.id}
                onClick={() => onOpenCase(s.id)}
                className={cx(
                  "group relative overflow-hidden rounded-card border bg-panel p-4 text-left transition-colors",
                  attack ? "border-threat/50" : "border-line hover:border-seal/40"
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
                      {s.agent.name.slice(0, 2).toUpperCase()}
                    </div>
                    <div>
                      <div className="font-sans text-[0.98rem] font-medium text-fg">{s.agent.name}</div>
                      <div className="font-mono text-[0.68rem] text-muted">{s.agent.tools.join(" · ")}</div>
                    </div>
                  </div>
                  <StatusBadge kind={kind} pulse={attack} />
                </div>
                <p className="mt-3 text-[0.86rem] leading-relaxed text-muted">{s.agent.purpose}</p>
                <div className="mt-3 flex items-center justify-between border-t border-line pt-2 font-mono text-[0.68rem] text-muted">
                  <span>
                    <span className="uppercase tracking-wide text-muted/80">{s.attackType}</span> · case {s.case.id}
                  </span>
                  <span className="text-seal opacity-0 transition-opacity group-hover:opacity-100">open →</span>
                </div>
              </button>
            );
          })}
        </div>

        <p className="mt-5 font-mono text-[0.68rem] text-muted/60">
          Each card is a real end-to-end case run through the live WARDEN pipeline. Click one to open its chain of
          custody.
        </p>
      </div>
    </div>
  );
}
