import { useState } from "react";
import { ingestDocument, type IngestReport } from "../lib/api";

export default function IngestionPage() {
    const [path, setPath] = useState("");
    const [recursive, setRecursive] = useState(true);
    const [loading, setLoading] = useState(false);
    const [report, setReport] = useState<IngestReport | null>(null);
    const [error, setError] = useState<string | null>(null);

    const handleIngest = async () => {
        const targetPath = path.trim();
        if (!targetPath || loading) return;

        setLoading(true);
        setReport(null);
        setError(null);

        try {
            const res = await ingestDocument(targetPath, recursive);
            setReport(res.report);
        } catch (err) {
            setError(err instanceof Error ? err.message : "Ingestion failed");
        } finally {
            setLoading(false);
        }
    };

    const handleKeyDown = (e: React.KeyboardEvent) => {
        if (e.key === "Enter" && !e.shiftKey) {
            e.preventDefault();
            handleIngest();
        }
    };

    return (
        <>
            <div className="page-header">
                <div>
                    <div className="page-title">Ingestion</div>
                    <div className="page-subtitle">
                        Add files or directories to your vector database to inform Smart Chat responses
                    </div>
                </div>
            </div>

            <div className="page-body">
                <div className="card" style={{ marginBottom: 20 }}>
                    <div className="card-title">Ingest Documents</div>
                    <div className="card-subtitle" style={{ marginBottom: 12 }}>
                        Provide an absolute path to a file (e.g., .md, .py, .txt, .pdf) or a directory.
                    </div>

                    <div className="input-group" style={{ marginBottom: 16 }}>
                        <input
                            className="input"
                            placeholder="C:\path\to\your\file_or_directory..."
                            value={path}
                            onChange={(e) => setPath(e.target.value)}
                            onKeyDown={handleKeyDown}
                            disabled={loading}
                            id="ingest-path"
                        />
                        <button
                            className="btn btn-primary"
                            onClick={handleIngest}
                            disabled={loading || !path.trim()}
                            id="ingest-run"
                        >
                            {loading ? (
                                <>
                                    <span className="spinner" /> Ingesting...
                                </>
                            ) : (
                                "📥 Ingest"
                            )}
                        </button>
                    </div>

                    <div style={{ display: "flex", gap: 12, alignItems: "center" }}>
                        <label className="toggle-switch" title="Process directories recursively">
                            <input
                                type="checkbox"
                                checked={recursive}
                                onChange={(e) => setRecursive(e.target.checked)}
                                disabled={loading}
                            />
                            <span className="toggle-slider" />
                        </label>
                        <label style={{ cursor: "pointer", fontSize: 13, color: "var(--text-color)" }}>
                            Recursive (for directories)
                        </label>
                    </div>
                </div>

                {error && (
                    <div className="card" style={{ borderLeft: "4px solid var(--danger)", marginBottom: 20 }}>
                        <h4 style={{ margin: "0 0 8px 0", color: "var(--danger)" }}>Error</h4>
                        <div style={{ color: "var(--text-muted)", fontSize: 13, wordWrap: "break-word" }}>{error}</div>
                    </div>
                )}

                {report && (
                    <div className="card" style={{ borderLeft: "4px solid var(--success)", marginBottom: 20 }}>
                        <h4 style={{ margin: "0 0 12px 0", color: "var(--success)" }}>Ingestion Complete</h4>

                        <div className="stats-row" style={{ marginTop: 0 }}>
                            <div className="stat-card" style={{ background: "var(--bg-primary)" }}>
                                <div className="stat-value">{report.files_processed}</div>
                                <div className="stat-label">Files Processed</div>
                            </div>
                            <div className="stat-card" style={{ background: "var(--bg-primary)" }}>
                                <div className="stat-value">{report.chunks_created}</div>
                                <div className="stat-label">Chunks Indexed</div>
                            </div>
                        </div>

                        {report.errors && Array.isArray(report.errors) && report.errors.length > 0 && (
                            <div style={{ marginTop: 16 }}>
                                <h5 style={{ margin: "0 0 8px 0", color: "var(--danger)", fontSize: 12 }}>Skipped / Errors:</h5>
                                <ul style={{ margin: 0, paddingLeft: 20, fontSize: 12, color: "var(--text-muted)", wordWrap: "break-word" }}>
                                    {report.errors.map((err: any, i) => (
                                        <li key={i}>
                                            <strong>{err.file || "Unknown file"}</strong>: {err.error || JSON.stringify(err)}
                                        </li>
                                    ))}
                                </ul>
                            </div>
                        )}
                    </div>
                )}
            </div>
        </>
    );
}
