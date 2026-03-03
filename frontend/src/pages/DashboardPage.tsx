/** Live telemetry dashboard — gauges, sparklines, status, lap info. */

import { useTelemetry } from "../hooks/useTelemetry";
import { useTelemetryStore } from "../stores/telemetryStore";
import GaugeWidget from "../components/dashboard/GaugeWidget";
import SparkStrip from "../components/dashboard/SparkStrip";
import StatusRow from "../components/dashboard/StatusRow";
import LapInfo from "../components/dashboard/LapInfo";

const GAUGES = [
  { key: "speed", label: "Speed", min: 0, max: 340, unit: "km/h", warnHigh: 320 },
  { key: "rpm", label: "RPM", min: 0, max: 9000, unit: "rpm", warnHigh: 8500 },
  { key: "throttle", label: "Throttle", min: 0, max: 100, unit: "%" },
  { key: "brake", label: "Brake", min: 0, max: 100, unit: "%", warnHigh: 95 },
  { key: "gear", label: "Gear", min: 0, max: 8, unit: "", decimals: 0 },
  { key: "steering", label: "Steering", min: -450, max: 450, unit: "°", decimals: 1 },
] as const;

const SPARKLINES = [
  { key: "tyre_fl", label: "Tyre FL", min: 50, max: 130, unit: "°C", warnHigh: 115 },
  { key: "tyre_fr", label: "Tyre FR", min: 50, max: 130, unit: "°C", warnHigh: 115 },
  { key: "tyre_rl", label: "Tyre RL", min: 50, max: 130, unit: "°C", warnHigh: 115 },
  { key: "tyre_rr", label: "Tyre RR", min: 50, max: 130, unit: "°C", warnHigh: 115 },
  { key: "fuel", label: "Fuel", min: 0, max: 110, unit: "L", warnLow: 5 },
  { key: "brake_temp", label: "Brake Temp", min: 100, max: 900, unit: "°C", warnHigh: 800 },
] as const;

export default function DashboardPage() {
  useTelemetry();
  const { channels, status, lapInfo, connected } = useTelemetryStore();

  const ch = (key: string) => channels[key] ?? { value: 0, history: [] };

  return (
    <div className="p-4">
      {/* Connection status */}
      <div className="mb-4 flex items-center justify-between">
        <h1 className="text-lg font-bold">Live Dashboard</h1>
        <div className="flex items-center gap-2">
          <div
            className="h-2 w-2 rounded-full"
            style={{ backgroundColor: connected ? "var(--color-green)" : "var(--color-red)" }}
          />
          <span className="text-xs text-neutral-400">
            {connected ? "Connected" : "Disconnected"}
          </span>
        </div>
      </div>

      {/* Status indicators */}
      <div className="mb-4">
        <StatusRow status={status} />
      </div>

      {/* Gauges grid */}
      <div className="mb-4 grid grid-cols-3 gap-3 lg:grid-cols-6">
        {GAUGES.map((g) => {
          const c = ch(g.key);
          // Dynamic max for RPM
          const maxVal =
            g.key === "rpm" && channels["rpm_max"]
              ? channels["rpm_max"].value
              : g.max;
          const warnHigh =
            g.key === "rpm" && channels["rpm_max"]
              ? channels["rpm_max"].value * 0.95
              : "warnHigh" in g ? g.warnHigh : undefined;
          return (
            <GaugeWidget
              key={g.key}
              label={g.label}
              value={c.value}
              min={g.min}
              max={maxVal}
              unit={g.unit}
              warnHigh={warnHigh}
              decimals={"decimals" in g ? g.decimals : 0}
            />
          );
        })}
      </div>

      {/* Sparklines + Lap info */}
      <div className="grid grid-cols-1 gap-3 lg:grid-cols-[1fr_200px]">
        <div className="grid grid-cols-2 gap-2 xl:grid-cols-3">
          {SPARKLINES.map((s) => {
            const c = ch(s.key);
            // Dynamic max for fuel capacity
            const maxVal =
              s.key === "fuel" && channels["fuel_capacity"]
                ? channels["fuel_capacity"].value
                : s.max;
            return (
              <SparkStrip
                key={s.key}
                label={s.label}
                value={c.value}
                history={c.history}
                unit={s.unit}
                min={s.min}
                max={maxVal}
                warnHigh={"warnHigh" in s ? s.warnHigh : undefined}
                warnLow={"warnLow" in s ? s.warnLow : undefined}
              />
            );
          })}
        </div>
        <LapInfo lapInfo={lapInfo} />
      </div>
    </div>
  );
}
