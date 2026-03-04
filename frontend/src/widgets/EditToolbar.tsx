/** Floating edit toolbar — toggle edit mode, add widgets, lock layout, reset. */

import { useState } from "react";
import { useLayoutStore } from "../stores/layoutStore";
import { DEFAULT_PAGES } from "./defaults";
import WidgetCatalog from "./WidgetCatalog";

interface EditToolbarProps {
  pageId: string;
}

export default function EditToolbar({ pageId }: EditToolbarProps) {
  const editMode = useLayoutStore((s) => s.editMode);
  const setEditMode = useLayoutStore((s) => s.setEditMode);
  const page = useLayoutStore((s) => s.getActivePage(pageId));
  const setPageLocked = useLayoutStore((s) => s.setPageLocked);
  const [showCatalog, setShowCatalog] = useState(false);

  const handleReset = () => {
    const defaultPage = DEFAULT_PAGES[pageId];
    if (!defaultPage) return;
    // Re-initialize the page with defaults by removing and recreating
    const profile = useLayoutStore.getState().profiles.find(
      (p) => p.id === useLayoutStore.getState().activeProfileId,
    );
    if (profile) {
      // Remove the page then re-init
      useLayoutStore.setState((state) => ({
        profiles: state.profiles.map((p) =>
          p.id === state.activeProfileId
            ? { ...p, pages: { ...p.pages, [pageId]: defaultPage } }
            : p,
        ),
      }));
    }
  };

  // Only show on widget pages
  if (!DEFAULT_PAGES[pageId] && !page) return null;

  return (
    <>
      <div className="flex items-center gap-2 border-b border-neutral-800 bg-neutral-900 px-4 py-1">
        <button
          onClick={() => setEditMode(!editMode)}
          className={`rounded px-2 py-0.5 text-xs font-bold transition-colors ${
            editMode
              ? "bg-[var(--color-accent)] text-black"
              : "bg-neutral-800 text-neutral-400 hover:text-neutral-200"
          }`}
        >
          {editMode ? "Done Editing" : "Edit Layout"}
        </button>
        {editMode && (
          <>
            <button
              onClick={() => setShowCatalog(true)}
              className="rounded bg-neutral-800 px-2 py-0.5 text-xs text-neutral-400 hover:text-neutral-200"
            >
              + Add Widget
            </button>
            <button
              onClick={() => page && setPageLocked(pageId, !page.locked)}
              className="rounded bg-neutral-800 px-2 py-0.5 text-xs text-neutral-400 hover:text-neutral-200"
            >
              {page?.locked ? "🔒 Unlock" : "🔓 Lock"}
            </button>
            <button
              onClick={handleReset}
              className="rounded bg-neutral-800 px-2 py-0.5 text-xs text-neutral-400 hover:text-red-400"
            >
              Reset Default
            </button>
          </>
        )}
      </div>
      {showCatalog && <WidgetCatalog pageId={pageId} onClose={() => setShowCatalog(false)} />}
    </>
  );
}
