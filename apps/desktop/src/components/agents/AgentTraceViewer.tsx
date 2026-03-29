/**
 * Agent Trace Viewer Component
 * 
 * Wraps the AgentTrace component for use in AgentsPage tabs.
 */

import AgentTrace from '../AgentTrace';

interface AgentTraceViewerProps {
  runId: string | null;
}

export default function AgentTraceViewer({ runId }: AgentTraceViewerProps) {
  if (!runId) {
    return (
      <div className="empty-state">
        <div className="empty-state-icon">📊</div>
        <div className="empty-state-title">No Active Trace</div>
        <div className="empty-state-text">
          Run an agent to see the execution trace
        </div>
      </div>
    );
  }

  return (
    <div>
      <div style={{ marginBottom: '16px' }}>
        <h3 style={{ margin: 0 }}>Execution Trace</h3>
        <p style={{ fontSize: '13px', color: 'var(--text-muted)', margin: '0' }}>
          Real-time view of agent execution (Planner → Researcher → Synthesizer)
        </p>
      </div>
      <AgentTrace runId={runId} />
    </div>
  );
}
