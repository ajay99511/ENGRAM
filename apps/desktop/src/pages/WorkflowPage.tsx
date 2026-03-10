import { useEffect, useState } from "react";
import {
  ReactFlow,
  Controls,
  Background,
  applyNodeChanges,
  applyEdgeChanges,
  addEdge,
  type Node,
  type Edge,
  type OnNodesChange,
  type OnEdgesChange,
  type OnConnect,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import { nodeTypes } from "./WorkflowNodes";
import { runWorkflow, type WorkflowRunResult } from "../lib/api";

type WorkflowNodeData = {
  label: string;
  config?: Record<string, unknown>;
};

const initialNodes: Node<WorkflowNodeData>[] = [
  {
    id: "trigger-1",
    type: "trigger",
    position: { x: 50, y: 100 },
    data: { label: "Start Flow", config: { type: "manual" } },
  },
  {
    id: "agent-1",
    type: "agent",
    position: { x: 300, y: 80 },
    data: {
      label: "Summarize Context",
      config: {
        model: "local",
        prompt: "Summarize the workflow context and explain the next best action.",
      },
    },
  },
  {
    id: "tool-1",
    type: "tool",
    position: { x: 550, y: 120 },
    data: {
      label: "Run Identity Check",
      config: { toolName: "toolExecCommand", command: "whoami", timeout: 30 },
    },
  },
];

const initialEdges: Edge[] = [
  { id: "e1-2", source: "trigger-1", target: "agent-1", animated: true },
  { id: "e2-3", source: "agent-1", target: "tool-1", animated: true },
];

export default function WorkflowPage() {
  const [nodes, setNodes] = useState<Node<WorkflowNodeData>[]>(initialNodes);
  const [edges, setEdges] = useState<Edge[]>(initialEdges);
  const [selectedNode, setSelectedNode] = useState<Node<WorkflowNodeData> | null>(null);
  const [configDraft, setConfigDraft] = useState("{}");
  const [configError, setConfigError] = useState("");
  const [runResult, setRunResult] = useState<WorkflowRunResult | null>(null);
  const [runError, setRunError] = useState("");
  const [isRunning, setIsRunning] = useState(false);

  useEffect(() => {
    if (!selectedNode) {
      setConfigDraft("{}");
      setConfigError("");
      return;
    }
    setConfigDraft(JSON.stringify(selectedNode.data.config ?? {}, null, 2));
    setConfigError("");
  }, [selectedNode]);

  const onNodesChange: OnNodesChange = (changes) => {
    setNodes((current) => applyNodeChanges(changes, current) as Node<WorkflowNodeData>[]);
  };

  const onEdgesChange: OnEdgesChange = (changes) => {
    setEdges((current) => applyEdgeChanges(changes, current) as Edge[]);
  };

  const onConnect: OnConnect = (connection) => {
    setEdges((current) => addEdge({ ...connection, animated: true }, current));
  };

  const onNodeClick = (_event: React.MouseEvent, node: Node<WorkflowNodeData>) => {
    setSelectedNode(node);
  };

  const onPaneClick = () => {
    setSelectedNode(null);
  };

  const addNode = (type: "trigger" | "agent" | "tool", label: string) => {
    const defaultConfig =
      type === "trigger"
        ? { type: "manual" }
        : type === "agent"
          ? { model: "local", prompt: "Describe what this workflow step should accomplish." }
          : { toolName: "toolExecCommand", command: "whoami", timeout: 30 };

    const newNode: Node<WorkflowNodeData> = {
      id: `${type}-${Date.now()}`,
      type,
      position: { x: Math.random() * 200 + 100, y: Math.random() * 200 + 100 },
      data: { label, config: defaultConfig },
    };
    setNodes((current) => [...current, newNode]);
  };

  const updateSelectedNode = (updater: (node: Node<WorkflowNodeData>) => Node<WorkflowNodeData>) => {
    if (!selectedNode) return;

    setNodes((current) =>
      current.map((node) => (node.id === selectedNode.id ? updater(node) : node))
    );
    setSelectedNode((current) => (current ? updater(current) : current));
  };

  const handleSaveNodeConfig = () => {
    if (!selectedNode) return;

    try {
      const parsed = JSON.parse(configDraft) as Record<string, unknown>;
      updateSelectedNode((node) => ({
        ...node,
        data: {
          ...node.data,
          config: parsed,
        },
      }));
      setConfigError("");
    } catch (error) {
      setConfigError(error instanceof Error ? error.message : "Invalid JSON");
    }
  };

  const handleLabelChange = (label: string) => {
    updateSelectedNode((node) => ({
      ...node,
      data: {
        ...node.data,
        label,
      },
    }));
  };

  const handleRunWorkflow = async () => {
    setIsRunning(true);
    setRunError("");
    setRunResult(null);

    try {
      const result = await runWorkflow({ nodes, edges });
      setRunResult(result);
      if (!result.success && result.error) {
        setRunError(result.error);
      }
    } catch (error) {
      setRunError(error instanceof Error ? error.message : "Workflow execution failed");
    } finally {
      setIsRunning(false);
    }
  };

  return (
    <div className="page-container" style={{ display: "flex", flexDirection: "column", height: "100%" }}>
      <header className="page-header" style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <div>
          <h2>Agentic Workflow Builder</h2>
          <p className="page-subtitle">Visually wire triggers, agents, and tools to run autonomously.</p>
        </div>
        <button className="primary-button" onClick={handleRunWorkflow} disabled={isRunning}>
          {isRunning ? "Running..." : "Run Workflow"}
        </button>
      </header>

      {runError && (
        <div className="card" style={{ marginTop: 16, borderLeft: "4px solid var(--error)" }}>
          <div style={{ color: "var(--error)", fontSize: 13 }}>{runError}</div>
        </div>
      )}

      {runResult && (
        <div className="card" style={{ marginTop: 16 }}>
          <div className="card-title">Latest Run</div>
          <div className="card-subtitle" style={{ marginBottom: 12 }}>
            {runResult.success ? "Workflow completed successfully." : "Workflow stopped before completion."}
          </div>
          <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
            {(runResult.trace ?? []).map((entry) => (
              <div
                key={entry.node_id}
                style={{
                  padding: 12,
                  borderRadius: 10,
                  background: "var(--bg-secondary)",
                  border: "1px solid var(--border)",
                }}
              >
                <div style={{ fontSize: 12, fontWeight: 600, marginBottom: 6 }}>{entry.node_id}</div>
                <pre style={{ margin: 0, whiteSpace: "pre-wrap", fontSize: 12 }}>
                  {JSON.stringify(entry.error ? { error: entry.error } : entry.result, null, 2)}
                </pre>
              </div>
            ))}
          </div>
        </div>
      )}

      <div style={{ display: "flex", flex: 1, gap: 16, marginTop: 16, minHeight: 0 }}>
        <div className="card" style={{ width: 220, display: "flex", flexDirection: "column", gap: 12 }}>
          <h3 style={{ fontSize: 14, textTransform: "uppercase", color: "var(--text-muted)" }}>Node Palette</h3>

          <button className="secondary-button" onClick={() => addNode("trigger", "Manual Trigger")} style={{ textAlign: "left" }}>
            Trigger Node
          </button>
          <button className="secondary-button" onClick={() => addNode("agent", "Custom Agent")} style={{ textAlign: "left" }}>
            Agent Node
          </button>
          <button className="secondary-button" onClick={() => addNode("tool", "Local Tool")} style={{ textAlign: "left" }}>
            Tool Node
          </button>
        </div>

        <div style={{ flex: 1, position: "relative", borderRadius: 12, overflow: "hidden", border: "1px solid var(--border-color)" }}>
          <ReactFlow
            nodes={nodes}
            edges={edges}
            onNodesChange={onNodesChange}
            onEdgesChange={onEdgesChange}
            onConnect={onConnect}
            onNodeClick={onNodeClick}
            onPaneClick={onPaneClick}
            nodeTypes={nodeTypes}
            fitView
            style={{ background: "#111" }}
          >
            <Controls />
            <Background color="#333" gap={16} />
          </ReactFlow>
        </div>

        {selectedNode && (
          <div className="card" style={{ width: 320, display: "flex", flexDirection: "column", gap: 12 }}>
            <h3 style={{ fontSize: 16, margin: 0 }}>Properties</h3>
            <label style={{ fontSize: 12, color: "var(--text-muted)" }}>Label</label>
            <input
              className="input"
              value={String(selectedNode.data.label ?? "")}
              onChange={(event) => handleLabelChange(event.target.value)}
            />

            <label style={{ fontSize: 12, color: "var(--text-muted)" }}>Config JSON</label>
            <textarea
              className="input"
              rows={12}
              value={configDraft}
              onChange={(event) => setConfigDraft(event.target.value)}
              style={{ fontFamily: "var(--font-mono)", resize: "vertical" }}
            />
            {configError && <div style={{ color: "var(--error)", fontSize: 12 }}>{configError}</div>}
            <button className="btn btn-primary" onClick={handleSaveNodeConfig}>
              Save Node Config
            </button>

            <div style={{ fontSize: 12, color: "var(--text-muted)" }}>
              ID: {selectedNode.id}
            </div>
            <div style={{ fontSize: 12, color: "var(--text-muted)" }}>
              Type: {selectedNode.type}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
