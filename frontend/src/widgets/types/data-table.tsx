/** Data table widget type — wraps DataTable. */

import { memo } from "react";
import { registerWidget, type WidgetProps } from "../registry";
import DataTable from "../../components/explorer/DataTable";

const DataTableWrapper = memo(function DataTableWrapper(_props: WidgetProps) {
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
  component: DataTableWrapper,
});
