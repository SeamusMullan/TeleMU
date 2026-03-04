/** Sparkline widget type — wraps SparkStrip with widget registry. */

import { memo } from "react";
import { registerWidget, type WidgetProps } from "../registry";
import SparkStrip from "../../components/dashboard/SparkStrip";
import { useTelemetryStore } from "../../stores/telemetryStore";

const SparklineWidgetWrapper = memo(function SparklineWidgetWrapper({ config }: WidgetProps) {
  const channel = config.channel as string;
  const dynamicMaxChannel = config.dynamicMaxChannel as string | undefined;

  const channelData = useTelemetryStore((s) => s.channels[channel]);
  const dynamicMax = useTelemetryStore((s) =>
    dynamicMaxChannel ? s.channels[dynamicMaxChannel]?.value : undefined,
  );

  const value = channelData?.value ?? 0;
  const history = channelData?.history ?? [];
  const max = dynamicMax ?? (config.max as number);

  return (
    <SparkStrip
      label={config.label as string}
      value={value}
      history={history}
      unit={config.unit as string}
      min={config.min as number}
      max={max}
      warnHigh={config.warnHigh as number | undefined}
      warnLow={config.warnLow as number | undefined}
    />
  );
});

registerWidget({
  type: "sparkline",
  name: "Sparkline",
  description: "Value with inline sparkline chart",
  icon: "〜",
  defaultW: 4,
  defaultH: 2,
  minW: 3,
  minH: 2,
  configFields: [
    { key: "channel", label: "Channel", type: "channel", default: "speed" },
    { key: "label", label: "Label", type: "string", default: "Speed" },
    { key: "min", label: "Min", type: "number", default: 0 },
    { key: "max", label: "Max", type: "number", default: 100 },
    { key: "unit", label: "Unit", type: "string", default: "" },
    { key: "warnHigh", label: "Warn High", type: "number", default: undefined },
    { key: "warnLow", label: "Warn Low", type: "number", default: undefined },
    { key: "dynamicMaxChannel", label: "Dynamic Max Channel", type: "channel", default: undefined },
  ],
  component: SparklineWidgetWrapper,
});
