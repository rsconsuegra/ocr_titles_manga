# US-2C1: Pipeline Visualization Page

**Sub-phase**: 2C — Pipeline Visualization
**Depends on**: Step 1 (`reactflow` dep), US-2A1–US-2A3 (OCR models with registry params)
**Blocks**: US-2C2 (interactive pipeline builder)

---

## Overview

Create a pipeline visualization page using React Flow that renders the current pipeline configuration as an interactive node graph. Nodes represent preprocessing steps, OCR models, and LLM post-processing. Edges show data flow. The graph reads from existing API endpoints (preprocess steps, model registry, profiles).

---

## Implementation Details

### 1. Install React Flow

```bash
cd frontend && npm install @xyflow/react
```

### 2. `frontend/src/components/pipeline/PipelineGraph.tsx`

Core React Flow graph component:

```tsx
import { useCallback } from "react";
import {
  ReactFlow,
  Background,
  Controls,
  MiniMap,
  type Node,
  type Edge,
  type NodeTypes,
  Handle,
  Position,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";

import type { StepDescriptor, ModelDescriptor } from "../../api/types";

interface StepNodeData {
  label: string;
  description: string;
  enabled: boolean;
  type: "preprocess" | "ocr" | "llm";
}

function StepNode({ data }: { data: StepNodeData }) {
  const borderColor = data.enabled
    ? data.type === "preprocess"
      ? "border-teal"
      : data.type === "ocr"
        ? "border-teal"
        : "border-amber"
    : "border-muted/30";

  return (
    <div
      className={`min-w-[180px] rounded-lg border-2 ${borderColor} bg-panel p-3 shadow-lg`}
    >
      <Handle type="target" position={Position.Top} className="!bg-teal" />
      <div className="flex items-center gap-2">
        {data.enabled && (
          <span
            className={`h-2 w-2 rounded-full ${
              data.type === "llm" ? "bg-amber" : "bg-teal"
            }`}
          />
        )}
        {!data.enabled && <span className="h-2 w-2 rounded-full bg-muted/30" />}
        <span className="text-sm font-medium text-bright">{data.label}</span>
      </div>
      <p className="mt-1 text-xs text-muted">{data.description}</p>
      <Handle type="source" position={Position.Bottom} className="!bg-teal" />
    </div>
  );
}

const nodeTypes: NodeTypes = {
  step: StepNode,
};

interface PipelineGraphProps {
  preprocessSteps: StepDescriptor[];
  ocrModels: ModelDescriptor[];
  enableLlm: boolean;
}

export function buildNodesAndEdges(
  steps: StepDescriptor[],
  models: ModelDescriptor[],
  enableLlm: boolean
) {
  const nodes: Node<StepNodeData>[] = [];
  const edges: Edge[] = [];

  const inputNode: Node<StepNodeData> = {
    id: "input",
    type: "step",
    position: { x: 300, y: 0 },
    data: {
      label: "Image Input",
      description: "Uploaded manga image",
      enabled: true,
      type: "preprocess",
    },
  };
  nodes.push(inputNode);

  steps.forEach((step, i) => {
    const id = `preprocess-${step.name}`;
    nodes.push({
      id,
      type: "step",
      position: { x: 300, y: 120 * (i + 1) },
      data: {
        label: step.label,
        description: step.description,
        enabled: true,
        type: "preprocess",
      },
    });
    const prevId = i === 0 ? "input" : `preprocess-${steps[i - 1].name}`;
    edges.push({
      id: `${prevId}-${id}`,
      source: prevId,
      target: id,
      animated: true,
      style: { stroke: "#00d4aa" },
    });
  });

  const lastPreprocessId =
    steps.length > 0 ? `preprocess-${steps[steps.length - 1].name}` : "input";

  models.forEach((model, i) => {
    const id = `ocr-${model.name}`;
    nodes.push({
      id,
      type: "step",
      position: { x: 150 * i, y: 120 * (steps.length + 1) },
      data: {
        label: model.label,
        description: model.description,
        enabled: true,
        type: "ocr",
      },
    });
    edges.push({
      id: `${lastPreprocessId}-${id}`,
      source: lastPreprocessId,
      target: id,
      animated: true,
      style: { stroke: "#00d4aa" },
    });
  });

  if (enableLlm && models.length > 0) {
    const firstModelId = `ocr-${models[0].name}`;
    nodes.push({
      id: "llm",
      type: "step",
      position: { x: 300, y: 120 * (steps.length + 2) },
      data: {
        label: "LLM Post-Processing",
        description: "Extract structured metadata",
        enabled: true,
        type: "llm",
      },
    });
    models.forEach((model) => {
      edges.push({
        id: `ocr-${model.name}-llm`,
        source: `ocr-${model.name}`,
        target: "llm",
        animated: true,
        style: { stroke: "#f0a030" },
      });
    });
  }

  return { nodes, edges };
}

export default function PipelineGraph({
  preprocessSteps,
  ocrModels,
  enableLlm,
}: PipelineGraphProps) {
  const { nodes, edges } = buildNodesAndEdges(
    preprocessSteps,
    ocrModels,
    enableLlm
  );

  return (
    <div className="h-[600px] w-full rounded-lg border border-highlight/10 bg-panel">
      <ReactFlow nodes={nodes} edges={edges} nodeTypes={nodeTypes} fitView>
        <Background color="#1a2030" gap={20} />
        <Controls className="!bg-panel !border-highlight/20 [&>button]:!bg-panel [&>button]:!border-highlight/20 [&>button]:!text-bright" />
        <MiniMap
          nodeColor={(n) => {
            const data = n.data as StepNodeData;
            return data?.type === "llm" ? "#f0a030" : "#00d4aa";
          }}
          maskColor="rgba(0,0,0,0.7)"
          className="!bg-panel !border-highlight/20"
        />
      </ReactFlow>
    </div>
  );
}
```

### 3. `frontend/src/pages/PipelineVisualization.tsx`

```tsx
import { useState, useEffect } from "react";
import { getPreprocessSteps, getOCRModels } from "../api/client";
import type { StepDescriptor, ModelDescriptor } from "../api/types";
import PipelineGraph from "../components/pipeline/PipelineGraph";
import { DsoCard, DsoSelect } from "../components/dso";

export default function PipelineVisualization() {
  const [steps, setSteps] = useState<StepDescriptor[]>([]);
  const [models, setModels] = useState<ModelDescriptor[]>([]);
  const [enableLlm, setEnableLlm] = useState(true);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([getPreprocessSteps(), getOCRModels()])
      .then(([s, m]) => {
        setSteps(s);
        setModels(m);
      })
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <p className="text-muted">Loading pipeline...</p>;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-bright">Pipeline Visualization</h1>
        <label className="flex items-center gap-2 text-sm text-bright">
          <input
            type="checkbox"
            checked={enableLlm}
            onChange={(e) => setEnableLlm(e.target.checked)}
            className="accent-teal"
          />
          LLM Post-Processing
        </label>
      </div>

      <DsoCard variant="flat">
        <PipelineGraph
          preprocessSteps={steps}
          ocrModels={models}
          enableLlm={enableLlm}
        />
      </DsoCard>

      <div className="grid grid-cols-3 gap-4">
        <DsoCard variant="flat">
          <h3 className="tech-label mb-2 text-xs text-muted">Preprocessing</h3>
          <p className="text-2xl font-bold text-bright">{steps.length}</p>
          <p className="text-xs text-muted">steps configured</p>
        </DsoCard>
        <DsoCard variant="flat">
          <h3 className="tech-label mb-2 text-xs text-muted">OCR Models</h3>
          <p className="text-2xl font-bold text-bright">{models.length}</p>
          <p className="text-xs text-muted">models registered</p>
        </DsoCard>
        <DsoCard variant="flat">
          <h3 className="tech-label mb-2 text-xs text-muted">Post-Processing</h3>
          <p className="text-2xl font-bold text-bright">
            {enableLlm ? "LLM + Rules" : "Rules Only"}
          </p>
          <p className="text-xs text-muted">extraction mode</p>
        </DsoCard>
      </div>
    </div>
  );
}
```

### 4. `frontend/src/App.tsx` (addition)

```tsx
import PipelineVisualization from "./pages/PipelineVisualization";

<Route path="/pipeline" element={<PipelineVisualization />} />

// In "Playground" dropdown:
<Link to="/pipeline">Pipeline Diagram</Link>
```

---

## Acceptance Criteria

- [ ] `/pipeline` page renders React Flow graph with pipeline nodes and edges
- [ ] Nodes: Input → Preprocessing Steps → OCR Models → (optional) LLM Post-Processing
- [ ] Each node shows label, description, and enabled/disabled LED indicator
- [ ] Edges animated with teal (data flow) or amber (LLM path) color
- [ ] LLM toggle checkbox adds/removes the LLM node
- [ ] Stats cards below graph: preprocessing step count, OCR model count, extraction mode
- [ ] Graph fits viewport, supports pan/zoom via React Flow controls
- [ ] MiniMap shows overview in corner
- [ ] DSO dark theme: dark panel background, teal/amber accents, tech labels

---

## Test Specifications

Manual UI testing:
- Navigate to `/pipeline` and verify graph renders with correct node layout
- Toggle LLM checkbox and verify LLM node appears/disappears
- Pan and zoom the graph using mouse and React Flow controls
- Verify node labels match configured preprocessing steps and registered OCR models
- Verify stats cards show correct counts
