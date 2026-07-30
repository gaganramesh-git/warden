import { BEATS } from "../types";
import type { Machine } from "../lib/useDemoMachine";
import { cx } from "../lib/cx";

// The transport: scene chips + play/prev/next/restart. Drives the whole demo
// hands-free, or step-by-step for a live narrator.
export function DemoControls({ m }: { m: Machine }) {
  return (
    <div className="flex items-center gap-3 border-b border-line bg-panel/50 px-4 py-2">
      <div className="flex items-center gap-1">
        <IconBtn label="Restart" onClick={m.restart}>
          <path d="M4 12a8 8 0 1 0 2.3-5.6M4 4v3h3" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" />
        </IconBtn>
        <IconBtn label="Previous" onClick={m.prev} disabled={m.atStart}>
          <path d="M15 6l-6 6 6 6" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" />
        </IconBtn>
        <button
          onClick={m.togglePlay}
          className="grid h-8 w-8 place-items-center rounded-full bg-seal text-white transition-colors hover:bg-seal/90"
          aria-label={m.playing ? "Pause" : "Play"}
        >
          {m.playing ? (
            <svg width="15" height="15" viewBox="0 0 24 24" fill="currentColor">
              <rect x="6" y="5" width="4" height="14" rx="1" />
              <rect x="14" y="5" width="4" height="14" rx="1" />
            </svg>
          ) : (
            <svg width="15" height="15" viewBox="0 0 24 24" fill="currentColor">
              <path d="M7 5l12 7-12 7V5z" />
            </svg>
          )}
        </button>
        <IconBtn label="Next" onClick={m.next} disabled={m.atEnd}>
          <path d="M9 6l6 6-6 6" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" />
        </IconBtn>
      </div>

      <div className="mx-1 h-5 w-px bg-line" />

      {/* scene chips */}
      <div className="flex min-w-0 flex-1 items-center gap-1 overflow-x-auto">
        {BEATS.map((b, i) => {
          const active = m.idx === i;
          const done = m.idx > i;
          return (
            <button
              key={b.id}
              onClick={() => m.goto(b.id)}
              className={cx(
                "shrink-0 rounded-full border px-2.5 py-1 font-mono text-[0.7rem] transition-colors",
                active && b.id === "refusal" && "border-threat/60 bg-threat/15 text-threat",
                active && b.id !== "refusal" && "border-seal/60 bg-seal/15 text-seal",
                !active && done && "border-line bg-panel-2 text-muted",
                !active && !done && "border-line/60 text-muted/60 hover:text-muted"
              )}
            >
              <span className="mr-1 opacity-60">{b.t}</span>
              {b.label}
            </button>
          );
        })}
      </div>
    </div>
  );
}

function IconBtn({
  children,
  onClick,
  label,
  disabled,
}: {
  children: React.ReactNode;
  onClick: () => void;
  label: string;
  disabled?: boolean;
}) {
  return (
    <button
      onClick={onClick}
      disabled={disabled}
      aria-label={label}
      className="grid h-8 w-8 place-items-center rounded-full text-muted transition-colors hover:bg-panel-2 hover:text-fg disabled:opacity-30"
    >
      <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor">
        {children}
      </svg>
    </button>
  );
}
