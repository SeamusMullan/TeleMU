/** Data table widget type — wraps DataTable. */

import React, { memo } from "react";
import { registerWidget, type WidgetProps } from "../registry";
import DataTable from "../../components/explorer/DataTable";

export const DataTableWrapper = memo(function DataTableWrapper() {
  return <DataTable />;
});

registerWidget({
  type: "data_table",
  name: "Data Table",
  description: "Virtualized data table for exploring table contents",
  icon: "📊",
  defaultW: 9,
  defaultH: 8,
  minW: 4,
  minH: 4,
  configFields: [],
  component: DataTableWrapper as React.ComponentType<WidgetProps>,
});
