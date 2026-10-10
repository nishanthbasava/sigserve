// 96-channel SBS signature plot, plain SVG. Bars in canonical COSMIC
// order, grouped into the six substitution classes with a colored header
// strip per class; class names are printed on the strips so color is
// never the only signal. Per-bar <title> tooltips carry the exact
// context and proportion.

import { CONTEXTS_96, substitutionOf, SUBSTITUTIONS } from "./csv.js";
import { usePalette } from "./palette.js";

const BAR = 8;
const STEP = 10;
const GROUP_GAP = 10;
const LEFT = 46;
const RIGHT = 6;
const STRIP_H = 15;
const STRIP_GAP = 5;

// labelScale > 1 is the compact mode: the SVG shrinks to its container
// (no min-width), so text is drawn larger in viewBox units to stay
// readable at the smaller rendered size.
export default function SbsPlot({
  profile,
  contexts,
  title,
  meta,
  plotHeight = 104,
  showContextLabels = true,
  labelScale = 1,
}) {
  const palette = usePalette();
  const labels = contexts && contexts.length === profile.length ? contexts : CONTEXTS_96;
  const max = Math.max(...profile, 1e-9);
  const stripH = STRIP_H * labelScale;
  const left = LEFT * labelScale;
  const labelArea = showContextLabels ? 40 : 4 * labelScale;
  const top = stripH + STRIP_GAP;
  const width = left + 96 * STEP + 5 * GROUP_GAP + RIGHT;
  const height = top + plotHeight + labelArea;
  const xOf = (index) => left + index * STEP + Math.floor(index / 16) * GROUP_GAP;
  const baseline = top + plotHeight;

  return (
    <div className="chart-card">
      {(title || meta) && (
        <div className="chart-head">
          {title && <h3>{title}</h3>}
          {meta}
        </div>
      )}
      <svg
        viewBox={`0 0 ${width} ${height}`}
        width="100%"
        style={{ minWidth: labelScale > 1 ? 0 : 640, display: "block" }}
        role="img"
        aria-label={`${title || "Signature"}: 96-channel SBS profile grouped by substitution class`}
      >
        {SUBSTITUTIONS.map((name, classIndex) => {
          const spec = palette.classes[classIndex];
          const x = xOf(classIndex * 16);
          const stripWidth = 15 * STEP + BAR;
          return (
            <g key={name}>
              <rect
                x={x}
                y={0}
                width={stripWidth}
                height={stripH}
                fill={spec.fill}
                stroke={spec.stroke}
                strokeWidth={spec.stroke ? 1 : 0}
                rx={2}
              />
              <text
                x={x + stripWidth / 2}
                y={stripH / 2 + 3.5 * labelScale}
                textAnchor="middle"
                fontSize={10 * labelScale}
                fontWeight="600"
                fill={spec.ink}
              >
                {name}
              </text>
            </g>
          );
        })}

        {/* y axis: 0 and the profile maximum */}
        <line x1={left - 4} y1={top} x2={left - 4} y2={baseline} stroke={palette.axis} />
        <line x1={left - 4} y1={baseline} x2={width - RIGHT} y2={baseline} stroke={palette.axis} />
        <line
          x1={left - 4}
          y1={top}
          x2={width - RIGHT}
          y2={top}
          stroke={palette.grid}
          strokeDasharray="2 3"
        />
        <text x={left - 8} y={top + 4 * labelScale} textAnchor="end" fontSize={9 * labelScale} fill={palette.muted}>
          {max.toPrecision(2)}
        </text>
        <text x={left - 8} y={baseline + 3} textAnchor="end" fontSize={9 * labelScale} fill={palette.muted}>
          0
        </text>

        {profile.map((value, index) => {
          const spec =
            palette.classes[SUBSTITUTIONS.indexOf(substitutionOf(labels[index]))] ??
            palette.classes[Math.floor(index / 16)];
          const barHeight = (Math.max(0, value) / max) * plotHeight;
          const x = xOf(index);
          return (
            <rect
              key={labels[index]}
              x={x}
              y={baseline - barHeight}
              width={BAR}
              height={Math.max(barHeight, value > 0 ? 0.75 : 0)}
              fill={spec.fill}
              stroke={spec.stroke}
              strokeWidth={spec.stroke ? 0.75 : 0}
            >
              <title>{`${labels[index]} — ${value.toFixed(4)}`}</title>
            </rect>
          );
        })}

        {showContextLabels &&
          labels.map((context, index) => (
            <text
              key={context}
              transform={`rotate(-90 ${xOf(index) + BAR / 2} ${baseline + 6})`}
              x={xOf(index) + BAR / 2}
              y={baseline + 6}
              dy="2.5"
              textAnchor="end"
              fontSize="6.5"
              fill={palette.muted}
              fontFamily="ui-monospace, SFMono-Regular, Menlo, monospace"
            >
              {context}
            </text>
          ))}
      </svg>
    </div>
  );
}
