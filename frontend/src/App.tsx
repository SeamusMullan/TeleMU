import { BrowserRouter, Routes, Route, NavLink } from "react-router";
import DashboardPage from "./pages/DashboardPage";
import AnalyzerPage from "./pages/AnalyzerPage";
import ExplorerPage from "./pages/ExplorerPage";
import ConvertPage from "./pages/ConvertPage";
import SettingsPage from "./pages/SettingsPage";

const NAV_ITEMS = [
  { to: "/", label: "Dashboard" },
  { to: "/explorer", label: "Explorer" },
  { to: "/analyzer", label: "Analyzer" },
  { to: "/convert", label: "Convert" },
  { to: "/settings", label: "Settings" },
] as const;

export default function App() {
  return (
    <BrowserRouter>
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
          <Routes>
            <Route path="/" element={<DashboardPage />} />
            <Route path="/explorer" element={<ExplorerPage />} />
            <Route path="/analyzer" element={<AnalyzerPage />} />
            <Route path="/convert" element={<ConvertPage />} />
            <Route path="/settings" element={<SettingsPage />} />
          </Routes>
        </main>
      </div>
    </BrowserRouter>
  );
}
