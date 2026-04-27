import React, { useState } from "react";

interface ToolCallProps {
  toolName: string;
  args: Record<string, any>;
  result?: any;
  status: "pending" | "success" | "error";
}

export const ToolCall: React.FC<ToolCallProps> = ({ 
  toolName, 
  args, 
  result, 
  status 
}) => {
  const [expanded, setExpanded] = useState(false);

  return (
    <div className={`card tool-call-card ${status}`} style={{ margin: "8px 0", padding: "12px" }}>
      <div 
        className="trace-header" 
        style={{ cursor: "pointer", display: "flex", alignItems: "center", gap: "8px" }}
        onClick={() => setExpanded(!expanded)}
      >
        <span className={`status-dot ${status === 'pending' ? '' : (status === 'success' ? 'online' : 'offline')}`} />
        <span className="trace-agent" style={{ color: "var(--info)" }}>Using Tool: {toolName}</span>
        <span className="badge badge-info btn-sm" style={{ marginLeft: "auto" }}>
          {expanded ? "Hide Details" : "Show Details"}
        </span>
      </div>

      {expanded && (
        <div style={{ marginTop: "12px", borderTop: "1px solid var(--border)", paddingTop: "12px" }}>
          <div className="card-title" style={{ fontSize: "12px" }}>Arguments</div>
          <pre className="tools-code-block">{JSON.stringify(args, null, 2)}</pre>
          
          {result && (
            <>
              <div className="card-title" style={{ fontSize: "12px", marginTop: "12px" }}>Result</div>
              <pre className="tools-code-block">{typeof result === 'string' ? result : JSON.stringify(result, null, 2)}</pre>
            </>
          )}
        </div>
      )}
    </div>
  );
};
