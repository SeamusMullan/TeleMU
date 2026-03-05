/** Status row widget type — wraps StatusRow. */

import React, { memo } from "react";
import { registerWidget, type WidgetProps } from "../registry";
import StatusRow from "../../components/dashboard/StatusRow";
import { useTelemetryStore } from "../../stores/telemetryStore";

export const StatusRowWrapper = memo(function StatusRowWrapper() {
  const status = useTelemetryStore((s) => s.status);
  return <StatusRow status={status} />;
});

registerWidget({
  type: "status_row",
  name: "Status Row",
  description: "DRS, PIT, TC, ABS, FLAG indicator pills",
  icon: "◉",
  defaultW: 8,
  defaultH: 2,
  minW: 4,
  minH: 2,
  configFields: [],
  component: StatusRowWrapper as React.ComponentType<WidgetProps>,
});
