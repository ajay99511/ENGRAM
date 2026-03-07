import { useState, useRef, useEffect } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import {
    chatSmart,
    chatPlain,
    chatStream,
    listModels,
    getActiveModel,
    getActiveContext,
    clearActiveContext,
    type ChatResponse,
    type ModelInfo,
} from "../lib/api";

interface Message {
    role: "user" | "assistant";
    content: string;
    model?: string;
    memoryUsed?: boolean;
    timestamp: Date;
}

export default function ChatPage() {
    const [messages, setMessages] = useState<Message[]>([]);
    const [input, setInput] = useState("");
    const [loading, setLoading] = useState(false);
    const [smartMode, setSmartMode] = useState(true);
    const [streamMode, setStreamMode] = useState(false);

    // Model state
    const [availableModels, setAvailableModels] = useState<ModelInfo[]>([]);
    const [selectedModelId, setSelectedModelId] = useState("");
    const [isFetchingModels, setIsFetchingModels] = useState(false);

    // Active Context state
    const [activeContext, setActiveContext] = useState<any>(null);

    const messagesEndRef = useRef<HTMLDivElement>(null);
    const textareaRef = useRef<HTMLTextAreaElement>(null);

    // Fetch models and active context on mount
    useEffect(() => {
        let mounted = true;
        const fetchModelsAndContext = async () => {
            setIsFetchingModels(true);
            try {
                const [modelData, activeData, contextData] = await Promise.all([
                    listModels(),
                    getActiveModel(),
                    getActiveContext()
                ]);
                if (mounted) {
                    setAvailableModels(modelData.models || []);
                    setSelectedModelId(activeData.active_model || "local");
                    if (Object.keys(contextData).length > 0) {
                        setActiveContext(contextData);
                    }
                }
            } catch (err) {
                console.error("Failed to fetch initial data for chat:", err);
            } finally {
                if (mounted) setIsFetchingModels(false);
            }
        };
        fetchModelsAndContext();
        return () => { mounted = false; };
    }, []);

    // Auto-scroll
    useEffect(() => {
        messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
    }, [messages]);

    // Auto-resize textarea
    useEffect(() => {
        if (textareaRef.current) {
            textareaRef.current.style.height = 'auto';
            const scrollHeight = textareaRef.current.scrollHeight;
            textareaRef.current.style.height = `${Math.min(scrollHeight, 150)}px`;
        }
    }, [input]);

    const handleSend = async () => {
        const text = input.trim();
        if (!text || loading) return;

        const userMsg: Message = {
            role: "user",
            content: text,
            timestamp: new Date(),
        };
        setMessages((prev) => [...prev, userMsg]);
        setInput("");
        setLoading(true);

        try {
            if (streamMode) {
                // SSE streaming mode
                const streamingMsg: Message = {
                    role: "assistant",
                    content: "",
                    model: selectedModelId,
                    timestamp: new Date(),
                };
                setMessages((prev) => [...prev, streamingMsg]);

                for await (const chunk of chatStream(text, selectedModelId)) {
                    setMessages((prev) => {
                        const updated = [...prev];
                        const last = updated[updated.length - 1];
                        if (last.role === "assistant") {
                            updated[updated.length - 1] = {
                                ...last,
                                content: last.content + chunk,
                            };
                        }
                        return updated;
                    });
                }
            } else {
                // Regular or Smart mode
                const fn = smartMode ? chatSmart : chatPlain;
                const resp: ChatResponse = await fn(text, selectedModelId);
                const assistantMsg: Message = {
                    role: "assistant",
                    content: resp.response,
                    model: resp.model_used,
                    memoryUsed: resp.memory_used,
                    timestamp: new Date(),
                };
                setMessages((prev) => [...prev, assistantMsg]);
            }
        } catch (err) {
            const errorMsg: Message = {
                role: "assistant",
                content: `⚠️ Error: ${err instanceof Error ? err.message : "Failed to get response"}`,
                timestamp: new Date(),
            };
            setMessages((prev) => [...prev, errorMsg]);
        } finally {
            setLoading(false);
        }
    };

    const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
        if (e.key === "Enter" && !e.shiftKey) {
            e.preventDefault();
            handleSend();
        }
    };

    const copyToClipboard = async (text: string) => {
        try {
            await navigator.clipboard.writeText(text);
        } catch (err) {
            console.error('Failed to copy text: ', err);
        }
    };

    // Group models for the dropdown
    const localModels = availableModels.filter(m => m.is_local);
    const geminiModels = availableModels.filter(m => !m.is_local && m.provider === 'gemini');
    const otherRemote = availableModels.filter(m => !m.is_local && m.provider !== 'gemini');

    return (
        <div className="chat-container">
            {/* Header controls (New Chat) */}
            <div style={{
                padding: '12px 28px',
                borderBottom: '1px solid var(--border)',
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
                background: 'var(--bg-secondary)'
            }}>
                <div style={{ fontSize: 16, fontWeight: 600 }}>Chat Session</div>
                <button
                    className="btn btn-secondary btn-sm"
                    onClick={() => setMessages([])}
                    title="Clear Conversation"
                    disabled={messages.length === 0}
                >
                    🆕 New Chat
                </button>
            </div>

            {/* Messages Area */}
            <div className="chat-messages">
                {messages.length === 0 && (
                    <div className="empty-state">
                        <div className="empty-state-icon">💬</div>
                        <div className="empty-state-title">Start a Conversation</div>
                        <div className="empty-state-text">
                            Ask anything — PersonalAssist uses your memories and documents for
                            context-aware responses.
                        </div>
                    </div>
                )}

                {messages.map((msg, i) => (
                    <div key={i} className={`message ${msg.role}`}>
                        {msg.role === "assistant" ? (
                            <div className="markdown-body">
                                <ReactMarkdown remarkPlugins={[remarkGfm]}>
                                    {msg.content}
                                </ReactMarkdown>
                            </div>
                        ) : (
                            <div>{msg.content}</div>
                        )}
                        <div className="message-meta" style={{ justifyContent: msg.role === 'user' ? 'flex-end' : 'flex-start' }}>
                            {msg.role === "assistant" && msg.model && (
                                <span className="badge badge-accent">{msg.model}</span>
                            )}
                            {msg.memoryUsed && (
                                <span className="badge badge-success">🧠 Memory</span>
                            )}
                            <span>
                                {msg.timestamp.toLocaleTimeString([], {
                                    hour: "2-digit",
                                    minute: "2-digit",
                                })}
                            </span>
                            {msg.role === "assistant" && (
                                <button
                                    onClick={() => copyToClipboard(msg.content)}
                                    style={{
                                        background: 'transparent', border: 'none', color: 'inherit',
                                        cursor: 'pointer', padding: '0 4px', fontSize: 14,
                                        opacity: 0.7, transform: 'translateY(-1px)'
                                    }}
                                    title="Copy response"
                                >
                                    📋
                                </button>
                            )}
                        </div>
                    </div>
                ))}

                {loading && !streamMode && (
                    <div className="typing-indicator">
                        <span /><span /><span />
                    </div>
                )}
                <div ref={messagesEndRef} />
            </div>

            {/* Active Context Banner */}
            {activeContext && (
                <div style={{
                    margin: '8px 16px',
                    padding: '8px 12px',
                    background: 'rgba(79, 172, 254, 0.1)',
                    border: '1px solid rgba(79, 172, 254, 0.3)',
                    borderRadius: '8px',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                    fontSize: '13px'
                }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                        <span style={{ color: 'var(--accent-color)' }}>◉ Active Context Detected</span>
                        <span style={{ color: 'var(--text-muted)' }}>
                            {activeContext.file_path && `File: ${activeContext.file_path.split(/[/\\]/).pop()} `}
                            {activeContext.terminal_error && `(Terminal Error)`}
                        </span>
                    </div>
                    <button
                        onClick={async () => {
                            await clearActiveContext();
                            setActiveContext(null);
                        }}
                        style={{ background: 'transparent', border: 'none', color: 'var(--text-muted)', cursor: 'pointer', fontSize: '12px' }}
                    >
                        ✕ Clear
                    </button>
                </div>
            )}

            {/* Input Bar */}
            <div className="chat-input-bar">
                <div className="chat-controls">
                    <label className="toggle-switch" title="Smart Mode (RAG-enhanced)">
                        <input
                            type="checkbox"
                            checked={smartMode}
                            onChange={(e) => {
                                setSmartMode(e.target.checked);
                                if (e.target.checked) setStreamMode(false);
                            }}
                        />
                        <span className="toggle-slider" />
                    </label>
                    <label style={{ cursor: "pointer" }}>Smart</label>

                    <div style={{ width: 1, height: 16, background: "var(--border)", margin: "0 4px" }} />

                    <label className="toggle-switch" title="Streaming Mode">
                        <input
                            type="checkbox"
                            checked={streamMode}
                            onChange={(e) => {
                                setStreamMode(e.target.checked);
                                if (e.target.checked) setSmartMode(false);
                            }}
                        />
                        <span className="toggle-slider" />
                    </label>
                    <label style={{ cursor: "pointer" }}>Stream</label>

                    <div style={{ flex: 1 }} />

                    {isFetchingModels ? (
                        <div style={{ fontSize: 12, color: 'var(--text-muted)' }}>Loading models...</div>
                    ) : (
                        <select
                            className="input"
                            value={selectedModelId}
                            onChange={(e) => setSelectedModelId(e.target.value)}
                            style={{ width: 'auto', minWidth: 180, flex: "none", padding: '6px 28px 6px 10px' }}
                        >
                            {localModels.length > 0 && (
                                <optgroup label="🖥️ Local Models">
                                    {localModels.map(m => (
                                        <option key={m.id} value={m.id}>{m.name || m.id}</option>
                                    ))}
                                </optgroup>
                            )}
                            {geminiModels.length > 0 && (
                                <optgroup label="☁️ Gemini Models">
                                    {geminiModels.map(m => (
                                        <option key={m.id} value={m.id}>{m.name || m.id}</option>
                                    ))}
                                </optgroup>
                            )}
                            {otherRemote.length > 0 && (
                                <optgroup label="🌐 Other Remote">
                                    {otherRemote.map(m => (
                                        <option key={m.id} value={m.id}>{m.name || m.id}</option>
                                    ))}
                                </optgroup>
                            )}
                        </select>
                    )}
                </div>

                <div className="input-group" style={{ alignItems: 'flex-end', background: 'var(--bg-input)', borderRadius: 'var(--radius-md)', border: '1px solid var(--border)', padding: '2px' }}>
                    <textarea
                        ref={textareaRef}
                        className="input"
                        placeholder="Type a message... (Shift+Enter for new line)"
                        value={input}
                        onChange={(e) => setInput(e.target.value)}
                        onKeyDown={handleKeyDown}
                        disabled={loading}
                        id="chat-input"
                        rows={1}
                        style={{
                            resize: 'none',
                            background: 'transparent',
                            border: 'none',
                            maxHeight: 150,
                            padding: '10px 14px',
                            minHeight: 40
                        }}
                    />
                    <button
                        className="btn btn-primary"
                        onClick={handleSend}
                        disabled={loading || !input.trim()}
                        id="chat-send"
                        style={{ margin: '6px' }}
                    >
                        {loading ? <span className="spinner" /> : "Send"}
                    </button>
                </div>
            </div>
        </div>
    );
}
