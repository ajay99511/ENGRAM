import { Handle, Position, type NodeProps } from "@xyflow/react";

const nodeStyle = {
    padding: "16px",
    borderRadius: "12px",
    border: "1px solid rgba(255,255,255,0.08)",
    background: "rgba(30, 30, 35, 0.85)",
    backdropFilter: "blur(12px)",
    WebkitBackdropFilter: "blur(12px)",
    color: "white",
    minWidth: "160px",
    boxShadow: "0 8px 32px rgba(0,0,0,0.4)",
    fontSize: "14px",
    transition: "transform 0.2s ease, box-shadow 0.2s ease",
};

const handleStyle = {
    background: "#555",
    width: "8px",
    height: "8px",
    border: "2px solid #222",
};

// ── Trigger Node ──
export function TriggerNode({ data }: NodeProps) {
    const d = data as any;
    return (
        <div style={{ ...nodeStyle, borderTop: "4px solid var(--accent-color, #4facfe)" }}>
            <div style={{ fontWeight: 600, marginBottom: "4px" }}>⚡ {d.label as string}</div>
            <div style={{ fontSize: "12px", color: "var(--text-muted)" }}>
                {d.config?.type === "manual" ? "Manual / API" : "Scheduled"}
            </div>
            <Handle type="source" position={Position.Right} style={handleStyle} />
        </div>
    );
}

// ── Agent Node ──
export function AgentNode({ data }: NodeProps) {
    const d = data as any;
    return (
        <div style={{ ...nodeStyle, borderTop: "4px solid #b721ff" }}>
            <Handle type="target" position={Position.Left} style={handleStyle} />
            <div style={{ fontWeight: 600, marginBottom: "4px" }}>🤖 {d.label as string}</div>
            <div style={{ fontSize: "12px", color: "var(--text-muted)" }}>
                Model: {d.config?.model || "local"}
            </div>
            <Handle type="source" position={Position.Right} style={handleStyle} />
        </div>
    );
}

// ── Tool Node ──
export function ToolNode({ data }: NodeProps) {
    const d = data as any;
    return (
        <div style={{ ...nodeStyle, borderTop: "4px solid #43e97b" }}>
            <Handle type="target" position={Position.Left} style={handleStyle} />
            <div style={{ fontWeight: 600, marginBottom: "4px" }}>🛠️ {d.label as string}</div>
            <div style={{ fontSize: "12px", color: "var(--text-muted)" }}>
                {d.config?.toolName || "Generic Tool"}
            </div>
            <Handle type="source" position={Position.Right} style={handleStyle} />
        </div>
    );
}

export const nodeTypes = {
    trigger: TriggerNode,
    agent: AgentNode,
    tool: ToolNode,
};
