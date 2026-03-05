/** Schema browser widget type — wraps SchemaBrowser. */

import React, { memo } from "react";
import { registerWidget, type WidgetProps } from "../registry";
import SchemaBrowser from "../../components/explorer/SchemaBrowser";

export const SchemaBrowserWrapper = memo(function SchemaBrowserWrapper() {
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
  component: SchemaBrowserWrapper as React.ComponentType<WidgetProps>,
});
