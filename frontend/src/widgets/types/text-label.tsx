/** Text label widget — simple heading/text display. */

import { memo } from "react";
import { registerWidget, type WidgetProps } from "../registry";

export const TextLabelWidget = memo(function TextLabelWidget({ config }: WidgetProps) {
  const text = (config.text as string) || "Label";
  const fontSize = (config.fontSize as number) || 14;

  return (
    <div className="flex h-full items-center px-3" style={{ fontSize }}>
      <span className="text-neutral-200">{text}</span>
    </div>
  );
});

registerWidget({
  type: "text_label",
  name: "Text Label",
  description: "Simple text or heading label",
  icon: "T",
  defaultW: 3,
  defaultH: 1,
  minW: 1,
  minH: 1,
  configFields: [
    { key: "text", label: "Text", type: "string", default: "Label" },
    { key: "fontSize", label: "Font Size", type: "number", default: 14 },
  ],
  component: TextLabelWidget,
});
