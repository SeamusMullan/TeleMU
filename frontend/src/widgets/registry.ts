/** Widget registry — type definitions and registration. */

import type { ComponentType } from "react";

export type ConfigFieldType = "string" | "number" | "boolean" | "select" | "channel";

export interface WidgetConfigField {
  key: string;
  label: string;
  type: ConfigFieldType;
  default: unknown;
  options?: { label: string; value: string | number }[];
}

export interface WidgetProps {
  config: Record<string, unknown>;
  width: number;
  height: number;
}

export interface WidgetDefinition {
  type: string;
  name: string;
  description: string;
  icon: string;
  defaultW: number;
  defaultH: number;
  minW: number;
  minH: number;
  configFields: WidgetConfigField[];
  component: ComponentType<WidgetProps>;
}

const registry = new Map<string, WidgetDefinition>();

export function registerWidget(def: WidgetDefinition): void {
  registry.set(def.type, def);
}

export function getWidget(type: string): WidgetDefinition | undefined {
  return registry.get(type);
}

export function getAllWidgets(): WidgetDefinition[] {
  return Array.from(registry.values());
}
