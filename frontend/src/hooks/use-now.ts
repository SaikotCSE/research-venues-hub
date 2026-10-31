import { useSyncExternalStore } from "react";

// One shared clock for every countdown on the page instead of an interval per component.
let now = Date.now();
const listeners = new Set<() => void>();
let timer: number | undefined;

function subscribe(listener: () => void) {
  listeners.add(listener);
  if (timer === undefined) {
    timer = window.setInterval(() => {
      now = Date.now();
      listeners.forEach((l) => l());
    }, 1000);
  }
  return () => {
    listeners.delete(listener);
    if (listeners.size === 0 && timer !== undefined) {
      window.clearInterval(timer);
      timer = undefined;
    }
  };
}

const getSnapshot = () => now;

/** Current time in ms, re-rendering every second while mounted. Prefer `useClock` with a coarse selector. */
export function useNow() {
  return useSyncExternalStore(subscribe, getSnapshot, getSnapshot);
}

/**
 * Derive a primitive from the shared clock; the component re-renders only when that value changes
 * (e.g. a countdown string that only changes once a minute).
 */
export function useClock<T extends string | number | boolean>(select: (now: number) => T): T {
  return useSyncExternalStore(
    subscribe,
    () => select(now),
    () => select(now),
  );
}

/** Wall-clock minute (ms), for values such as progress bars that don't need per-second updates. */
export function useMinute() {
  return useClock((n) => Math.floor(n / 60_000) * 60_000);
}
