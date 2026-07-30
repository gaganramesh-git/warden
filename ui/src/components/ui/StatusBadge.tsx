import { cx } from "../../lib/cx";

// Status is never conveyed by colour alone — every badge carries a label + a
// dot/icon (accessibility floor, UI/UX §10).
export type StatusKind = "healthy" | "watching" | "attack" | "awaiting" | "sealed" | "resolved";

const MAP: Record<StatusKind, { label: string; fg: string; dot: string; ring: string }> = {
  healthy: { label: "Healthy", fg: "text-verified", dot: "bg-verified", ring: "border-verified/40" },
  watching: { label: "Watching", fg: "text-muted", dot: "bg-muted", ring: "border-line" },
  attack: { label: "Under attack", fg: "text-threat", dot: "bg-threat", ring: "border-threat/50" },
  awaiting: { label: "Awaiting", fg: "text-pending", dot: "bg-pending", ring: "border-pending/45" },
  sealed: { label: "Sealed", fg: "text-seal", dot: "bg-seal", ring: "border-seal/50" },
  resolved: { label: "Resolved", fg: "text-verified", dot: "bg-verified", ring: "border-verified/40" },
};

export function StatusBadge({ kind, label, pulse }: { kind: StatusKind; label?: string; pulse?: boolean }) {
  const m = MAP[kind];
  return (
    <span
      className={cx(
        "inline-flex items-center gap-1.5 rounded-full border bg-ink/40 px-2.5 py-1 text-micro font-medium",
        m.fg,
        m.ring
      )}
    >
      <span className={cx("relative h-1.5 w-1.5 rounded-full", m.dot)}>
        {pulse && <span className={cx("absolute inset-0 rounded-full", m.dot, "animate-ping opacity-75")} />}
      </span>
      {label ?? m.label}
    </span>
  );
}
