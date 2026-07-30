import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { BEATS, type Beat } from "../types";

// Per-beat dwell time when auto-playing (ms). Auto-play is OPT-IN and paced for
// narration, not a blur — manual stepping (the StepGuide button) is the default.
const DWELL: Record<Beat, number> = {
  disaster: 6500,
  catch: 5500,
  evidence: 6000,
  proof: 7500,
  fix: 5500,
  rehearsal: 5000,
  approval: 5000,
  deployed: 6000,
  refusal: 9000,
};

export interface Machine {
  idx: number;
  beat: Beat;
  playing: boolean;
  atStart: boolean;
  atEnd: boolean;
  next: () => void;
  prev: () => void;
  goto: (b: Beat) => void;
  gotoRefusal: () => void;
  restart: () => void;
  togglePlay: () => void;
  reached: (b: Beat) => boolean;
  // derived seal / deploy state
  isRefusal: boolean;
  sealA: "empty" | "sealed" | "cracked";
  sealB: "empty" | "sealed";
  deployState: "locked" | "ready" | "deployed" | "refused";
}

export function useDemoMachine(): Machine {
  const [idx, setIdx] = useState(0);
  const [playing, setPlaying] = useState(false);
  const timer = useRef<number | null>(null);

  const beat = BEATS[idx].id;
  const atStart = idx === 0;
  const atEnd = idx === BEATS.length - 1;

  const clear = () => {
    if (timer.current) {
      window.clearTimeout(timer.current);
      timer.current = null;
    }
  };

  useEffect(() => {
    if (!playing) {
      clear();
      return;
    }
    if (atEnd) {
      setPlaying(false);
      return;
    }
    timer.current = window.setTimeout(() => setIdx((i) => Math.min(i + 1, BEATS.length - 1)), DWELL[beat]);
    return clear;
  }, [playing, idx, beat, atEnd]);

  const next = useCallback(() => setIdx((i) => Math.min(i + 1, BEATS.length - 1)), []);
  const prev = useCallback(() => setIdx((i) => Math.max(i - 1, 0)), []);
  const goto = useCallback((b: Beat) => setIdx(BEATS.findIndex((x) => x.id === b)), []);
  const gotoRefusal = useCallback(() => {
    setPlaying(false);
    setIdx(BEATS.findIndex((x) => x.id === "refusal"));
  }, []);
  const restart = useCallback(() => {
    setPlaying(false);
    setIdx(0);
  }, []);
  const togglePlay = useCallback(() => {
    setPlaying((p) => {
      const np = !p;
      if (np && idx === BEATS.length - 1) setIdx(0);
      return np;
    });
  }, [idx]);

  const reached = useCallback((b: Beat) => idx >= BEATS.findIndex((x) => x.id === b), [idx]);

  const derived = useMemo(() => {
    const isRefusal = beat === "refusal";
    const rehearsed = idx >= BEATS.findIndex((x) => x.id === "rehearsal");
    const approved = idx >= BEATS.findIndex((x) => x.id === "approval");
    const deployed = idx >= BEATS.findIndex((x) => x.id === "deployed");

    const sealA: "empty" | "sealed" | "cracked" = isRefusal ? "cracked" : rehearsed ? "sealed" : "empty";
    const sealB: "empty" | "sealed" = approved && !isRefusal ? "sealed" : isRefusal ? "sealed" : "empty";

    let deployState: "locked" | "ready" | "deployed" | "refused";
    if (isRefusal) deployState = "refused";
    else if (deployed) deployState = "deployed";
    else if (rehearsed && approved) deployState = "ready";
    else deployState = "locked";

    return { isRefusal, sealA, sealB, deployState };
  }, [beat, idx]);

  return {
    idx,
    beat,
    playing,
    atStart,
    atEnd,
    next,
    prev,
    goto,
    gotoRefusal,
    restart,
    togglePlay,
    reached,
    ...derived,
  };
}
