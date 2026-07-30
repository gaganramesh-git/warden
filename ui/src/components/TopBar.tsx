import { StatusBadge, type StatusKind } from "./ui/StatusBadge";

export function TopBar({ status, alerts }: { status: StatusKind; alerts: number }) {
  return (
    <header className="flex h-14 shrink-0 items-center justify-between border-b border-line bg-panel/70 px-5 backdrop-blur">
      <div className="flex items-center gap-3">
        <div className="grid h-7 w-7 place-items-center rounded-[6px] bg-seal/15 ring-1 ring-seal/40">
          {/* the WARDEN mark — a shield seal */}
          <svg width="16" height="16" viewBox="0 0 24 24" className="text-seal" aria-hidden>
            <path
              d="M12 2l8 3v6c0 5-3.4 8.4-8 11-4.6-2.6-8-6-8-11V5l8-3z"
              fill="currentColor"
              opacity="0.22"
            />
            <path
              d="M12 2l8 3v6c0 5-3.4 8.4-8 11-4.6-2.6-8-6-8-11V5l8-3z"
              fill="none"
              stroke="currentColor"
              strokeWidth="1.5"
            />
            <path d="M8.5 12l2.4 2.4L15.5 9" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" />
          </svg>
        </div>
        <div className="flex items-baseline gap-2">
          <span className="font-display text-[1.05rem] font-bold tracking-tight">WARDEN</span>
          <span className="hidden font-mono text-micro text-muted sm:inline">
            antivirus for autonomous AI agents
          </span>
        </div>
        <span className="ml-2 rounded-full border border-line px-2 py-0.5 font-mono text-micro text-muted">
          env: local
        </span>
      </div>

      <div className="flex items-center gap-4">
        <span className="flex items-center gap-1.5 font-mono text-micro text-verified">
          <span className="relative h-1.5 w-1.5 rounded-full bg-verified">
            <span className="absolute inset-0 animate-ping rounded-full bg-verified opacity-70" />
          </span>
          live
        </span>
        <StatusBadge kind={status} pulse={status === "attack"} />
        {alerts > 0 && (
          <span className="rounded-full bg-threat/15 px-2 py-0.5 font-mono text-micro font-medium text-threat">
            alerts ({alerts})
          </span>
        )}
        <div className="flex items-center gap-2 border-l border-line pl-4">
          <div className="grid h-7 w-7 place-items-center rounded-full bg-panel-2 font-mono text-micro text-muted ring-1 ring-line">
            SL
          </div>
          <span className="hidden font-mono text-micro text-muted md:inline">sec-lead@org</span>
        </div>
      </div>
    </header>
  );
}
