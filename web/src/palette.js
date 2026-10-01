// Validated palette (dataviz reference instance); both modes passed the
// six-check validator against their surfaces. Charts read concrete hex
// through usePalette() because SVG presentation attributes cannot
// resolve CSS custom properties.

import { useEffect, useState } from "react";

const LIGHT = {
  surface: "#fcfcfb",
  ink: "#0b0b0b",
  inkSecondary: "#52514e",
  muted: "#898781",
  grid: "#e1e0d9",
  axis: "#c3c2b7",
  series: ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#4a3aa7", "#e34948"],
  good: "#0ca30c",
  critical: "#d03b3b",
};

const DARK = {
  surface: "#1a1a19",
  ink: "#ffffff",
  inkSecondary: "#c3c2b7",
  muted: "#898781",
  grid: "#2c2c2a",
  axis: "#383835",
  series: ["#3987e5", "#d95926", "#199e70", "#c98500", "#d55181", "#008300", "#9085e9", "#e66767"],
  good: "#0ca30c",
  critical: "#d03b3b",
};

export function usePalette() {
  const query = window.matchMedia("(prefers-color-scheme: dark)");
  const [dark, setDark] = useState(query.matches);
  useEffect(() => {
    const onChange = (event) => setDark(event.matches);
    query.addEventListener("change", onChange);
    return () => query.removeEventListener("change", onChange);
  }, []);
  return dark ? DARK : LIGHT;
}

// Signature index -> color. Beyond eight signatures a cycled hue would
// be unreadable; fall back to an ordered single-hue ramp.
const ORDINAL_BLUES = ["#86b6ef", "#6da7ec", "#5598e7", "#3987e5", "#2a78d6", "#256abf", "#1c5cab", "#184f95", "#104281", "#0d366b"];

export function seriesColor(palette, index, total) {
  if (total <= palette.series.length) return palette.series[index];
  return ORDINAL_BLUES[Math.min(index, ORDINAL_BLUES.length - 1)];
}
