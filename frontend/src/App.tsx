import { lazy, Suspense } from "react";
import { HashRouter, Routes, Route, NavLink } from "react-router";
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

export default function App() {
  return (
    <HashRouter>
      <div className="flex h-screen flex-col">
        {/* Navigation bar */}
        <nav className="flex items-center gap-1 border-b border-neutral-800 bg-neutral-900 px-4">
          <span className="mr-4 text-lg font-bold text-[var(--color-accent)]">
            TeleMU
          </span>
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
        </nav>

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
    </HashRouter>
  );
}
