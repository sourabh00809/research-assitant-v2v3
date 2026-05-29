"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import useSWR from "swr";
import {
  ReactFlow,
  Background,
  Controls,
  MiniMap,
  useNodesState,
  useEdgesState,
  type Node,
  type Edge,
  MarkerType,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import type { Project } from "../../../../lib/api";
import { api } from "../../../../lib/api";
import { useAuth } from "@clerk/nextjs";
import { Panel, LoadingSpinner } from "../../../../components/ui";
import SidebarLayout from "../../../../components/SidebarLayout";

type GraphNode = {
  id: string;
  label?: string;
  kind?: string;
  x?: number;
  y?: number;
};

type GraphEdge = {
  id?: string;
  source: string;
  target: string;
  label?: string;
};

type GraphData = {
  nodes: GraphNode[];
  edges: GraphEdge[];
};

const NODE_COLORS: Record<string, string> = {
  question: "#6366f1",
  brief: "#059669",
  evidence: "#d97706",
  paper: "#2563eb",
  memory: "#7c3aed",
  plan: "#dc2626",
  hypothesis: "#0891b2",
  gap: "#9333ea",
};

export default function GraphPage() {
  const params = useParams();
  const router = useRouter();
  const { isLoaded, isSignedIn } = useAuth();
  const projectId = params.id as string;
  const { data: projects, isLoading: projectsLoading } = useSWR<Project[]>("/api/v1/projects", api);
  const [graphData, setGraphData] = useState<GraphData | null>(null);
  const [graphError, setGraphError] = useState("");
  const [selectedNode, setSelectedNode] = useState<Node | null>(null);

  const project = projects?.find((p) => p.id === projectId);

  useEffect(() => {
    if (!projectId) return;
    api<GraphData>(`/api/projects/${projectId}/graph`).then(setGraphData).catch((err) => { setGraphError(err instanceof Error ? err.message : "Failed to load graph"); setGraphData({ nodes: [], edges: [] }); });
  }, [projectId]);

  const { nodes: initialNodes, edges: initialEdges } = useMemo(() => {
    if (!graphData?.nodes) return { nodes: [], edges: [] };
    const nodes: Node[] = graphData.nodes.map((n: any, i: number) => ({
      id: n.id,
      type: "default",
      position: { x: n.x ?? ((i % 5) * 200), y: n.y ?? (Math.floor(i / 5) * 120) },
      data: { label: n.label || n.id, kind: n.kind },
      style: {
        background: NODE_COLORS[n.kind] || "#64748b",
        color: "#fff",
        border: "none",
        borderRadius: "8px",
        padding: "8px 12px",
        fontSize: "12px",
        fontWeight: 600,
      },
    }));
    const edges: Edge[] = (graphData.edges || []).map((e: any) => ({
      id: e.id || `${e.source}->${e.target}`,
      source: e.source,
      target: e.target,
      type: "smoothstep",
      animated: true,
      markerEnd: { type: MarkerType.ArrowClosed },
      style: { stroke: "#94a3b8", strokeWidth: 1.5 },
      label: e.label || "",
    }));
    return { nodes, edges };
  }, [graphData]);

  const [nodes, setNodes, onNodesChange] = useNodesState(initialNodes);
  const [edges, setEdges, onEdgesChange] = useEdgesState(initialEdges);

  useEffect(() => { setNodes(initialNodes); setEdges(initialEdges); }, [initialNodes, initialEdges]);

  const onNodeClick = useCallback((_event: any, node: Node) => {
    setSelectedNode(node);
  }, []);

  if (!isLoaded) return <SidebarLayout><LoadingSpinner text="Loading graph..." /></SidebarLayout>;
  if (!isSignedIn) { router.replace("/login"); return null; }

  if (projectsLoading || !graphData) return <SidebarLayout><LoadingSpinner text="Loading research graph..." /></SidebarLayout>;

  return (
    <SidebarLayout>
      <div className="flex h-[calc(100vh-0px)]">
        <div className="flex-1">
          <div className="absolute left-4 top-4 z-10">
            <h1 className="text-xl font-bold text-slate-900 dark:text-slate-100">Research Graph</h1>
            <p className="text-xs text-slate-500 dark:text-slate-400">{project?.name ?? "Project"} · {nodes.length} nodes, {edges.length} connections</p>
          </div>
          {nodes.length > 0 ? (
            <ReactFlow
              nodes={nodes}
              edges={edges}
              onNodesChange={onNodesChange}
              onEdgesChange={onEdgesChange}
              onNodeClick={onNodeClick}
              fitView
              attributionPosition="bottom-left"
            >
              <Background color="#e2e8f0" gap={20} />
              <Controls />
              <MiniMap
                nodeColor={(n) => NODE_COLORS[(n.data as Record<string, string>)?.kind] || "#64748b"}
                maskColor="rgba(0,0,0,0.1)"
                style={{ border: "1px solid #e2e8f0", borderRadius: "8px" }}
              />
            </ReactFlow>
          ) : (
            <div className="flex h-full items-center justify-center">
              <p className="text-sm text-slate-400 dark:text-slate-500">Run investigations to populate the research graph.</p>
            </div>
          )}
        </div>

        {selectedNode && (
          <aside className="w-80 border-l border-slate-200 bg-white p-4 overflow-y-auto dark:border-slate-600 dark:bg-slate-800/95">
            <div className="mb-4 flex items-center justify-between">
              <h2 className="font-bold text-slate-900 dark:text-slate-100">Node Detail</h2>
              <button onClick={() => setSelectedNode(null)} className="text-xs text-slate-400 hover:text-slate-600 dark:text-slate-500 dark:hover:text-slate-300">Close</button>
            </div>
            <div className="grid gap-3 text-sm">
              <div>
                <span className="text-xs font-semibold uppercase tracking-wide text-slate-400 dark:text-slate-500">ID</span>
                <p className="text-slate-700 dark:text-slate-200">{selectedNode.id}</p>
              </div>
              <div>
                <span className="text-xs font-semibold uppercase tracking-wide text-slate-400 dark:text-slate-500">Kind</span>
                <p className="text-slate-700 dark:text-slate-200">{(selectedNode.data as Record<string, string>)?.kind || "unknown"}</p>
              </div>
              <div>
                <span className="text-xs font-semibold uppercase tracking-wide text-slate-400 dark:text-slate-500">Label</span>
                <p className="text-slate-700 dark:text-slate-200">{(selectedNode.data as Record<string, string>)?.label || "—"}</p>
              </div>
              <div className="flex flex-wrap gap-2">
                <span
                  className="rounded-full px-2 py-1 text-xs font-bold text-white"
                  style={{ background: NODE_COLORS[(selectedNode.data as Record<string, string>)?.kind] || "#64748b" }}
                >
                  {(selectedNode.data as Record<string, string>)?.kind || "node"}
                </span>
              </div>
            </div>
          </aside>
        )}
      </div>
    </SidebarLayout>
  );
}