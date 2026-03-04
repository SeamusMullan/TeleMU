/** Channel selector — checkbox list of available channels grouped by category. */

import { useMemo } from "react";
import { useTelemetryStore } from "../../stores/telemetryStore";
import { useAnalyzerStore, type ChartType } from "../../stores/analyzerStore";

const CATEGORIES: Record<string, string[]> = {
  "Motion": ["speed", "rpm", "throttle", "brake", "gear", "steering"],
  "Tyres": ["tyre_fl", "tyre_fr", "tyre_rl", "tyre_rr"],
  "Engine": ["fuel", "brake_temp", "oil_temp", "water_temp"],
};

const CHART_TYPES: { value: ChartType; label: string }[] = [
  { value: "line", label: "Line" },
  { value: "scatter", label: "Scatter" },
  { value: "histogram", label: "Histogram" },
];

export default function ChannelSelector() {
  const channelKeys = useTelemetryStore((s) => Object.keys(s.channels));
  const { selectedChannels, chartType, toggleChannel, setChartType, clearChannels } = useAnalyzerStore();
  const selectedSet = useMemo(
    () => new Set(selectedChannels.map((c) => c.channel)),
    [selectedChannels],
  );
  const colorMap = useMemo(
    () => new Map(selectedChannels.map((c) => [c.channel, c.color])),
    [selectedChannels],
  );

  // Group channels: known categories + uncategorized
  const categorized = useMemo(() => {
    const used = new Set(Object.values(CATEGORIES).flat());
    const uncategorized = channelKeys.filter((k) => !used.has(k));
    const groups: [string, string[]][] = [];
    for (const [cat, keys] of Object.entries(CATEGORIES)) {
      const available = keys.filter((k) => channelKeys.includes(k));
      if (available.length > 0) groups.push([cat, available]);
    }
    if (uncategorized.length > 0) groups.push(["Other", uncategorized]);
    return groups;
  }, [channelKeys]);

  return (
    <div className="flex h-full flex-col overflow-auto p-2">
      <div className="mb-2 text-xs font-bold text-neutral-300">Channels</div>

      {/* Chart type selector */}
      <div className="mb-3 flex gap-1">
        {CHART_TYPES.map((ct) => (
          <button
            key={ct.value}
            onClick={() => setChartType(ct.value)}
            className={`rounded px-2 py-0.5 text-xs transition-colors ${
              chartType === ct.value
                ? "bg-[var(--color-accent)] text-black font-bold"
                : "bg-neutral-800 text-neutral-400 hover:text-neutral-200"
            }`}
          >
            {ct.label}
          </button>
        ))}
      </div>

      {selectedChannels.length > 0 && (
        <button
          onClick={clearChannels}
          className="mb-2 text-xs text-neutral-500 hover:text-neutral-300"
        >
          Clear all ({selectedChannels.length})
        </button>
      )}

      {categorized.map(([category, channels]) => (
        <div key={category} className="mb-2">
          <div className="mb-1 text-[10px] font-bold uppercase tracking-wider text-neutral-600">
            {category}
          </div>
          {channels.map((ch) => (
            <label
              key={ch}
              className="flex cursor-pointer items-center gap-2 rounded px-1 py-0.5 text-xs hover:bg-neutral-800"
            >
              <input
                type="checkbox"
                checked={selectedSet.has(ch)}
                onChange={() => toggleChannel(ch)}
                className="accent-[var(--color-accent)]"
              />
              {selectedSet.has(ch) && (
                <span
                  className="inline-block h-2 w-2 rounded-full"
                  style={{ backgroundColor: colorMap.get(ch) }}
                />
              )}
              <span className="font-mono text-neutral-300">{ch}</span>
            </label>
          ))}
        </div>
      ))}

      {channelKeys.length === 0 && (
        <div className="text-xs text-neutral-500">
          Connect to live telemetry or open a session to see channels
        </div>
      )}
    </div>
  );
}
