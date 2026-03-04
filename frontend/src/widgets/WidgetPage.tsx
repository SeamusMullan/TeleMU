/** Generic widget page renderer — reads layout from store, renders grid. */

import { useCallback, useMemo, useRef } from "react";
import { Responsive, WidthProvider, type Layout } from "react-grid-layout";
import { useLayoutStore } from "../stores/layoutStore";
import { DEFAULT_PAGES } from "./defaults";
import WidgetShell from "./WidgetShell";

const ResponsiveGridLayout = WidthProvider(Responsive);

interface WidgetPageProps {
  pageId: string;
}

export default function WidgetPage({ pageId }: WidgetPageProps) {
  const initPageIfMissing = useLayoutStore((s) => s.initPageIfMissing);
  const editMode = useLayoutStore((s) => s.editMode);
  const updateGridLayouts = useLayoutStore((s) => s.updateGridLayouts);

  // Ensure page exists with defaults
  const defaultPage = DEFAULT_PAGES[pageId];
  if (defaultPage) {
    initPageIfMissing(pageId, defaultPage);
  }

  const page = useLayoutStore((s) => s.getActivePage(pageId));

  // Debounce layout changes
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const handleLayoutChange = useCallback(
    (_current: Layout[], allLayouts: ReactGridLayout.Layouts) => {
      if (debounceRef.current) clearTimeout(debounceRef.current);
      debounceRef.current = setTimeout(() => {
        updateGridLayouts(pageId, {
          lg: (allLayouts.lg ?? []) as Layout[],
          md: (allLayouts.md ?? []) as Layout[],
          sm: (allLayouts.sm ?? []) as Layout[],
        });
      }, 300);
    },
    [pageId, updateGridLayouts],
  );

  const widgetMap = useMemo(() => {
    if (!page) return new Map();
    return new Map(page.widgets.map((w) => [w.id, w]));
  }, [page]);

  if (!page) {
    return (
      <div className="flex h-full items-center justify-center text-neutral-500">
        No layout configured for this page.
      </div>
    );
  }

  return (
    <ResponsiveGridLayout
      className="layout"
      layouts={page.gridLayouts}
      breakpoints={{ lg: 1200, md: 768, sm: 0 }}
      cols={{ lg: 12, md: 10, sm: 6 }}
      rowHeight={30}
      isDraggable={editMode && !page.locked}
      isResizable={editMode && !page.locked}
      draggableHandle=".drag-handle"
      onLayoutChange={handleLayoutChange}
      compactType="vertical"
      margin={[8, 8]}
    >
      {page.gridLayouts.lg.map((layout) => {
        const widget = widgetMap.get(layout.i);
        if (!widget) return <div key={layout.i} />;
        return (
          <div key={layout.i}>
            <WidgetShell
              instance={widget}
              pageId={pageId}
              width={0}
              height={0}
            />
          </div>
        );
      })}
    </ResponsiveGridLayout>
  );
}
