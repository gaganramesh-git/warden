import { AnimatePresence, motion, useReducedMotion } from "framer-motion";
import { cx } from "../lib/cx";

export type SealState = "empty" | "sealed" | "cracked";

interface Props {
  state: SealState;
  glyph?: string; // short mark inside the seal
  size?: number;
}

// The seal is sacred: cryptographic signing gets its own colour (--seal) and
// its own motion. Empty = hollow ring. Sealed = it stamps in. Cracked = the
// gap is loud, in --threat (UI/UX §5, §7).
export function Seal({ state, glyph = "✓", size = 46 }: Props) {
  const reduce = useReducedMotion();
  const r = size / 2;

  return (
    <div className="relative" style={{ width: size, height: size }}>
      {/* hollow ring — always present as the socket */}
      <svg width={size} height={size} className="absolute inset-0">
        <circle
          cx={r}
          cy={r}
          r={r - 3}
          fill="none"
          strokeWidth={state === "empty" ? 1.5 : 2}
          strokeDasharray={state === "empty" ? "3 3" : undefined}
          className={cx(
            state === "empty" && "stroke-line",
            state === "sealed" && "stroke-seal",
            state === "cracked" && "stroke-threat"
          )}
        />
      </svg>

      <AnimatePresence>
        {state === "sealed" && (
          <motion.div
            key="sealed"
            initial={reduce ? { opacity: 1 } : { scale: 1.15, opacity: 0.2 }}
            animate={{ scale: 1, opacity: 1 }}
            transition={{ duration: 0.42, ease: [0.2, 0.9, 0.2, 1] }}
            className="absolute inset-0 grid place-items-center"
          >
            {/* ripple */}
            {!reduce && (
              <motion.span
                initial={{ scale: 0.8, opacity: 0.55 }}
                animate={{ scale: 1.9, opacity: 0 }}
                transition={{ duration: 0.7, ease: "easeOut" }}
                className="absolute rounded-full border border-seal"
                style={{ width: size - 8, height: size - 8 }}
              />
            )}
            <div
              className="grid place-items-center rounded-full text-white shadow-seal"
              style={{
                width: size - 8,
                height: size - 8,
                background: "radial-gradient(120% 120% at 30% 25%, #9384ff 0%, #7c6bf5 45%, #5b4bd6 100%)",
              }}
            >
              <span className="font-display text-[0.95rem] font-bold">{glyph}</span>
            </div>
          </motion.div>
        )}

        {state === "cracked" && (
          <motion.div
            key="cracked"
            initial={reduce ? {} : { scale: 1.05 }}
            animate={{ scale: 1 }}
            className="absolute inset-0 grid place-items-center"
          >
            <div
              className="relative grid place-items-center rounded-full"
              style={{
                width: size - 8,
                height: size - 8,
                background: "radial-gradient(120% 120% at 30% 25%, #3a2530 0%, #2a1a22 100%)",
                border: "2px solid rgba(229,72,77,0.7)",
              }}
            >
              {/* the crack */}
              <svg width={size - 8} height={size - 8} className="absolute inset-0">
                <polyline
                  points={`${(size - 8) * 0.5},2 ${(size - 8) * 0.42},${(size - 8) * 0.4} ${(size - 8) * 0.6},${
                    (size - 8) * 0.55
                  } ${(size - 8) * 0.48},${size - 10}`}
                  fill="none"
                  stroke="#E5484D"
                  strokeWidth={2}
                />
              </svg>
              <span className="font-display text-[0.95rem] font-bold text-threat">⛒</span>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
