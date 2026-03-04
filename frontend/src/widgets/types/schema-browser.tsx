/** Schema browser widget type — wraps SchemaBrowser. */

import { memo } from "react";
import { registerWidget, type WidgetProps } from "../registry";
import SchemaBrowser from "../../components/explorer/SchemaBrowser";

const SchemaBrowserWrapper = memo(function SchemaBrowserWrapper(_props: WidgetProps) {
  return <SchemaBrowser />;
});

registerWidget({
  type: "schema_browser",
  name: "Schema Browser",
  description: "Tree view of tables and columns with type badges",
  icon: "🌳",
  defaultW: 3,
  defaultH: 10,
  minW: 2,
  minH: 4,
  configFields: [],
  component: SchemaBrowserWrapper,
});
