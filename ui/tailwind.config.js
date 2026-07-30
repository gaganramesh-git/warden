/** @type {import('tailwindcss').Config} */
// WARDEN colour system (UI/UX Design §2). Colour means status, nothing else.
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        ink: "#0E1621", // app background — deep slate, not pure black
        panel: "#17212E", // cards, rails, chrome
        "panel-2": "#1B2735",
        line: "#26333F", // hairline dividers
        fg: "#DCE3EC", // primary text on dark
        muted: "#7C8A9A", // secondary text, labels
        paper: "#ECE7DB", // EVIDENCE surfaces — parchment
        "paper-2": "#E4DECF",
        "paper-ink": "#1C2530", // text on parchment
        threat: "#E5484D", // misbehavior / attack / refusal
        verified: "#3DBB8E", // confirmed / cleared / resolved
        pending: "#E0A83E", // awaiting rehearsal / approval
        seal: "#7C6BF5", // cryptographic seals & signatures ONLY
      },
      fontFamily: {
        display: ['"Space Grotesk"', "ui-sans-serif", "system-ui", "sans-serif"],
        sans: ['"IBM Plex Sans"', "ui-sans-serif", "system-ui", "sans-serif"],
        mono: ['"IBM Plex Mono"', "ui-monospace", "SFMono-Regular", "Menlo", "monospace"],
      },
      fontSize: {
        // scale (rem): 0.75 · 0.875 · 1 · 1.25 · 1.75 · 2.5 · 3.5
        micro: ["0.75rem", { lineHeight: "1rem" }],
        record: ["0.875rem", { lineHeight: "1.55rem" }],
        h4: ["1.25rem", { lineHeight: "1.6rem" }],
        h3: ["1.75rem", { lineHeight: "2rem" }],
        h2: ["2.5rem", { lineHeight: "2.6rem" }],
        h1: ["3.5rem", { lineHeight: "3.6rem" }],
      },
      borderRadius: {
        card: "5px",
        paper: "6px",
      },
      boxShadow: {
        seal: "0 0 0 1px rgba(124,107,245,0.4), 0 6px 22px rgba(124,107,245,0.28)",
        paper: "0 1px 0 rgba(0,0,0,0.25), 0 10px 30px rgba(0,0,0,0.35)",
        panel: "0 8px 30px rgba(0,0,0,0.35)",
      },
      keyframes: {
        stamp: {
          "0%": { transform: "scale(1.15)", opacity: "0.2" },
          "60%": { transform: "scale(0.97)" },
          "100%": { transform: "scale(1)", opacity: "1" },
        },
        ripple: {
          "0%": { transform: "scale(0.8)", opacity: "0.55" },
          "100%": { transform: "scale(1.9)", opacity: "0" },
        },
        shake: {
          "10%,90%": { transform: "translateX(-1px)" },
          "20%,80%": { transform: "translateX(2px)" },
          "30%,50%,70%": { transform: "translateX(-4px)" },
          "40%,60%": { transform: "translateX(4px)" },
        },
        threatpulse: {
          "0%,100%": { boxShadow: "0 0 0 0 rgba(229,72,77,0)" },
          "50%": { boxShadow: "0 0 0 4px rgba(229,72,77,0.35)" },
        },
        tick: {
          from: { opacity: "0", transform: "translateY(3px)" },
          to: { opacity: "1", transform: "translateY(0)" },
        },
      },
      animation: {
        stamp: "stamp 420ms cubic-bezier(0.2,0.9,0.2,1) both",
        ripple: "ripple 700ms ease-out both",
        shake: "shake 420ms cubic-bezier(.36,.07,.19,.97) both",
        threatpulse: "threatpulse 520ms ease-in-out 2",
        tick: "tick 240ms ease-out both",
      },
    },
  },
  plugins: [],
};
