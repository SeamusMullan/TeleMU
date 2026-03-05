/** Gauge widget type — wraps GaugeWidget with widget registry. */

import { memo } from "react";
import { registerWidget, type WidgetProps } from "../registry";
import GaugeWidget from "../../components/dashboard/GaugeWidget";
import { useTelemetryStore } from "../../stores/telemetryStore";

export const GaugeWidgetWrapper = memo(function GaugeWidgetWrapper({ config }: WidgetProps) {
  const channel = config.channel as string;
  const dynamicMaxChannel = config.dynamicMaxChannel as string | undefined;

  const value = useTelemetryStore((s) => s.channels[channel]?.value ?? 0);
  const dynamicMax = useTelemetryStore((s) =>
    dynamicMaxChannel ? s.channels[dynamicMaxChannel]?.value : undefined,
  );

  const max = dynamicMax ?? (config.max as number);
  const warnHigh =
    dynamicMax && (config.warnHigh as number | undefined) === undefined
      ? dynamicMax * 0.95
      : (config.warnHigh as number | undefined);

  return (
    <GaugeWidget
      label={config.label as string}
      value={value}
      min={config.min as number}
      max={max}
      unit={config.unit as string}
      warnHigh={warnHigh}
      decimals={config.decimals as number | undefined}
    />
  );
});

registerWidget({
  type: "gauge",
  name: "Gauge",
  description: "Radial gauge showing a single channel value",
  icon: "⊙",
  defaultW: 2,
  defaultH: 4,
  minW: 2,
  minH: 3,
  configFields: [
    { key: "channel", label: "Channel", type: "channel", default: "speed" },
    { key: "label", label: "Label", type: "string", default: "Speed" },
    { key: "min", label: "Min", type: "number", default: 0 },
    { key: "max", label: "Max", type: "number", default: 100 },
    { key: "unit", label: "Unit", type: "string", default: "" },
    { key: "warnHigh", label: "Warn High", type: "number", default: undefined },
    { key: "decimals", label: "Decimals", type: "number", default: 0 },
    { key: "dynamicMaxChannel", label: "Dynamic Max Channel", type: "channel", default: undefined },
  ],
  component: GaugeWidgetWrapper,
});
