// Chart components (Recharts). Forms: 96-context signature bars colored
// by substitution class, stacked exposures per sample, single-series
// convergence trace. Palette is the validated reference instance; the
// light-mode contrast WARN slots get relief via the printed class
// legend, per-mark tooltips, and the CSV table downloads.

import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import { SUBSTITUTIONS, substitutionOf } from "./csv.js";
import { seriesColor, usePalette } from "./palette.js";

const tooltipStyle = (palette) => ({
  backgroundColor: palette.surface,
  border: `1px solid ${palette.grid}`,
  borderRadius: 6,
  fontSize: 12.5,
  color: palette.ink,
});

export function ClassLegend() {
  const palette = usePalette();
  return (
    <div className="class-legend">
      {SUBSTITUTIONS.map((substitution, index) => (
        <span key={substitution}>
          <span className="swatch" style={{ background: palette.series[index] }} />
          {substitution}
        </span>
      ))}
    </div>
  );
}

export function SignatureChart({ profile, mutationTypes, title }) {
  const palette = usePalette();
  const data = profile.map((value, i) => ({
    context: mutationTypes?.[i] ?? `type ${i + 1}`,
    value,
  }));
  return (
    <div className="chart-card">
      <h3>{title}</h3>
      <ResponsiveContainer width="100%" height={140} minWidth={560}>
        <BarChart data={data} margin={{ top: 4, right: 4, bottom: 0, left: 4 }} barCategoryGap={1}>
          <XAxis dataKey="context" tick={false} axisLine={{ stroke: palette.axis }} height={6} />
          <YAxis
            width={44}
            tick={{ fill: palette.muted, fontSize: 11 }}
            axisLine={false}
            tickLine={false}
            tickFormatter={(value) => (value === 0 ? "0" : Number(value).toPrecision(2))}
          />
          <Tooltip
            cursor={{ fill: "transparent" }}
            contentStyle={tooltipStyle(palette)}
            formatter={(value) => [value.toFixed(4), "proportion"]}
          />
          <Bar dataKey="value" isAnimationActive={false} radius={[2, 2, 0, 0]}>
            {data.map((entry) => (
              <Cell
                key={entry.context}
                fill={palette.series[SUBSTITUTIONS.indexOf(substitutionOf(entry.context))]}
              />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}

export function ExposuresChart({ exposures, sampleNames }) {
  const palette = usePalette();
  const rank = exposures.length;
  const nSamples = exposures[0]?.length ?? 0;
  const data = Array.from({ length: nSamples }, (_, j) => {
    const row = { sample: sampleNames?.[j] ?? `sample_${j + 1}` };
    exposures.forEach((signatureRow, k) => {
      row[`signature_${k + 1}`] = signatureRow[j];
    });
    return row;
  });
  const showTicks = nSamples <= 40;
  return (
    <div className="chart-card">
      <h3>Exposures per sample</h3>
      <div className="class-legend">
        {exposures.map((_, k) => (
          <span key={k}>
            <span
              className="swatch"
              style={{ background: seriesColor(palette, k, rank) }}
            />
            signature {k + 1}
          </span>
        ))}
      </div>
      <ResponsiveContainer width="100%" height={240} minWidth={Math.max(560, nSamples * 14)}>
        <BarChart data={data} margin={{ top: 4, right: 4, bottom: 0, left: 4 }}>
          <CartesianGrid vertical={false} stroke={palette.grid} />
          <XAxis
            dataKey="sample"
            tick={showTicks ? { fill: palette.muted, fontSize: 10, angle: -45, textAnchor: "end" } : false}
            height={showTicks ? 70 : 6}
            interval={0}
            axisLine={{ stroke: palette.axis }}
            tickLine={false}
          />
          <YAxis
            width={56}
            tick={{ fill: palette.muted, fontSize: 11 }}
            axisLine={false}
            tickLine={false}
          />
          <Tooltip
            cursor={{ fill: "transparent" }}
            contentStyle={tooltipStyle(palette)}
            formatter={(value, key) => [Math.round(value).toLocaleString(), key.replace("_", " ")]}
          />
          {exposures.map((_, k) => (
            <Bar
              key={k}
              dataKey={`signature_${k + 1}`}
              stackId="exposures"
              fill={seriesColor(palette, k, rank)}
              isAnimationActive={false}
              // 1px surface gap between stacked segments
              stroke={palette.surface}
              strokeWidth={1}
            />
          ))}
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}

export function TraceChart({ trace, metric }) {
  const palette = usePalette();
  const data = (trace.iter ?? [])
    .map((iter, i) => ({ iter, value: trace[metric]?.[i] }))
    .filter((point) => point.value != null);
  if (data.length === 0) {
    return <p className="subtitle">No {metric} trace recorded for this run.</p>;
  }
  return (
    <ResponsiveContainer width="100%" height={220} minWidth={420}>
      <LineChart data={data} margin={{ top: 8, right: 12, bottom: 4, left: 4 }}>
        <CartesianGrid vertical={false} stroke={palette.grid} />
        <XAxis
          dataKey="iter"
          tick={{ fill: palette.muted, fontSize: 11 }}
          axisLine={{ stroke: palette.axis }}
          tickLine={false}
          label={{ value: "iteration", position: "insideBottomRight", offset: -2, fill: palette.muted, fontSize: 11 }}
        />
        <YAxis
          width={76}
          tick={{ fill: palette.muted, fontSize: 11 }}
          axisLine={false}
          tickLine={false}
          domain={["auto", "auto"]}
          tickFormatter={(value) => Number(value).toPrecision(4)}
        />
        <Tooltip
          contentStyle={tooltipStyle(palette)}
          formatter={(value) => [Number(value).toPrecision(6), metric]}
          labelFormatter={(iter) => `iteration ${iter}`}
        />
        <Line
          type="monotone"
          dataKey="value"
          stroke={palette.series[0]}
          strokeWidth={2}
          dot={false}
          isAnimationActive={false}
        />
      </LineChart>
    </ResponsiveContainer>
  );
}
