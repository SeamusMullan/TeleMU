/** Session picker widget type — wraps SessionPicker. */

import { memo } from "react";
import { registerWidget, type WidgetProps } from "../registry";
import SessionPicker from "../../components/explorer/SessionPicker";

const SessionPickerWrapper = memo(function SessionPickerWrapper(_props: WidgetProps) {
  return <SessionPicker />;
});

registerWidget({
  type: "session_picker",
  name: "Session Picker",
  description: "Dropdown of .duckdb session files",
  icon: "📂",
  defaultW: 3,
  defaultH: 2,
  minW: 2,
  minH: 2,
  configFields: [],
  component: SessionPickerWrapper,
});
