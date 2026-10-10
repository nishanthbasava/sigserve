// Chart palette. Substitution classes use the standard COSMIC SBS colors
// so signature plots read the same here as in the literature; those six
// colors are also the signature series for the exposures chart. Charts
// read concrete hex through usePalette() because SVG presentation
// attributes cannot resolve CSS custom properties.

import { useEffect, useState } from "react";

// Standard COSMIC class colors, in canonical order C>A C>G C>T T>A T>C T>G.
// `ink` is a text color that meets WCAG AA on the class swatch.
const CLASSES = [
  { name: "C>A", fill: "#03bcee", ink: "#0b0b0b" },
  { name: "C>G", fill: "#010101", ink: "#ffffff" },
  { name: "C>T", fill: "#e32926", ink: "#ffffff" },
  { name: "T>A", fill: "#cac9c9", ink: "#0b0b0b" },
  { name: "T>C", fill: "#a1ce63", ink: "#0b0b0b" },
  { name: "T>G", fill: "#ebc6c4", ink: "#0b0b0b" },
];

// On dark surfaces #010101 vanishes: lift C>G to a near-black and give its
// marks a light outline so the bars stay visible without changing the hue.
const CLASSES_DARK = CLASSES.map((entry) =>
  entry.name === "C>G"
    ? { ...entry, fill: "#3d3d3d", stroke: "rgba(255, 255, 255, 0.55)" }
    : entry
);

const LIGHT = {
  surface: "#fcfcfb",
  ink: "#0b0b0b",
  inkSecondary: "#52514e",
  muted: "#898781",
  grid: "#e1e0d9",
  axis: "#c3c2b7",
  accent: "#0277a8",
  classes: CLASSES,
  series: CLASSES.map((entry) => entry.fill),
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
  accent: "#03bcee",
  classes: CLASSES_DARK,
  series: CLASSES_DARK.map((entry) => entry.fill),
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

// Signature index -> color. Up to six signatures reuse the class colors;
// beyond that a cycled hue would be unreadable, so fall back to an
// ordered single-hue ramp.
const ORDINAL_BLUES = ["#86b6ef", "#6da7ec", "#5598e7", "#3987e5", "#2a78d6", "#256abf", "#1c5cab", "#184f95", "#104281", "#0d366b"];

export function seriesColor(palette, index, total) {
  if (total <= palette.series.length) return palette.series[index];
  return ORDINAL_BLUES[Math.min(index, ORDINAL_BLUES.length - 1)];
}
