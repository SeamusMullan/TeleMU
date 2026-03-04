/** Widget catalog modal — shows all registered widgets for adding to a page. */

import { getAllWidgets } from "./registry";
import { useLayoutStore } from "../stores/layoutStore";

interface WidgetCatalogProps {
  pageId: string;
  onClose: () => void;
}

export default function WidgetCatalog({ pageId, onClose }: WidgetCatalogProps) {
  const addWidget = useLayoutStore((s) => s.addWidget);
  const widgets = getAllWidgets();

  const handleAdd = (type: string) => {
    const def = widgets.find((w) => w.type === type);
    if (!def) return;

    const id = `${type}_${Date.now()}`;
    const config: Record<string, unknown> = {};
    for (const field of def.configFields) {
      if (field.default !== undefined) {
        config[field.key] = field.default;
      }
    }

    addWidget(
      pageId,
      { id, type, config },
      { i: id, x: 0, y: Infinity, w: def.defaultW, h: def.defaultH, minW: def.minW, minH: def.minH },
    );
    onClose();
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70" onClick={onClose}>
      <div
        className="max-h-[80vh] w-full max-w-lg overflow-auto rounded-lg border border-neutral-700 bg-neutral-900 p-4 shadow-xl"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="mb-3 flex items-center justify-between">
          <h2 className="text-sm font-bold text-neutral-200">Add Widget</h2>
          <button onClick={onClose} className="text-neutral-500 hover:text-white">✕</button>
        </div>
        <div className="grid grid-cols-2 gap-2">
          {widgets.map((w) => (
            <button
              key={w.type}
              onClick={() => handleAdd(w.type)}
              className="flex items-center gap-2 rounded border border-neutral-700 bg-neutral-800 p-3 text-left transition-colors hover:border-[var(--color-accent)]"
            >
              <span className="text-lg">{w.icon}</span>
              <div>
                <div className="text-xs font-bold text-neutral-200">{w.name}</div>
                <div className="text-xs text-neutral-500">{w.description}</div>
              </div>
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}
