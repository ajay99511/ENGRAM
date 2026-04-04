/**
 * Autonomous Agents Tab Component
 *
 * Displays autonomous agent controls and event stream:
 * - Watch mode control
 * - Research scheduling
 * - Gap analysis
 * - Real-time event viewer
 */

import { useState, useEffect, useRef } from "react";
import {
  getAutonomousStatus,
  startWatchMode,
  stopWatchMode,
  startResearch,
  stopResearch,
  startGapAnalysis,
  stopGapAnalysis,
  stopAllAutonomous,
  streamAutonomousEvents,
  getAutonomousEventHistory,
  type AutonomousStatus,
  type AutonomousEvent,
} from "../../lib/api";

export default function AutonomousAgentsTab() {
  // Status state
  const [status, setStatus] = useState<AutonomousStatus | null>(null);
  const [saving, setSaving] = useState(false);

  // Event stream state
  const [events, setEvents] = useState<AutonomousEvent[]>([]);
  const [eventFilter, setEventFilter] = useState<string[]>([]);
  const [streaming, setStreaming] = useState(false);

  // Form state
  const [watchPath, setWatchPath] = useState("");
  const [watchInterval, setWatchInterval] = useState(30);
  const [researchTopics, setResearchTopics] = useState("");
  const [researchInterval, setResearchInterval] = useState(6);
  const [gapPath, setGapPath] = useState("");
  const [gapInterval, setGapInterval] = useState(24);

  const eventsEndRef = useRef<HTMLDivElement>(null);

  // Load initial status
  useEffect(() => {
    loadStatus();
    const interval = setInterval(loadStatus, 10000); // Refresh status every 10s
    return () => clearInterval(interval);
  }, []);

  // Load event history
  useEffect(() => {
    loadEventHistory();
  }, []);

  // Stream new events
  useEffect(() => {
    let abort = false;

    const startStream = async () => {
      setStreaming(true);
      try {
        for await (const event of streamAutonomousEvents(eventFilter.length > 0 ? eventFilter : undefined)) {
          if (abort) break;
          setEvents((prev) => [event, ...prev].slice(0, 100)); // Keep last 100
        }
      } catch (err) {
        console.error("Event stream error:", err);
      } finally {
        setStreaming(false);
      }
    };

    startStream();

    return () => {
      abort = true;
    };
  }, [eventFilter]);

  // Auto-scroll events
  useEffect(() => {
    eventsEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [events]);

  const loadStatus = async () => {
    try {
      const data = await getAutonomousStatus();
      setStatus(data);
    } catch (err) {
      console.error("Failed to load autonomous status:", err);
    }
  };

  const loadEventHistory = async () => {
    try {
      const data = await getAutonomousEventHistory(50);
      setEvents(data.events);
    } catch (err) {
      console.error("Failed to load event history:", err);
    }
  };

  const handleStartWatch = async () => {
    if (!watchPath) return;
    setSaving(true);
    try {
      await startWatchMode(watchPath, watchInterval);
      await loadStatus();
      setWatchPath("");
    } catch (err) {
      alert(`Error: ${err instanceof Error ? err.message : "Failed to start watch mode"}`);
    } finally {
      setSaving(false);
    }
  };

  const handleStopWatch = async () => {
    setSaving(true);
    try {
      await stopWatchMode();
      await loadStatus();
    } catch (err) {
      alert(`Error: ${err instanceof Error ? err.message : "Failed to stop watch mode"}`);
    } finally {
      setSaving(false);
    }
  };

  const handleStartResearch = async () => {
    if (!researchTopics.trim()) return;
    const topics = researchTopics.split(",").map((t) => t.trim()).filter(Boolean);
    setSaving(true);
    try {
      await startResearch(topics, researchInterval);
      await loadStatus();
      setResearchTopics("");
    } catch (err) {
      alert(`Error: ${err instanceof Error ? err.message : "Failed to start research"}`);
    } finally {
      setSaving(false);
    }
  };

  const handleStopResearch = async () => {
    setSaving(true);
    try {
      await stopResearch();
      await loadStatus();
    } catch (err) {
      alert(`Error: ${err instanceof Error ? err.message : "Failed to stop research"}`);
    } finally {
      setSaving(false);
    }
  };

  const handleStartGap = async () => {
    if (!gapPath) return;
    setSaving(true);
    try {
      await startGapAnalysis(gapPath, gapInterval);
      await loadStatus();
      setGapPath("");
    } catch (err) {
      alert(`Error: ${err instanceof Error ? err.message : "Failed to start gap analysis"}`);
    } finally {
      setSaving(false);
    }
  };

  const handleStopGap = async () => {
    setSaving(true);
    try {
      await stopGapAnalysis();
      await loadStatus();
    } catch (err) {
      alert(`Error: ${err instanceof Error ? err.message : "Failed to stop gap analysis"}`);
    } finally {
      setSaving(false);
    }
  };

  const handleStopAll = async () => {
    if (!confirm("Stop all autonomous tasks?")) return;
    setSaving(true);
    try {
      await stopAllAutonomous();
      await loadStatus();
    } catch (err) {
      alert(`Error: ${err instanceof Error ? err.message : "Failed to stop all tasks"}`);
    } finally {
      setSaving(false);
    }
  };

  const toggleEventFilter = (eventType: string) => {
    setEventFilter((prev) =>
      prev.includes(eventType)
        ? prev.filter((t) => t !== eventType)
        : [...prev, eventType]
    );
  };

  const getEventIcon = (type: string) => {
    switch (type) {
      case "watch_change": return "📁";
      case "research_complete": return "📚";
      case "gap_found": return "⚠️";
      case "error": return "❌";
      default: return "📄";
    }
  };

  const getEventColor = (type: string) => {
    switch (type) {
      case "watch_change": return "var(--info-color)";
      case "research_complete": return "var(--success-color)";
      case "gap_found": return "var(--warning-color)";
      case "error": return "var(--error-color)";
      default: return "var(--text-muted)";
    }
  };

  const formatInterval = (interval: string) => {
    if (!interval) return "N/A";
    const parts = interval.split(":");
    if (parts.length === 3) {
      const hours = parseInt(parts[0]);
      const minutes = parseInt(parts[1]);
      if (hours > 0) return `${hours}h ${minutes}m`;
      return `${minutes}m`;
    }
    return interval;
  };

  return (
    <div style={{ padding: "20px", height: "100%", overflow: "auto" }}>
      {/* Status Overview */}
      <section className="card" style={{
        background: "var(--bg-secondary)",
        padding: "20px",
        marginBottom: "24px",
      }}>
        <h2 style={{ marginTop: 0, marginBottom: "16px" }}>🤖 Autonomous Agent Status</h2>

        {status ? (
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(250px, 1fr))", gap: "16px" }}>
            {/* Watch Mode Status */}
            <div style={{
              background: "var(--bg-input)",
              padding: "16px",
              borderRadius: "8px",
              border: `1px solid ${status.watch_mode.active ? "var(--success-color)" : "var(--border)"}`,
            }}>
              <div style={{ fontSize: "12px", color: "var(--text-muted)", marginBottom: "8px" }}>
                📁 Watch Mode
              </div>
              <div style={{ fontSize: "18px", fontWeight: 700, marginBottom: "8px" }}>
                {status.watch_mode.active ? "✅ Active" : "⏸️ Inactive"}
              </div>
              {status.watch_mode.config && (
                <div style={{ fontSize: "11px", color: "var(--text-muted)" }}>
                  <div>Path: {status.watch_mode.config.repo_path}</div>
                  <div>Interval: {formatInterval(status.watch_mode.config.interval)}</div>
                </div>
              )}
            </div>

            {/* Research Status */}
            <div style={{
              background: "var(--bg-input)",
              padding: "16px",
              borderRadius: "8px",
              border: `1px solid ${status.research.active ? "var(--success-color)" : "var(--border)"}`,
            }}>
              <div style={{ fontSize: "12px", color: "var(--text-muted)", marginBottom: "8px" }}>
                📚 Research
              </div>
              <div style={{ fontSize: "18px", fontWeight: 700, marginBottom: "8px" }}>
                {status.research.active ? "✅ Active" : "⏸️ Inactive"}
              </div>
              {status.research.config && (
                <div style={{ fontSize: "11px", color: "var(--text-muted)" }}>
                  <div>Topics: {status.research.config.topics.length}</div>
                  <div>Interval: {formatInterval(status.research.config.interval)}</div>
                </div>
              )}
            </div>

            {/* Gap Analysis Status */}
            <div style={{
              background: "var(--bg-input)",
              padding: "16px",
              borderRadius: "8px",
              border: `1px solid ${status.gap_analysis.active ? "var(--success-color)" : "var(--border)"}`,
            }}>
              <div style={{ fontSize: "12px", color: "var(--text-muted)", marginBottom: "8px" }}>
                ⚠️ Gap Analysis
              </div>
              <div style={{ fontSize: "18px", fontWeight: 700, marginBottom: "8px" }}>
                {status.gap_analysis.active ? "✅ Active" : "⏸️ Inactive"}
              </div>
              {status.gap_analysis.config && (
                <div style={{ fontSize: "11px", color: "var(--text-muted)" }}>
                  <div>Path: {status.gap_analysis.config.project_path}</div>
                  <div>Interval: {formatInterval(status.gap_analysis.config.interval)}</div>
                </div>
              )}
            </div>

            {/* Callbacks */}
            <div style={{
              background: "var(--bg-input)",
              padding: "16px",
              borderRadius: "8px",
              border: "1px solid var(--border)",
            }}>
              <div style={{ fontSize: "12px", color: "var(--text-muted)", marginBottom: "8px" }}>
                🔔 Event Listeners
              </div>
              <div style={{ fontSize: "11px", color: "var(--text-muted)" }}>
                {Object.entries(status.callbacks_registered).map(([type, count]) => (
                  <div key={type}>
                    {type}: {count}
                  </div>
                ))}
              </div>
            </div>
          </div>
        ) : (
          <div className="empty-state">
            <div className="empty-state-text">Loading status...</div>
          </div>
        )}

        {/* Stop All Button */}
        <div style={{ marginTop: "16px", textAlign: "right" }}>
          <button
            className="btn btn-danger"
            onClick={handleStopAll}
            disabled={saving || !status?.running}
          >
            ⏹️ Stop All Tasks
          </button>
        </div>
      </section>

      {/* Control Panels */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(350px, 1fr))", gap: "24px", marginBottom: "24px" }}>
        
        {/* Watch Mode Control */}
        <section className="card" style={{
          background: "var(--bg-secondary)",
          padding: "20px",
        }}>
          <h3 style={{ marginTop: 0, marginBottom: "16px" }}>📁 Watch Mode Control</h3>

          <div style={{ marginBottom: "12px" }}>
            <label style={{ display: "block", marginBottom: "4px", fontSize: "13px" }}>
              Repository Path
            </label>
            <input
              type="text"
              className="input"
              value={watchPath}
              onChange={(e) => setWatchPath(e.target.value)}
              placeholder="/path/to/repo"
              disabled={saving || status?.watch_mode.active}
            />
          </div>

          <div style={{ marginBottom: "12px" }}>
            <label style={{ display: "block", marginBottom: "4px", fontSize: "13px" }}>
              Check Interval (minutes)
            </label>
            <input
              type="number"
              className="input"
              value={watchInterval}
              onChange={(e) => setWatchInterval(parseInt(e.target.value) || 30)}
              min={1}
              max={1440}
              disabled={saving || status?.watch_mode.active}
            />
          </div>

          <div style={{ display: "flex", gap: "8px" }}>
            {!status?.watch_mode.active ? (
              <button
                className="btn btn-primary"
                onClick={handleStartWatch}
                disabled={saving || !watchPath}
              >
                ▶️ Start Watch
              </button>
            ) : (
              <button
                className="btn btn-secondary"
                onClick={handleStopWatch}
                disabled={saving}
              >
                ⏹️ Stop Watch
              </button>
            )}
          </div>
        </section>

        {/* Research Control */}
        <section className="card" style={{
          background: "var(--bg-secondary)",
          padding: "20px",
        }}>
          <h3 style={{ marginTop: 0, marginBottom: "16px" }}>📚 Research Control</h3>

          <div style={{ marginBottom: "12px" }}>
            <label style={{ display: "block", marginBottom: "4px", fontSize: "13px" }}>
              Topics (comma-separated)
            </label>
            <input
              type="text"
              className="input"
              value={researchTopics}
              onChange={(e) => setResearchTopics(e.target.value)}
              placeholder="Python async, FastAPI security"
              disabled={saving || status?.research.active}
            />
          </div>

          <div style={{ marginBottom: "12px" }}>
            <label style={{ display: "block", marginBottom: "4px", fontSize: "13px" }}>
              Research Interval (hours)
            </label>
            <input
              type="number"
              className="input"
              value={researchInterval}
              onChange={(e) => setResearchInterval(parseInt(e.target.value) || 6)}
              min={1}
              max={168}
              disabled={saving || status?.research.active}
            />
          </div>

          <div style={{ display: "flex", gap: "8px" }}>
            {!status?.research.active ? (
              <button
                className="btn btn-primary"
                onClick={handleStartResearch}
                disabled={saving || !researchTopics.trim()}
              >
                ▶️ Start Research
              </button>
            ) : (
              <button
                className="btn btn-secondary"
                onClick={handleStopResearch}
                disabled={saving}
              >
                ⏹️ Stop Research
              </button>
            )}
          </div>
        </section>

        {/* Gap Analysis Control */}
        <section className="card" style={{
          background: "var(--bg-secondary)",
          padding: "20px",
        }}>
          <h3 style={{ marginTop: 0, marginBottom: "16px" }}>⚠️ Gap Analysis Control</h3>

          <div style={{ marginBottom: "12px" }}>
            <label style={{ display: "block", marginBottom: "4px", fontSize: "13px" }}>
              Project Path
            </label>
            <input
              type="text"
              className="input"
              value={gapPath}
              onChange={(e) => setGapPath(e.target.value)}
              placeholder="/path/to/project"
              disabled={saving || status?.gap_analysis.active}
            />
          </div>

          <div style={{ marginBottom: "12px" }}>
            <label style={{ display: "block", marginBottom: "4px", fontSize: "13px" }}>
              Analysis Interval (hours)
            </label>
            <input
              type="number"
              className="input"
              value={gapInterval}
              onChange={(e) => setGapInterval(parseInt(e.target.value) || 24)}
              min={1}
              max={168}
              disabled={saving || status?.gap_analysis.active}
            />
          </div>

          <div style={{ display: "flex", gap: "8px" }}>
            {!status?.gap_analysis.active ? (
              <button
                className="btn btn-primary"
                onClick={handleStartGap}
                disabled={saving || !gapPath}
              >
                ▶️ Start Analysis
              </button>
            ) : (
              <button
                className="btn btn-secondary"
                onClick={handleStopGap}
                disabled={saving}
              >
                ⏹️ Stop Analysis
              </button>
            )}
          </div>
        </section>
      </div>

      {/* Event Stream */}
      <section className="card" style={{
        background: "var(--bg-secondary)",
        padding: "20px",
        marginBottom: "24px",
      }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "16px" }}>
          <h2 style={{ marginTop: 0, marginBottom: 0 }}>📡 Event Stream</h2>
          
          {/* Event Type Filters */}
          <div style={{ display: "flex", gap: "8px" }}>
            {["watch_change", "research_complete", "gap_found", "error"].map((type) => (
              <button
                key={type}
                className={`btn ${eventFilter.includes(type) ? "btn-primary" : "btn-secondary"}`}
                onClick={() => toggleEventFilter(type)}
                style={{ fontSize: "11px", padding: "4px 8px" }}
              >
                {getEventIcon(type)} {type.replace("_", " ")}
              </button>
            ))}
          </div>
        </div>

        {/* Events List */}
        <div style={{
          background: "var(--bg-input)",
          borderRadius: "8px",
          border: "1px solid var(--border)",
          maxHeight: "400px",
          overflow: "auto",
          padding: "12px",
        }}>
          {events.length === 0 ? (
            <div className="empty-state">
              <div className="empty-state-icon">📡</div>
              <div className="empty-state-title">No Events Yet</div>
              <div className="empty-state-text">
                Events will appear here in real-time
              </div>
            </div>
          ) : (
            <div style={{ display: "flex", flexDirection: "column", gap: "8px" }}>
              {events.map((event, idx) => (
                <div
                  key={event.id || idx}
                  style={{
                    background: "var(--bg-secondary)",
                    padding: "12px",
                    borderRadius: "6px",
                    border: `1px solid ${getEventColor(event.type)}`,
                  }}
                >
                  <div style={{ display: "flex", alignItems: "center", gap: "8px", marginBottom: "4px" }}>
                    <span style={{ fontSize: "16px" }}>{getEventIcon(event.type)}</span>
                    <span style={{ fontSize: "12px", fontWeight: 600, color: getEventColor(event.type) }}>
                      {event.type.replace("_", " ")}
                    </span>
                    <span style={{ fontSize: "11px", color: "var(--text-muted)", marginLeft: "auto" }}>
                      {new Date(event.timestamp).toLocaleTimeString()}
                    </span>
                  </div>
                  <div style={{ fontSize: "12px", color: "var(--text)" }}>
                    {JSON.stringify(event.data, null, 2).slice(0, 300)}
                    {JSON.stringify(event.data).length > 300 ? "..." : ""}
                  </div>
                </div>
              ))}
              <div ref={eventsEndRef} />
            </div>
          )}
        </div>

        {/* Stream Status */}
        <div style={{
          marginTop: "12px",
          fontSize: "11px",
          color: "var(--text-muted)",
          display: "flex",
          justifyContent: "space-between",
        }}>
          <span>
            {streaming ? "🔴 Live" : "⚪ Disconnected"} • {events.length} events
          </span>
          <button
            className="btn btn-secondary"
            onClick={loadEventHistory}
            style={{ fontSize: "11px", padding: "2px 8px" }}
          >
            🔄 Refresh
          </button>
        </div>
      </section>
    </div>
  );
}
