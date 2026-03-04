/** Signal analyzer — widget-based layout. */

import { useTelemetry } from "../hooks/useTelemetry";
import WidgetPage from "../widgets/WidgetPage";
import EditToolbar from "../widgets/EditToolbar";

export default function AnalyzerPage() {
  useTelemetry(); // Keep WS connected for live channel data

  return (
    <div className="flex h-full flex-col">
      <EditToolbar pageId="analyzer" />
      <div className="flex-1 overflow-auto p-2">
        <WidgetPage pageId="analyzer" />
      </div>
    </div>
  );
}
