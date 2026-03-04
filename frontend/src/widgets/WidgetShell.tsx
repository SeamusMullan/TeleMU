/** Widget shell — wraps each widget on the grid with edit-mode controls. */

import { memo, useCallback, useRef, useState, useEffect } from "react";
import { getWidget } from "./registry";
import type { WidgetInstance } from "../stores/layoutStore";
import { useLayoutStore } from "../stores/layoutStore";

interface WidgetShellProps {
  instance: WidgetInstance;
  pageId: string;
  width: number;
  height: number;
}

const WidgetShell = memo(function WidgetShell({ instance, pageId, width, height }: WidgetShellProps) {
  const editMode = useLayoutStore((s) => s.editMode);
  const removeWidget = useLayoutStore((s) => s.removeWidget);
  const def = getWidget(instance.type);
  const [showConfig, setShowConfig] = useState(false);

  const containerRef = useRef<HTMLDivElement>(null);
  const [size, setSize] = useState({ w: width, h: height });

  useEffect(() => {
    if (!containerRef.current) return;
    const ro = new ResizeObserver((entries) => {
      const entry = entries[0];
      if (entry) {
        setSize({
          w: entry.contentRect.width,
          h: entry.contentRect.height,
        });
      }
    });
    ro.observe(containerRef.current);
    return () => ro.disconnect();
  }, []);

  const handleRemove = useCallback(() => {
    removeWidget(pageId, instance.id);
  }, [removeWidget, pageId, instance.id]);

  if (!def) {
    return (
      <div className="flex h-full items-center justify-center rounded border border-red-800 bg-neutral-900 text-xs text-red-400">
        Unknown widget: {instance.type}
      </div>
    );
  }

  const Component = def.component;

  return (
    <div ref={containerRef} className="relative h-full overflow-hidden rounded-lg border border-neutral-800 bg-neutral-900">
      {editMode && (
        <div className="drag-handle flex items-center justify-between border-b border-neutral-700 bg-neutral-800 px-2 py-0.5">
          <span className="cursor-grab text-xs text-neutral-400">{def.name}</span>
          <div className="flex gap-1">
            <button
              onClick={() => setShowConfig(!showConfig)}
              className="text-xs text-neutral-500 hover:text-neutral-200"
              title="Configure"
            >
              ⚙
            </button>
            <button
              onClick={handleRemove}
              className="text-xs text-neutral-500 hover:text-red-400"
              title="Remove"
            >
              ✕
            </button>
          </div>
        </div>
      )}
      <div className={editMode ? "h-[calc(100%-24px)]" : "h-full"}>
        <Component config={instance.config} width={size.w} height={size.h} />
      </div>
      {showConfig && editMode && (
        <WidgetConfigInline
          instance={instance}
          pageId={pageId}
          onClose={() => setShowConfig(false)}
        />
      )}
    </div>
  );
});

export default WidgetShell;

/** Inline config editor that pops over the widget. */
function WidgetConfigInline({
  instance,
  pageId,
  onClose,
}: {
  instance: WidgetInstance;
  pageId: string;
  onClose: () => void;
}) {
  const def = getWidget(instance.type);
  const configureWidget = useLayoutStore((s) => s.configureWidget);
  const [draft, setDraft] = useState<Record<string, unknown>>({ ...instance.config });

  if (!def || def.configFields.length === 0) {
    return (
      <div className="absolute inset-0 z-10 flex items-center justify-center bg-black/80">
        <div className="rounded bg-neutral-800 p-3 text-xs text-neutral-400">
          No configurable fields
          <button onClick={onClose} className="ml-3 text-neutral-500 hover:text-white">
            ✕
          </button>
        </div>
      </div>
    );
  }

  const handleSave = () => {
    configureWidget(pageId, instance.id, draft);
    onClose();
  };

  return (
    <div className="absolute inset-0 z-10 overflow-auto bg-black/90 p-3">
      <div className="mb-2 flex items-center justify-between">
        <span className="text-xs font-bold text-neutral-300">Configure {def.name}</span>
        <button onClick={onClose} className="text-xs text-neutral-500 hover:text-white">✕</button>
      </div>
      <div className="space-y-2">
        {def.configFields.map((field) => (
          <div key={field.key}>
            <label className="mb-0.5 block text-xs text-neutral-400">{field.label}</label>
            {field.type === "boolean" ? (
              <input
                type="checkbox"
                checked={!!draft[field.key]}
                onChange={(e) => setDraft({ ...draft, [field.key]: e.target.checked })}
              />
            ) : field.type === "select" ? (
              <select
                value={String(draft[field.key] ?? "")}
                onChange={(e) => setDraft({ ...draft, [field.key]: e.target.value })}
                className="w-full rounded border border-neutral-600 bg-neutral-800 px-2 py-1 text-xs text-neutral-200"
              >
                {field.options?.map((opt) => (
                  <option key={opt.value} value={opt.value}>{opt.label}</option>
                ))}
              </select>
            ) : (
              <input
                type={field.type === "number" ? "number" : "text"}
                value={draft[field.key] != null ? String(draft[field.key]) : ""}
                onChange={(e) =>
                  setDraft({
                    ...draft,
                    [field.key]: field.type === "number"
                      ? e.target.value === "" ? undefined : Number(e.target.value)
                      : e.target.value,
                  })
                }
                className="w-full rounded border border-neutral-600 bg-neutral-800 px-2 py-1 text-xs text-neutral-200"
              />
            )}
          </div>
        ))}
      </div>
      <div className="mt-3 flex justify-end gap-2">
        <button onClick={onClose} className="rounded bg-neutral-700 px-3 py-1 text-xs text-neutral-300 hover:bg-neutral-600">
          Cancel
        </button>
        <button onClick={handleSave} className="rounded px-3 py-1 text-xs font-bold text-black" style={{ backgroundColor: "var(--color-accent)" }}>
          Save
        </button>
      </div>
    </div>
  );
}
