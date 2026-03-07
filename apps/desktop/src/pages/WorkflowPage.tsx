import { useState, useCallback } from "react";
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
import { runWorkflow } from "../lib/api";

const initialNodes: Node[] = [
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
        data: { label: "Summarize Code", config: { model: "local" } },
    },
    {
        id: "tool-1",
        type: "tool",
        position: { x: 550, y: 120 },
        data: { label: "Execute Command", config: { toolName: "toolExecCommand" } },
    },
];

const initialEdges: Edge[] = [
    { id: "e1-2", source: "trigger-1", target: "agent-1", animated: true },
    { id: "e2-3", source: "agent-1", target: "tool-1", animated: true },
];

export default function WorkflowPage() {
    const [nodes, setNodes] = useState<Node[]>(initialNodes);
    const [edges, setEdges] = useState<Edge[]>(initialEdges);
    const [selectedNode, setSelectedNode] = useState<Node | null>(null);

    const onNodesChange: OnNodesChange = useCallback(
        (changes) => setNodes((nds) => applyNodeChanges(changes, nds)),
        []
    );

    const onEdgesChange: OnEdgesChange = useCallback(
        (changes) => setEdges((eds) => applyEdgeChanges(changes, eds)),
        []
    );

    const onConnect: OnConnect = useCallback(
        (connection) => setEdges((eds) => addEdge({ ...connection, animated: true }, eds)),
        []
    );

    const onNodeClick = (_: React.MouseEvent, node: Node) => {
        setSelectedNode(node);
    };

    const onPaneClick = () => {
        setSelectedNode(null);
    };

    // Add a new node to the canvas
    const addNode = (type: "trigger" | "agent" | "tool", label: string) => {
        const newNode: Node = {
            id: `${type}-${Date.now()}`,
            type,
            position: { x: Math.random() * 200 + 100, y: Math.random() * 200 + 100 },
            data: { label, config: {} },
        };
        setNodes((nds) => [...nds, newNode]);
    };

    const handleRunWorkflow = async () => {
        // In a future step, this will serialize the local graph
        // and send it to the backend `/workflows/run` endpoint.
        alert("Running Workflow via Backend Exec Engine... (Implementation Pending)");
    };

    return (
        <div className="page-container" style={{ display: "flex", flexDirection: "column", height: "100%" }}>
            <header className="page-header" style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                <div>
                    <h2>Agentic Workflow Builder</h2>
                    <p className="page-subtitle">Visually wire triggers, agents, and tools to run autonomously.</p>
                </div>
                <button className="primary-button" onClick={handleRunWorkflow}>
                    ▶ Run Workflow
                </button>
            </header>

            <div style={{ display: "flex", flex: 1, gap: 16, marginTop: 16 }}>
                {/* Available Nodes Palette */}
                <div
                    className="card"
                    style={{ width: 220, display: "flex", flexDirection: "column", gap: 12 }}
                >
                    <h3 style={{ fontSize: 14, textTransform: "uppercase", color: "var(--text-muted)" }}>Node Palette</h3>

                    <button className="secondary-button" onClick={() => addNode("trigger", "Manual Trigger")} style={{ textAlign: "left" }}>
                        ⚡ Trigger Node
                    </button>
                    <button className="secondary-button" onClick={() => addNode("agent", "Custom Agent")} style={{ textAlign: "left" }}>
                        🤖 Agent Node
                    </button>
                    <button className="secondary-button" onClick={() => addNode("tool", "Local Tool")} style={{ textAlign: "left" }}>
                        🛠️ Tool Node
                    </button>
                </div>

                {/* React Flow Canvas */}
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

                {/* Properties Panel */}
                {selectedNode && (
                    <div className="card" style={{ width: 280, display: "flex", flexDirection: "column" }}>
                        <h3 style={{ fontSize: 16, marginBottom: 12 }}>Properties: {selectedNode.data.label as string}</h3>
                        <div style={{ background: "rgba(0,0,0,0.2)", padding: 12, borderRadius: 8, fontSize: 13, fontFamily: "monospace", whiteSpace: "pre-wrap" }}>
                            {JSON.stringify(selectedNode.data.config, null, 2)}
                        </div>

                        <p style={{ marginTop: 16, fontSize: 13, color: "var(--text-muted)" }}>
                            ID: {selectedNode.id} <br />
                            Type: {selectedNode.type}
                        </p>
                    </div>
                )}
            </div>
        </div>
    );
}
