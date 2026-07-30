import { cx } from "../lib/cx";

export type Screen = "case" | "fleet" | "reports";

const ITEMS: { id: Screen; label: string; icon: JSX.Element }[] = [
  {
    id: "fleet",
    label: "Fleet",
    icon: (
      <path d="M4 7h16M4 12h16M4 17h10" strokeWidth="1.6" strokeLinecap="round" />
    ),
  },
  {
    id: "case",
    label: "Cases",
    icon: (
      <>
        <rect x="4" y="4" width="16" height="16" rx="2" strokeWidth="1.6" />
        <path d="M8 9h8M8 13h5" strokeWidth="1.6" strokeLinecap="round" />
      </>
    ),
  },
  {
    id: "reports",
    label: "Reports",
    icon: (
      <>
        <path d="M5 19V9M12 19V5M19 19v-7" strokeWidth="1.8" strokeLinecap="round" />
      </>
    ),
  },
];

export function LeftNav({ screen, onSelect }: { screen: Screen; onSelect: (s: Screen) => void }) {
  return (
    <nav className="flex w-[68px] shrink-0 flex-col items-stretch gap-1 border-r border-line bg-panel/40 py-3 lg:w-[168px]">
      {ITEMS.map((it) => {
        const active = screen === it.id;
        return (
          <button
            key={it.id}
            onClick={() => onSelect(it.id)}
            className={cx(
              "group relative mx-2 flex items-center gap-3 rounded-[6px] px-3 py-2.5 text-left transition-colors",
              active ? "bg-panel-2 text-fg" : "text-muted hover:bg-panel/60 hover:text-fg"
            )}
          >
            {/* current section marked with a --seal tick */}
            {active && <span className="absolute left-0 top-1/2 h-5 w-[3px] -translate-y-1/2 rounded-r bg-seal" />}
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" aria-hidden>
              {it.icon}
            </svg>
            <span className="hidden font-sans text-[0.9rem] lg:inline">{it.label}</span>
          </button>
        );
      })}
      <div className="mt-auto mx-3 hidden border-t border-line pt-3 lg:block">
        <p className="font-mono text-[0.68rem] leading-relaxed text-muted/70">
          provable cause
          <br />
          unforgeable fix
        </p>
      </div>
    </nav>
  );
}
