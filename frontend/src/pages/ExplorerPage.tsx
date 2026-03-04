/** Data explorer — widget-based layout. */

import WidgetPage from "../widgets/WidgetPage";
import EditToolbar from "../widgets/EditToolbar";

export default function ExplorerPage() {
  return (
    <div className="flex h-full flex-col">
      <EditToolbar pageId="explorer" />
      <div className="flex-1 overflow-auto p-2">
        <WidgetPage pageId="explorer" />
      </div>
    </div>
  );
}
