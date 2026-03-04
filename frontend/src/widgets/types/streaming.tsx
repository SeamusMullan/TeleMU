/** Streaming panel widget type — wraps StreamingPanel. */

import { memo } from "react";
import { registerWidget, type WidgetProps } from "../registry";
import StreamingPanel from "../../components/dashboard/StreamingPanel";

const StreamingWrapper = memo(function StreamingWrapper(_props: WidgetProps) {
  return <StreamingPanel />;
});

registerWidget({
  type: "streaming_panel",
  name: "Streaming Panel",
  description: "LAN streaming server start/stop control",
  icon: "📡",
  defaultW: 3,
  defaultH: 4,
  minW: 2,
  minH: 3,
  configFields: [],
  component: StreamingWrapper,
});
