/**
 * Agents Page - Expanded with A2A and Autonomous tabs
 *
 * Tabs:
 * - Agent Crew - Run Planner → Researcher → Synthesizer pipeline
 * - A2A Agents - Discover and delegate to Tier 1 agents
 * - Autonomous - Autonomous agent controls and event stream
 * - Execution Trace - View agent execution trace
 */

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
import A2AAgentsTab from "../components/agents/A2AAgentsTab";
import AutonomousAgentsTab from "../components/agents/AutonomousAgentsTab";
import AgentTraceViewer from "../components/agents/AgentTraceViewer";

type AgentsTab = 'crew' | 'a2a' | 'autonomous' | 'trace';

export default function AgentsPage() {
    const [activeTab, setActiveTab] = useState<AgentsTab>('crew');
    const [input, setInput] = useState("");
    const [model, setModel] = useState("local");
    const [loading, setLoading] = useState(false);
    const [traces, setTraces] = useState<TraceEvent[]>([]);
    const [result, setResult] = useState<AgentResult | null>(null);
    const [models, setModels] = useState<ModelInfo[]>([]);
    const [currentRunId, setCurrentRunId] = useState<string | null>(null);
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
            setCurrentRunId(res.run_id);

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
                run_id: "",
                agent_name: "system",
                event_type: "error",
                content: err instanceof Error ? err.message : "Unknown error",
                timestamp: new Date().toISOString(),
                metadata: {},
            };
            setTraces((prev) => [...prev, errorTrace]);
        } finally {
            setLoading(false);
        }
    };

    const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
        if (e.key === "Enter" && !e.shiftKey) {
            e.preventDefault();
            handleRun();
        }
    };

    return (
        <div style={{ padding: '20px', height: '100%', overflow: 'auto' }}>
            {/* Tabs */}
            <div style={{
                display: 'flex',
                gap: '8px',
                marginBottom: '24px',
                borderBottom: '1px solid var(--border)',
                paddingBottom: '12px',
            }}>
                <button
                    className={`btn ${activeTab === 'crew' ? 'btn-primary' : 'btn-secondary'}`}
                    onClick={() => setActiveTab('crew')}
                >
                    🎯 Agent Crew
                </button>
                <button
                    className={`btn ${activeTab === 'a2a' ? 'btn-primary' : 'btn-secondary'}`}
                    onClick={() => setActiveTab('a2a')}
                >
                    🤖 A2A Agents
                </button>
                <button
                    className={`btn ${activeTab === 'autonomous' ? 'btn-primary' : 'btn-secondary'}`}
                    onClick={() => setActiveTab('autonomous')}
                >
                    🔄 Autonomous
                </button>
                <button
                    className={`btn ${activeTab === 'trace' ? 'btn-primary' : 'btn-secondary'}`}
                    onClick={() => setActiveTab('trace')}
                >
                    📊 Execution Trace
                </button>
            </div>

            {/* Tab Content */}
            {activeTab === 'autonomous' && (
                <AutonomousAgentsTab />
            )}

            {activeTab === 'crew' && (
                <div>
                    <div style={{ marginBottom: '24px' }}>
                        <h3 style={{ margin: '0 0 8px 0' }}>Agent Crew</h3>
                        <p style={{ fontSize: '13px', color: 'var(--text-muted)', margin: 0 }}>
                            Run the Planner → Researcher → Synthesizer pipeline
                        </p>
                    </div>

                    {/* Input */}
                    <div style={{ marginBottom: '24px' }}>
                        <textarea
                            className="input"
                            placeholder="Describe your task or question..."
                            value={input}
                            onChange={(e) => setInput(e.target.value)}
                            onKeyDown={handleKeyDown}
                            disabled={loading}
                            rows={4}
                            style={{ width: '100%', resize: 'vertical' }}
                        />
                        <div style={{ display: 'flex', gap: '12px', marginTop: '12px' }}>
                            <button
                                className="btn btn-primary"
                                onClick={handleRun}
                                disabled={loading || !input.trim()}
                            >
                                {loading ? 'Running Agent...' : '🚀 Run Agent Crew'}
                            </button>
                            <select
                                className="input"
                                value={model}
                                onChange={(e) => setModel(e.target.value)}
                                disabled={loading}
                            >
                                {models.map((m) => (
                                    <option key={m.id} value={m.id}>
                                        {m.name || m.id}
                                    </option>
                                ))}
                            </select>
                        </div>
                    </div>

                    {/* Result */}
                    {result && (
                        <div style={{ marginBottom: '24px' }}>
                            <h4 style={{ margin: '0 0 12px 0' }}>Result</h4>
                            <div className="markdown-body" style={{
                                background: 'var(--bg-secondary)',
                                padding: '16px',
                                borderRadius: '8px',
                            }}>
                                {result.response}
                            </div>
                        </div>
                    )}

                    {/* Trace */}
                    {traces.length > 0 && (
                        <div>
                            <h4 style={{ margin: '0 0 12px 0' }}>Execution Trace</h4>
                            <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                                {traces.map((trace, i) => (
                                    <div
                                        key={i}
                                        style={{
                                            background: 'var(--bg-secondary)',
                                            padding: '12px',
                                            borderRadius: '8px',
                                            border: `1px solid var(--border)`,
                                        }}
                                    >
                                        <div style={{ fontSize: '11px', color: 'var(--text-muted)', marginBottom: '4px' }}>
                                            <span className="badge badge-accent">{trace.agent_name}</span>
                                            {' '}{trace.event_type} • {new Date(trace.timestamp).toLocaleTimeString()}
                                        </div>
                                        <div style={{ fontSize: '13px', whiteSpace: 'pre-wrap' }}>
                                            {trace.content}
                                        </div>
                                    </div>
                                ))}
                            </div>
                            <div ref={traceEndRef} />
                        </div>
                    )}
                </div>
            )}

            {activeTab === 'a2a' && <A2AAgentsTab />}

            {activeTab === 'trace' && <AgentTraceViewer runId={currentRunId} />}
        </div>
    );
}
