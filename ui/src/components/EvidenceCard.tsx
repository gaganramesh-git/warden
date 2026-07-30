import { cx } from "../lib/cx";

const SLICE_LABEL: Record<string, string> = {
  tool_io: "tool I/O",
  instructions: "instructions",
  retrieved: "retrieved content",
  reasoning: "reasoning",
  user: "customer message",
  untrusted: "untrusted content",
};

interface Props {
  slice: string;
  source?: string;
  trusted?: boolean;
  children: React.ReactNode;
  struck?: boolean; // for the counterfactual strike-through
  dim?: boolean;
  className?: string;
}

// Evidence is paper: the data the agent produced renders on warm parchment in a
// monospace "record" face — it reads as seized evidence (UI/UX §1).
export function EvidenceCard({ slice, source, trusted, children, struck, dim, className }: Props) {
  const untrusted = trusted === false;
  return (
    <figure
      className={cx(
        "paper-grain relative rounded-paper text-paper-ink shadow-paper transition-opacity duration-500",
        dim && "opacity-40",
        className
      )}
    >
      {/* untrusted evidence gets a threat hairline on its edge */}
      {untrusted && <span className="absolute inset-y-0 left-0 w-[3px] rounded-l-paper bg-threat" />}
      <figcaption className="flex items-center justify-between border-b border-paper-ink/10 px-3 py-1.5">
        <span className="font-mono text-[0.7rem] uppercase tracking-wider text-paper-ink/60">
          {SLICE_LABEL[slice] ?? slice}
        </span>
        <span className="flex items-center gap-2 font-mono text-[0.7rem] text-paper-ink/55">
          {source && <span>{source}</span>}
          {untrusted ? (
            <span className="rounded-sm bg-threat/15 px-1.5 py-0.5 font-medium text-threat">untrusted</span>
          ) : trusted === true ? (
            <span className="rounded-sm bg-paper-ink/10 px-1.5 py-0.5">trusted</span>
          ) : null}
        </span>
      </figcaption>
      <div className={cx("px-3 py-2.5 font-mono text-record leading-relaxed", struck && "strike-line struck")}>
        {children}
      </div>
    </figure>
  );
}
