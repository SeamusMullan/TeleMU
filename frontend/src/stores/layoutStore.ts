/** Layout store — persisted widget layouts per page. */

import { create } from "zustand";
import { persist } from "zustand/middleware";
import type { Layout } from "react-grid-layout";

export interface WidgetInstance {
  id: string;
  type: string;
  config: Record<string, unknown>;
}

export interface PageLayout {
  id: string;
  name: string;
  gridLayouts: { lg: Layout[]; md: Layout[]; sm: Layout[] };
  widgets: WidgetInstance[];
  locked: boolean;
}

export interface LayoutProfile {
  id: string;
  name: string;
  pages: Record<string, PageLayout>;
}

interface LayoutState {
  profiles: LayoutProfile[];
  activeProfileId: string;
  editMode: boolean;

  getActivePage: (pageId: string) => PageLayout | undefined;
  setEditMode: (v: boolean) => void;
  addWidget: (pageId: string, widget: WidgetInstance, layout: Layout) => void;
  removeWidget: (pageId: string, widgetId: string) => void;
  configureWidget: (pageId: string, widgetId: string, config: Record<string, unknown>) => void;
  updateGridLayouts: (pageId: string, layouts: { lg: Layout[]; md: Layout[]; sm: Layout[] }) => void;
  setPageLocked: (pageId: string, locked: boolean) => void;
  saveProfile: (profile: LayoutProfile) => void;
  deleteProfile: (profileId: string) => void;
  setActiveProfile: (profileId: string) => void;
  importProfile: (profile: LayoutProfile) => void;
  exportProfile: (profileId: string) => LayoutProfile | undefined;
  resetToDefault: () => void;
  initPageIfMissing: (pageId: string, defaultPage: PageLayout) => void;
}

let defaultProfileFactory: (() => LayoutProfile) | null = null;

export function setDefaultProfileFactory(factory: () => LayoutProfile): void {
  defaultProfileFactory = factory;
}

function createEmptyProfile(): LayoutProfile {
  if (defaultProfileFactory) return defaultProfileFactory();
  return {
    id: "default",
    name: "Default",
    pages: {},
  };
}

function getActiveProfile(state: { profiles: LayoutProfile[]; activeProfileId: string }): LayoutProfile {
  return state.profiles.find((p) => p.id === state.activeProfileId) ?? state.profiles[0]!;
}

function updateActiveProfile(
  state: { profiles: LayoutProfile[]; activeProfileId: string },
  updater: (profile: LayoutProfile) => LayoutProfile,
): { profiles: LayoutProfile[] } {
  return {
    profiles: state.profiles.map((p) =>
      p.id === state.activeProfileId ? updater(p) : p,
    ),
  };
}

export const useLayoutStore = create<LayoutState>()(
  persist(
    (set, get) => ({
      profiles: [createEmptyProfile()],
      activeProfileId: "default",
      editMode: false,

      getActivePage: (pageId: string) => {
        const profile = getActiveProfile(get());
        return profile?.pages[pageId];
      },

      setEditMode: (v) => set({ editMode: v }),

      addWidget: (pageId, widget, layout) =>
        set((state) =>
          updateActiveProfile(state, (profile) => {
            const page = profile.pages[pageId];
            if (!page) return profile;
            return {
              ...profile,
              pages: {
                ...profile.pages,
                [pageId]: {
                  ...page,
                  widgets: [...page.widgets, widget],
                  gridLayouts: {
                    lg: [...page.gridLayouts.lg, layout],
                    md: [...page.gridLayouts.md, { ...layout, w: Math.min(layout.w, 10) }],
                    sm: [...page.gridLayouts.sm, { ...layout, w: Math.min(layout.w, 6), x: 0 }],
                  },
                },
              },
            };
          }),
        ),

      removeWidget: (pageId, widgetId) =>
        set((state) =>
          updateActiveProfile(state, (profile) => {
            const page = profile.pages[pageId];
            if (!page) return profile;
            return {
              ...profile,
              pages: {
                ...profile.pages,
                [pageId]: {
                  ...page,
                  widgets: page.widgets.filter((w) => w.id !== widgetId),
                  gridLayouts: {
                    lg: page.gridLayouts.lg.filter((l) => l.i !== widgetId),
                    md: page.gridLayouts.md.filter((l) => l.i !== widgetId),
                    sm: page.gridLayouts.sm.filter((l) => l.i !== widgetId),
                  },
                },
              },
            };
          }),
        ),

      configureWidget: (pageId, widgetId, config) =>
        set((state) =>
          updateActiveProfile(state, (profile) => {
            const page = profile.pages[pageId];
            if (!page) return profile;
            return {
              ...profile,
              pages: {
                ...profile.pages,
                [pageId]: {
                  ...page,
                  widgets: page.widgets.map((w) =>
                    w.id === widgetId ? { ...w, config: { ...w.config, ...config } } : w,
                  ),
                },
              },
            };
          }),
        ),

      updateGridLayouts: (pageId, layouts) =>
        set((state) =>
          updateActiveProfile(state, (profile) => {
            const page = profile.pages[pageId];
            if (!page) return profile;
            return {
              ...profile,
              pages: {
                ...profile.pages,
                [pageId]: { ...page, gridLayouts: layouts },
              },
            };
          }),
        ),

      setPageLocked: (pageId, locked) =>
        set((state) =>
          updateActiveProfile(state, (profile) => {
            const page = profile.pages[pageId];
            if (!page) return profile;
            return {
              ...profile,
              pages: {
                ...profile.pages,
                [pageId]: { ...page, locked },
              },
            };
          }),
        ),

      saveProfile: (profile) =>
        set((state) => {
          const exists = state.profiles.some((p) => p.id === profile.id);
          return {
            profiles: exists
              ? state.profiles.map((p) => (p.id === profile.id ? profile : p))
              : [...state.profiles, profile],
          };
        }),

      deleteProfile: (profileId) =>
        set((state) => ({
          profiles: state.profiles.filter((p) => p.id !== profileId),
          activeProfileId:
            state.activeProfileId === profileId
              ? state.profiles[0]?.id ?? "default"
              : state.activeProfileId,
        })),

      setActiveProfile: (profileId) => set({ activeProfileId: profileId }),

      importProfile: (profile) =>
        set((state) => {
          const newId = `${profile.id}-${Date.now()}`;
          return {
            profiles: [...state.profiles, { ...profile, id: newId, name: `${profile.name} (imported)` }],
          };
        }),

      exportProfile: (profileId) => {
        return get().profiles.find((p) => p.id === profileId);
      },

      resetToDefault: () => {
        const defaultProfile = createEmptyProfile();
        set({
          profiles: [defaultProfile],
          activeProfileId: "default",
        });
      },

      initPageIfMissing: (pageId, defaultPage) =>
        set((state) => {
          const profile = getActiveProfile(state);
          if (profile?.pages[pageId]) return state;
          return updateActiveProfile(state, (p) => ({
            ...p,
            pages: { ...p.pages, [pageId]: defaultPage },
          }));
        }),
    }),
    {
      name: "telemu-layouts",
    },
  ),
);
