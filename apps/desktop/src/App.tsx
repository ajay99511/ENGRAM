import { useState, useEffect, useCallback, useRef } from "react";
import "./index.css";

import ChatPage from "./pages/ChatPage";
import MemoryPage from "./pages/MemoryPage";
import ModelsPage from "./pages/ModelsPage";
import AgentsPage from "./pages/AgentsPage";
import IngestionPage from "./pages/IngestionPage";
import PodcastPage from "./pages/PodcastPage";
import WorkspacePage from "./pages/WorkspacePage";
import JobsPage from "./pages/JobsPage";
import HealthPage from "./pages/HealthPage";
import TelegramPage from "./pages/TelegramPage";
import { checkHealth } from "./lib/api";
import { register } from "@tauri-apps/plugin-global-shortcut";
import { getCurrentWindow } from "@tauri-apps/api/window";

type Page =
  | "chat" | "memory" | "models" | "agents" | "ingest"
  | "podcast" | "workspace" | "jobs" | "health" | "telegram";

type Theme = "dark" | "light";

const NAV_ITEMS: { id: Page; label: string; icon: string }[] = [
  { id: "chat",      label: "Chat",             icon: "💬" },
  { id: "memory",    label: "Memory",           icon: "🧠" },
  { id: "models",    label: "Models",           icon: "⚡" },
  { id: "agents",    label: "Agents",           icon: "🤖" },
  { id: "ingest",    label: "Ingestion",        icon: "📥" },
  { id: "podcast",   label: "Podcast",          icon: "🎙️" },
  { id: "workspace", label: "Workspace",        icon: "📁" },
  { id: "jobs",      label: "Background Tasks", icon: "⚙️" },
  { id: "health",    label: "System Health",    icon: "🏥" },
  { id: "telegram",  label: "Telegram",         icon: "✈️" },
];

function App() {
  const [activePage, setActivePage] = useState<Page>("chat");
  const [apiOnline, setApiOnline] = useState(false);
  const [theme, setTheme] = useState<Theme>(() => {
    return (localStorage.getItem("pa-theme") as Theme) || "dark";
  });
  const healthRef = useRef<ReturnType<typeof setInterval>>(undefined);

  // Apply theme to <html> so CSS vars cascade everywhere
  useEffect(() => {
    document.documentElement.setAttribute("data-theme", theme);
    localStorage.setItem("pa-theme", theme);
  }, [theme]);

  const toggleTheme = () => setTheme(t => t === "dark" ? "light" : "dark");

  const pollHealth = useCallback(async () => {
    try {
      await checkHealth();
      setApiOnline(true);
    } catch {
      setApiOnline(false);
    }
  }, []);

  useEffect(() => {
    pollHealth();
    healthRef.current = setInterval(pollHealth, 10000);

    const setupShortcut = async () => {
      try {
        await register("CommandOrControl+Space", async (event) => {
          if (event.state === "Pressed") {
            const appWindow = getCurrentWindow();
            const isVisible = await appWindow.isVisible();
            if (isVisible) {
              await appWindow.hide();
            } else {
              await appWindow.show();
              await appWindow.setFocus();
            }
          }
        });
      } catch (err) {
        console.error("Failed to register global shortcut:", err);
      }
    };
    setupShortcut();

    return () => clearInterval(healthRef.current);
  }, [pollHealth]);

  const renderPage = () => {
    switch (activePage) {
      case "chat":      return <ChatPage />;
      case "memory":    return <MemoryPage />;
      case "models":    return <ModelsPage />;
      case "agents":    return <AgentsPage />;
      case "ingest":    return <IngestionPage />;
      case "podcast":   return <PodcastPage />;
      case "workspace": return <WorkspacePage />;
      case "jobs":      return <JobsPage />;
      case "health":    return <HealthPage />;
      case "telegram":  return <TelegramPage />;
    }
  };

  return (
    <div className="app-layout">
      {/* ── Sidebar ── */}
      <aside className="sidebar">
        <div className="sidebar-brand">
          <div className="sidebar-brand-icon">W</div>
          <div>
            <div className="sidebar-brand-text">Agent Workbench</div>
          </div>
          <span className="sidebar-brand-version">v1.0</span>
        </div>

        <nav>
          {NAV_ITEMS.map((item) => (
            <div
              key={item.id}
              className={`nav-item ${activePage === item.id ? "active" : ""}`}
              onClick={() => setActivePage(item.id)}
            >
              <span className="nav-icon">{item.icon}</span>
              {item.label}
            </div>
          ))}
        </nav>

        <div className="sidebar-footer">
          {/* Theme toggle + API status row */}
          <div style={{ display: "flex", alignItems: "center", gap: "8px", padding: "4px 12px 8px" }}>
            <button
              className="theme-toggle"
              onClick={toggleTheme}
              title={`Switch to ${theme === "dark" ? "light" : "dark"} mode`}
              aria-label="Toggle theme"
            >
              {theme === "dark" ? "☀️" : "🌙"}
            </button>
            <span style={{ fontSize: 11, color: "var(--text-muted)", flex: 1 }}>
              {theme === "dark" ? "Light mode" : "Dark mode"}
            </span>
          </div>

          <div className="nav-item" style={{ cursor: "default" }}>
            <span className={`status-dot ${apiOnline ? "online" : "offline"}`} />
            <span style={{ fontSize: 12, color: "var(--text-muted)" }}>
              API {apiOnline ? "Connected" : "Offline"}
            </span>
          </div>
        </div>
      </aside>

      {/* ── Main Content ── */}
      <main className="main-content">{renderPage()}</main>
    </div>
  );
}

export default App;
