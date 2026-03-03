/** Sparkline strip — value + mini chart. */

interface SparkStripProps {
  label: string;
  value: number;
  history: number[];
  unit: string;
  min: number;
  max: number;
  warnHigh?: number;
  warnLow?: number;
  decimals?: number;
}

export default function SparkStrip({
  label,
  value,
  history,
  unit,
  min,
  max,
  warnHigh,
  warnLow,
  decimals = 1,
}: SparkStripProps) {
  const isWarning =
    (warnHigh !== undefined && value >= warnHigh) ||
    (warnLow !== undefined && value <= warnLow);

  // Build SVG sparkline path
  const width = 120;
  const height = 30;
  const range = max - min || 1;
  const points = history.map((v, i) => {
    const x = (i / Math.max(history.length - 1, 1)) * width;
    const y = height - ((v - min) / range) * height;
    return `${x},${Math.max(0, Math.min(height, y))}`;
  });
  const linePath = points.length > 1 ? `M ${points.join(" L ")}` : "";
  const fillPath =
    points.length > 1
      ? `${linePath} L ${width},${height} L 0,${height} Z`
      : "";

  const color = isWarning ? "var(--color-red)" : "var(--color-accent)";

  return (
    <div className="flex items-center gap-3 rounded-lg bg-neutral-900 px-3 py-2">
      <div className="w-20">
        <div className="text-xs text-neutral-400">{label}</div>
        <div className="font-mono text-sm font-bold" style={{ color }}>
          {value.toFixed(decimals)}
          <span className="ml-1 text-xs font-normal text-neutral-500">
            {unit}
          </span>
        </div>
      </div>
      <svg width={width} height={height} className="shrink-0">
        {fillPath && (
          <path d={fillPath} fill={color} opacity={0.15} />
        )}
        {linePath && (
          <path d={linePath} fill="none" stroke={color} strokeWidth={1.5} />
        )}
      </svg>
    </div>
  );
}
