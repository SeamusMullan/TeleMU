/** Live telemetry dashboard — widget-based layout. */

import { useTelemetry } from "../hooks/useTelemetry";
import WidgetPage from "../widgets/WidgetPage";
import EditToolbar from "../widgets/EditToolbar";

export default function DashboardPage() {
  useTelemetry();

  return (
    <div className="flex h-full flex-col">
      <EditToolbar pageId="dashboard" />
      <div className="flex-1 overflow-auto p-2">
        <WidgetPage pageId="dashboard" />
      </div>
    </div>
  );
}
