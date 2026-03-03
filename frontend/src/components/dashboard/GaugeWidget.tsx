/** Radial gauge widget — SVG semicircular gauge. */

import { useMemo } from "react";

interface GaugeWidgetProps {
  label: string;
  value: number;
  min: number;
  max: number;
  unit: string;
  warnHigh?: number;
  warnLow?: number;
  decimals?: number;
}

const SIZE = 160;
const CX = SIZE / 2;
const CY = SIZE / 2 + 10;
const RADIUS = 60;
const START_ANGLE = Math.PI;
const END_ANGLE = 0;

function polarToCartesian(angle: number) {
  return {
    x: CX + RADIUS * Math.cos(angle),
    y: CY - RADIUS * Math.sin(angle),
  };
}

function describeArc(startAngle: number, endAngle: number) {
  const start = polarToCartesian(startAngle);
  const end = polarToCartesian(endAngle);
  const largeArc = startAngle - endAngle > Math.PI ? 1 : 0;
  return `M ${start.x} ${start.y} A ${RADIUS} ${RADIUS} 0 ${largeArc} 0 ${end.x} ${end.y}`;
}

export default function GaugeWidget({
  label,
  value,
  min,
  max,
  unit,
  warnHigh,
  decimals = 0,
}: GaugeWidgetProps) {
  const fraction = Math.max(0, Math.min(1, (value - min) / (max - min)));
  const valueAngle = START_ANGLE - fraction * Math.PI;

  const isWarning = warnHigh !== undefined && value >= warnHigh;

  const bgArc = useMemo(() => describeArc(START_ANGLE, END_ANGLE), []);
  const valueArc = useMemo(
    () => describeArc(START_ANGLE, valueAngle),
    [valueAngle],
  );

  const color = isWarning ? "var(--color-red)" : "var(--color-accent)";

  return (
    <div className="flex flex-col items-center rounded-lg bg-neutral-900 p-2">
      <svg width={SIZE} height={SIZE / 2 + 30} viewBox={`0 0 ${SIZE} ${SIZE / 2 + 30}`}>
        {/* Background arc */}
        <path d={bgArc} fill="none" stroke="#333" strokeWidth={10} strokeLinecap="round" />
        {/* Value arc */}
        <path d={valueArc} fill="none" stroke={color} strokeWidth={10} strokeLinecap="round" />
        {/* Value text */}
        <text
          x={CX}
          y={CY - 10}
          textAnchor="middle"
          fill="white"
          fontSize="24"
          fontWeight="bold"
          fontFamily="monospace"
        >
          {value.toFixed(decimals)}
        </text>
        {/* Unit */}
        <text x={CX} y={CY + 10} textAnchor="middle" fill="#888" fontSize="12">
          {unit}
        </text>
        {/* Min / Max labels */}
        <text x={CX - RADIUS} y={CY + 20} textAnchor="middle" fill="#555" fontSize="10">
          {min}
        </text>
        <text x={CX + RADIUS} y={CY + 20} textAnchor="middle" fill="#555" fontSize="10">
          {max}
        </text>
      </svg>
      <span className="text-xs text-neutral-400">{label}</span>
    </div>
  );
}
