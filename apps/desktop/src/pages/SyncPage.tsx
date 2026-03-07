import { useState, useEffect } from "react";
import { getSyncStatus, triggerSync, type SyncStatus } from "../lib/api";

export default function SyncPage() {
    const [status, setStatus] = useState<SyncStatus | null>(null);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState("");
    const [successMessage, setSuccessMessage] = useState("");

    const fetchStatus = async () => {
        try {
            const data = await getSyncStatus();
            setStatus(data);
        } catch (err) {
            setError(err instanceof Error ? err.message : String(err));
        }
    };

    useEffect(() => {
        fetchStatus();
    }, []);

    const handleForceSync = async () => {
        setLoading(true);
        setError("");
        setSuccessMessage("");
        try {
            const res = await triggerSync();
            setSuccessMessage(res.message || "Manual sync triggered successfully.");
            await fetchStatus();
        } catch (err) {
            setError(err instanceof Error ? err.message : String(err));
        } finally {
            setLoading(false);
        }
    };

    const formatTime = (ms: number | null) => {
        if (!ms) return "Never";
        return new Date(ms).toLocaleString();
    };

    return (
        <div className="page-container" style={{ maxWidth: 800, margin: "0 auto", padding: "40px 20px" }}>
            <h1 style={{ fontSize: 32, fontWeight: 700, marginBottom: 8 }}>P2P Sync Hub</h1>
            <p style={{ color: "var(--text-muted)", fontSize: 16, marginBottom: 40 }}>
                Manage your cross-device synchronization. PersonalAssist uses a file-based sync architecture.
                Point a tool like Syncthing or Dropbox at <code>~/.personalassist/</code> to sync your Brain across devices.
            </p>

            {error && (
                <div style={{ background: "rgba(255, 60, 60, 0.1)", color: "var(--color-error)", padding: 16, borderRadius: 8, marginBottom: 24, border: "1px solid rgba(255, 60, 60, 0.3)" }}>
                    ⚠️ {error}
                </div>
            )}
            {successMessage && (
                <div style={{ background: "rgba(60, 255, 120, 0.1)", color: "#3cff78", padding: 16, borderRadius: 8, marginBottom: 24, border: "1px solid rgba(60, 255, 120, 0.3)" }}>
                    ✅ {successMessage}
                </div>
            )}

            <div style={{ background: "var(--card-bg)", border: "1px solid var(--border)", borderRadius: 12, overflow: "hidden" }}>
                <div style={{ padding: "24px 32px", borderBottom: "1px solid var(--border)", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                    <div>
                        <h2 style={{ fontSize: 20, fontWeight: 600, margin: 0 }}>Sync Status</h2>
                        <div style={{ fontSize: 14, color: "var(--text-muted)", marginTop: 4 }}>
                            Last Automated Snapshot: <strong style={{ color: "white" }}>{formatTime(status?.last_sync ?? null)}</strong>
                        </div>
                    </div>
                    <div>
                        <button
                            className="btn btn-primary"
                            onClick={handleForceSync}
                            disabled={loading}
                            style={{
                                padding: "10px 20px",
                                display: "flex",
                                alignItems: "center",
                                gap: "8px",
                                ...(loading ? { opacity: 0.7, cursor: "wait" } : {})
                            }}
                        >
                            {loading ? <span className="spinner" style={{ borderColor: 'rgba(255,255,255,0.3)', borderTopColor: 'white' }} /> : "🔄"}
                            {loading ? "Exporting Data..." : "Force Snapshot Export"}
                        </button>
                    </div>
                </div>

                <div style={{ padding: "32px", background: "rgba(0,0,0,0.1)" }}>
                    <h3 style={{ fontSize: 14, textTransform: "uppercase", letterSpacing: 1, color: "var(--text-muted)", marginBottom: 16 }}>Available Snapshot Files</h3>
                    {status?.snapshots && status.snapshots.length > 0 ? (
                        <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
                            {status.snapshots.map(snap => (
                                <div key={snap} style={{ padding: "12px 16px", background: "var(--bg-primary)", border: "1px solid var(--border)", borderRadius: 8, fontSize: 14, display: "flex", alignItems: "center", gap: 12 }}>
                                    <span style={{ fontSize: 18 }}>📦</span>
                                    <span style={{ fontFamily: "monospace", color: "var(--accent-color)" }}>{snap}</span>
                                </div>
                            ))}
                        </div>
                    ) : (
                        <div style={{ color: "var(--text-muted)", fontStyle: "italic" }}>No snapshots found. Click Force Snapshot above to trigger an export.</div>
                    )}
                </div>
            </div>

            <div style={{ marginTop: 40, padding: 24, background: "rgba(79, 172, 254, 0.1)", borderRadius: 12, border: "1px solid rgba(79, 172, 254, 0.2)" }}>
                <h3 style={{ fontSize: 16, color: "var(--accent-color)", margin: "0 0 12px 0", display: "flex", alignItems: "center", gap: 8 }}>
                    💡 How it works
                </h3>
                <ol style={{ margin: 0, paddingLeft: 20, color: "var(--text-secondary)", lineHeight: 1.6 }}>
                    <li><strong style={{ color: "white" }}>Export:</strong> The backend automatically creates immutable snapshot files in <code>~/.personalassist/snapshots/</code> every hour.</li>
                    <li><strong style={{ color: "white" }}>Sync:</strong> You point an external sync tool (Syncthing, Nextcloud, Resilio) at the <code>~/.personalassist</code> directory.</li>
                    <li><strong style={{ color: "white" }}>Restore:</strong> When PersonalAssist boots, if it detects a newer snapshot file than its current database (e.g. pushed from another machine), it seamlessly ingests it into Qdrant.</li>
                </ol>
            </div>
        </div>
    );
}
