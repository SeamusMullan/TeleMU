/** SQL query widget type — wraps SqlQuery. */

import { memo } from "react";
import { registerWidget, type WidgetProps } from "../registry";
import SqlQuery from "../../components/explorer/SqlQuery";

const SqlQueryWrapper = memo(function SqlQueryWrapper(_props: WidgetProps) {
  return <SqlQuery />;
});

registerWidget({
  type: "sql_query",
  name: "SQL Query",
  description: "SQL editor with execute and results view",
  icon: "⌨",
  defaultW: 9,
  defaultH: 4,
  minW: 4,
  minH: 3,
  configFields: [],
  component: SqlQueryWrapper,
});
