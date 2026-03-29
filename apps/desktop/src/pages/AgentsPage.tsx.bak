import { useState, useRef, useEffect } from "react";
import {
    runAgent,
    streamTrace,
    listModels,
    getActiveModel,
    type TraceEvent,
    type AgentResult,
    type ModelInfo,
} from "../lib/api";

export default function AgentsPage() {
    const [input, setInput] = useState("");
    const [model, setModel] = useState("local");
    const [loading, setLoading] = useState(false);
    const [traces, setTraces] = useState<TraceEvent[]>([]);
    const [result, setResult] = useState<AgentResult | null>(null);
    const [models, setModels] = useState<ModelInfo[]>([]);
    const traceEndRef = useRef<HTMLDivElement>(null);

    useEffect(() => {
        traceEndRef.current?.scrollIntoView({ behavior: "smooth" });
    }, [traces]);

    useEffect(() => {
        let mounted = true;
        const loadModels = async () => {
            try {
                const [modelData, activeData] = await Promise.all([
                    listModels(),
                    getActiveModel(),
                ]);
                if (!mounted) return;
                setModels(modelData.models || []);
                setModel(activeData.active_model || "local");
            } catch (err) {
                console.error("Failed to load models for agents page:", err);
            }
        };
        loadModels();
        return () => { mounted = false; };
    }, []);

    const handleRun = async () => {
        const text = input.trim();
        if (!text || loading) return;

        setLoading(true);
        setTraces([]);
        setResult(null);

        try {
            const res = await runAgent(text, model);
            setResult(res);

            const streamed: TraceEvent[] = [];
            try {
                for await (const event of streamTrace(res.run_id)) {
                    streamed.push(event);
                    setTraces([...streamed]);
                }
            } catch (streamErr) {
                const traceError: TraceEvent = {
                    run_id: res.run_id,
                    agent_name: "system",
                    event_type: "error",
                    content: streamErr instanceof Error ? streamErr.message : "Trace stream failed",
                    timestamp: new Date().toISOString(),
                    metadata: {},
                };
                setTraces((prev) => [...prev, traceError]);
            }

            if (streamed.length === 0) {
                // Fallback: still show the actual agent outputs if no trace events were emitted.
                setTraces([
                    {
                        run_id: res.run_id,
                        agent_name: "planner",
                        event_type: "output",
                        content: res.plan,
                        timestamp: new Date().toISOString(),
                        metadata: {},
                    },
                    {
                        run_id: res.run_id,
                        agent_name: "researcher",
                        event_type: "output",
                        content: res.research,
                        timestamp: new Date().toISOString(),
                        metadata: {},
                    },
                    {
                        run_id: res.run_id,
                        agent_name: "synthesizer",
                        event_type: "output",
                        content: res.response,
                        timestamp: new Date().toISOString(),
                        metadata: {},
                    },
                ]);
            }
        } catch (err) {
            const errorTrace: TraceEvent = {
                run_id: "error",
                agent_name: "system",
                event_type: "error",
                content: err instanceof Error ? err.message : "Agent run failed",
                timestamp: new Date().toISOString(),
                metadata: {},
            };
            setTraces([errorTrace]);
        } finally {
            setLoading(false);
        }
    };

    const handleKeyDown = (e: React.KeyboardEvent) => {
        if (e.key === "Enter" && !e.shiftKey) {
            e.preventDefault();
            handleRun();
        }
    };

    const getEventIcon = (type: string) => {
        switch (type) {
            case "thinking": return "💭";
            case "tool_call": return "🔧";
            case "tool_result": return "📋";
            case "output": return "✅";
            case "error": return "❌";
            default: return "📝";
        }
    };

    const getAgentColor = (name: string) => {
        switch (name) {
            case "planner": return "#818cf8";
            case "researcher": return "#60a5fa";
            case "synthesizer": return "#34d399";
            case "system": return "#94a3b8";
            default: return "#fbbf24";
        }
    };

    const selectedModel = models.find(m => m.id === model);
    const localModels = models.filter(m => m.is_local);
    const remoteGroups = models
        .filter(m => !m.is_local)
        .reduce<Record<string, ModelInfo[]>>((acc, m) => {
            const key = m.provider || "remote";
            if (!acc[key]) acc[key] = [];
            acc[key].push(m);
            return acc;
        }, {});

    return (
        <>
            <div className="page-header">
                <div>
                    <div className="page-title">Agents</div>
                    <div className="page-subtitle">
                        Run the multi-agent crew pipeline: Planner → Researcher → Synthesizer
                    </div>
                </div>
            </div>

            <div className="page-body">
                {/* Input */}
                <div className="card" style={{ marginBottom: 20 }}>
                    <div className="card-title">Run Agent Crew</div>
                    <div className="card-subtitle" style={{ marginBottom: 12 }}>
                        Send a complex query to the multi-agent pipeline for deep analysis
                    </div>

                    <div style={{ display: "flex", gap: 8, marginBottom: 12 }}>
                        <select
                            className="input"
                            value={model}
                            onChange={(e) => setModel(e.target.value)}
                            style={{ width: 160, flex: "none" }}
                        >
                            {localModels.length > 0 && (
                                <optgroup label="🖥️ Local">
                                    {localModels.map((m) => (
                                        <option key={m.id} value={m.id}>{m.name || m.id}</option>
                                    ))}
                                </optgroup>
                            )}
                            {Object.entries(remoteGroups).map(([provider, providerModels]) => (
                                <optgroup key={provider} label={`☁️ ${provider}`}>
                                    {providerModels.map((m) => (
                                        <option key={m.id} value={m.id}>{m.name || m.id}</option>
                                    ))}
                                </optgroup>
                            ))}
                            <option value="active">Active Model</option>
                        </select>
                    </div>

                    {selectedModel && (
                        <div className="card-subtitle" style={{ marginBottom: 8 }}>
                            {selectedModel.supports_tool_calls ? "Tool-calling enabled." : "Tool-calling may be routed to a compatible model."}
                            {selectedModel.requires_reasoning_echo ? " Reasoning echo continuity is enabled for this model." : ""}
                        </div>
                    )}

                    <div className="input-group">
                        <input
                            className="input"
                            placeholder="Ask the crew something complex..."
                            value={input}
                            onChange={(e) => setInput(e.target.value)}
                            onKeyDown={handleKeyDown}
                            disabled={loading}
                            id="agent-input"
                        />
                        <button
                            className="btn btn-primary"
                            onClick={handleRun}
                            disabled={loading || !input.trim()}
                            id="agent-run"
                        >
                            {loading ? (
                                <>
                                    <span className="spinner" /> Running...
                                </>
                            ) : (
                                "🚀 Run Crew"
                            )}
                        </button>
                    </div>
                </div>

                {/* Trace Timeline */}
                {traces.length > 0 && (
                    <>
                        <h3
                            style={{
                                fontSize: 13,
                                fontWeight: 600,
                                color: "var(--text-muted)",
                                textTransform: "uppercase",
                                letterSpacing: 0.5,
                                marginBottom: 12,
                            }}
                        >
                            Agent Execution Trace
                            {result && (
                                <span className="badge badge-accent" style={{ marginLeft: 8, textTransform: "none" }}>
                                    Run: {result.run_id}
                                </span>
                            )}
                        </h3>

                        <div className="trace-timeline">
                            {traces.map((t, i) => (
                                <div
                                    key={i}
                                    className={`trace-event ${t.event_type}`}
                                >
                                    <div className="trace-header">
                                        <span style={{ fontSize: 14 }}>{getEventIcon(t.event_type)}</span>
                                        <span
                                            className="trace-agent"
                                            style={{ color: getAgentColor(t.agent_name) }}
                                        >
                                            {t.agent_name}
                                        </span>
                                        <span className="trace-type">{t.event_type}</span>
                                    </div>
                                    <div className="trace-content">{t.content}</div>
                                    <div className="trace-time">
                                        {new Date(t.timestamp).toLocaleTimeString([], {
                                            hour: "2-digit",
                                            minute: "2-digit",
                                            second: "2-digit",
                                        })}
                                    </div>
                                </div>
                            ))}
                            <div ref={traceEndRef} />
                        </div>
                    </>
                )}

                {/* Empty State */}
                {traces.length === 0 && !loading && (
                    <div className="empty-state">
                        <div className="empty-state-icon">🤖</div>
                        <div className="empty-state-title">No Agent Runs Yet</div>
                        <div className="empty-state-text">
                            Submit a query above to trigger the Planner → Researcher →
                            Synthesizer pipeline. You'll see the recorded trace of each agent's
                            work.
                        </div>
                    </div>
                )}
            </div>
        </>
    );
}
