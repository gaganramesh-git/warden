import { motion, useReducedMotion } from "framer-motion";

// The refusal: full-width --threat, cracked-seal icon, plain reason line. The
// frame a judge screenshots (UI/UX §6, §9).
export function RefusalBanner({ reason, stateUnchanged }: { reason: string; stateUnchanged: boolean }) {
  const reduce = useReducedMotion();
  return (
    <motion.div
      initial={reduce ? { opacity: 0 } : { y: -18, opacity: 0 }}
      animate={{ y: 0, opacity: 1 }}
      transition={{ type: "spring", stiffness: 420, damping: 30 }}
      role="alert"
      className="overflow-hidden rounded-card border border-threat/60 bg-threat/12"
    >
      <div className="flex items-center gap-3 border-b border-threat/25 bg-threat/15 px-4 py-3">
        <svg width="22" height="22" viewBox="0 0 24 24" className="shrink-0 text-threat" aria-hidden>
          <circle cx="12" cy="12" r="9" fill="none" stroke="currentColor" strokeWidth="1.6" />
          <path d="M12 4v10M9 6l6 6" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" />
        </svg>
        <span className="font-display text-[1.15rem] font-bold tracking-tight text-threat">
          ACTUATION REFUSED
        </span>
      </div>
      <div className="px-4 py-3">
        <p className="font-mono text-record text-fg">
          <span className="text-threat">reason:</span> {reason}.
        </p>
        <p className="mt-1 font-mono text-micro text-muted">
          Rehearse the fix, then try again. The actuator can <em>check</em> signatures — it cannot forge them.
        </p>
        {stateUnchanged && (
          <p className="mt-2 inline-flex items-center gap-1.5 rounded-full border border-verified/40 bg-verified/10 px-2.5 py-1 font-mono text-micro text-verified">
            <span className="h-1.5 w-1.5 rounded-full bg-verified" />
            production policy unchanged — nothing was deployed
          </p>
        )}
      </div>
    </motion.div>
  );
}
