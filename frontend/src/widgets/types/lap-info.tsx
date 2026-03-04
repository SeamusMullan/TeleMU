/** Lap info widget type — wraps LapInfo. */

import React, { memo } from "react";
import { registerWidget, type WidgetProps } from "../registry";
import LapInfo from "../../components/dashboard/LapInfo";
import { useTelemetryStore } from "../../stores/telemetryStore";

const LapInfoWrapper = memo(function LapInfoWrapper() {
  const lapInfo = useTelemetryStore((s) => s.lapInfo);
  return <LapInfo lapInfo={lapInfo} />;
});

registerWidget({
  type: "lap_info",
  name: "Lap Info",
  description: "Lap number, last/best time, sector splits",
  icon: "⏱",
  defaultW: 3,
  defaultH: 4,
  minW: 2,
  minH: 3,
  configFields: [],
  component: LapInfoWrapper as React.ComponentType<WidgetProps>,
});
