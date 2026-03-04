/** Channel selector widget type — wraps ChannelSelector. */

import React, { memo } from "react";
import { registerWidget, type WidgetProps } from "../registry";
import ChannelSelector from "../../components/analyzer/ChannelSelector";

const ChannelSelectorWrapper = memo(function ChannelSelectorWrapper() {
  return <ChannelSelector />;
});

registerWidget({
  type: "channel_selector",
  name: "Channel Selector",
  description: "Checkbox tree to select channels for analysis",
  icon: "☑",
  defaultW: 3,
  defaultH: 12,
  minW: 2,
  minH: 4,
  configFields: [],
  component: ChannelSelectorWrapper as React.ComponentType<WidgetProps>,
});
