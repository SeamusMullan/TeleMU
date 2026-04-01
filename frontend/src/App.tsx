import { lazy, Suspense, useState } from "react";
import { HashRouter, Routes, Route, NavLink } from "react-router";
import { TooltipProvider } from "./components/ui";
import AlertBanner from "./components/alerts/AlertBanner";
import AlertFlash from "./components/alerts/AlertFlash";
import PageSkeleton from "./components/common/PageSkeleton";

const DashboardPage = lazy(() => import("./pages/DashboardPage"));
const ExplorerPage = lazy(() => import("./pages/ExplorerPage"));
const AnalyzerPage = lazy(() => import("./pages/AnalyzerPage"));
const ConvertPage = lazy(() => import("./pages/ConvertPage"));
const AlertsPage = lazy(() => import("./pages/AlertsPage"));
const StreamingPage = lazy(() => import("./pages/StreamingPage"));
const SettingsPage = lazy(() => import("./pages/SettingsPage"));
const NotFoundPage = lazy(() => import("./pages/NotFoundPage"));

const NAV_ITEMS = [
  { to: "/", label: "Dashboard" },
  { to: "/explorer", label: "Explorer" },
  { to: "/analyzer", label: "Analyzer" },
  { to: "/convert", label: "Convert" },
  { to: "/alerts", label: "Alerts" },
  { to: "/streaming", label: "Streaming" },
  { to: "/settings", label: "Settings" },
] as const;

function MobileMenu({ open, onClose }: { open: boolean; onClose: () => void }) {
  if (!open) return null;

  return (
    <>
      {/* Backdrop */}
      <div
        className="fixed inset-0 z-40 bg-black/50"
        onClick={onClose}
        aria-hidden="true"
      />
      {/* Drawer */}
      <div className="fixed inset-y-0 left-0 z-50 w-64 bg-neutral-900 shadow-[var(--shadow-lg)]">
        <div className="flex items-center justify-between border-b border-neutral-800 px-4 py-3">
          <span className="text-lg font-bold text-[var(--color-accent)]">TeleMU</span>
          <button
            onClick={onClose}
            aria-label="Close menu"
            className="flex h-11 w-11 items-center justify-center rounded text-neutral-400 hover:text-neutral-200"
          >
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="h-5 w-5">
              <path d="M18 6L6 18M6 6l12 12" strokeLinecap="round" />
            </svg>
          </button>
        </div>
        <nav className="flex flex-col py-2">
          {NAV_ITEMS.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              onClick={onClose}
              className={({ isActive }) =>
                `flex min-h-[44px] items-center px-4 py-3 text-sm transition-colors ${
                  isActive
                    ? "border-l-2 border-[var(--color-accent)] bg-neutral-800 text-white"
                    : "text-neutral-400 hover:bg-neutral-800 hover:text-neutral-200"
                }`
              }
            >
              {item.label}
            </NavLink>
          ))}
        </nav>
      </div>
    </>
  );
}

export default function App() {
  const [menuOpen, setMenuOpen] = useState(false);

  // Close menu on navigation (navigate is called inside MobileMenu)
  const closeMenu = () => setMenuOpen(false);

  return (
    <HashRouter>
      <TooltipProvider delayDuration={300}>
      <div className="flex h-screen flex-col">
        {/* Navigation bar */}
        <nav className="flex items-center gap-1 border-b border-neutral-800 bg-neutral-900 px-4">
          {/* Hamburger button — visible only on small screens */}
          <button
            onClick={() => setMenuOpen(true)}
            aria-label="Open navigation menu"
            aria-expanded={menuOpen}
            className="mr-2 flex h-11 w-11 items-center justify-center rounded text-neutral-400 hover:text-neutral-200 md:hidden"
          >
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="h-5 w-5">
              <path d="M4 6h16M4 12h16M4 18h16" strokeLinecap="round" />
            </svg>
          </button>

          <span className="mr-4 text-lg font-bold text-[var(--color-accent)]">
            TeleMU
          </span>

          {/* Desktop nav links — hidden on small screens */}
          <div className="hidden items-center gap-1 md:flex">
            {NAV_ITEMS.map((item) => (
              <NavLink
                key={item.to}
                to={item.to}
                className={({ isActive }) =>
                  `px-3 py-2 text-sm transition-colors ${
                    isActive
                      ? "border-b-2 border-[var(--color-accent)] text-white"
                      : "text-neutral-400 hover:text-neutral-200"
                  }`
                }
              >
                {item.label}
              </NavLink>
            ))}
          </div>
        </nav>

        {/* Mobile drawer menu */}
        <MobileMenu open={menuOpen} onClose={closeMenu} />

        {/* Page content */}
        <main className="flex-1 overflow-auto">
          <Suspense fallback={<PageSkeleton />}>
            <Routes>
              <Route path="/" element={<DashboardPage />} />
              <Route path="/explorer" element={<ExplorerPage />} />
              <Route path="/analyzer" element={<AnalyzerPage />} />
              <Route path="/convert" element={<ConvertPage />} />
              <Route path="/alerts" element={<AlertsPage />} />
              <Route path="/streaming" element={<StreamingPage />} />
              <Route path="/settings" element={<SettingsPage />} />
              <Route path="*" element={<NotFoundPage />} />
            </Routes>
          </Suspense>
        </main>

        {/* Global alert overlays */}
        <AlertFlash />
        <AlertBanner />
      </div>
      </TooltipProvider>
    </HashRouter>
  );
}
