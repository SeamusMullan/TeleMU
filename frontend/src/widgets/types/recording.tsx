/** Recording widget type — wraps RecordingControls. */

import { memo } from "react";
import { registerWidget, type WidgetProps } from "../registry";
import RecordingControls from "../../components/dashboard/RecordingControls";

const RecordingWrapper = memo(function RecordingWrapper(_props: WidgetProps) {
  return <RecordingControls />;
});

registerWidget({
  type: "recording",
  name: "Recording Controls",
  description: "Start/stop recording with timer and file info",
  icon: "⏺",
  defaultW: 4,
  defaultH: 2,
  minW: 3,
  minH: 2,
  configFields: [],
  component: RecordingWrapper,
});
