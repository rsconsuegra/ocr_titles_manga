# US-2C2: Interactive Pipeline Profile Builder

**Sub-phase**: 2C — Pipeline Visualization
**Depends on**: US-2C1 (PipelineGraph component), US-1D1 (PipelineProfile)
**Blocks**: None

---

## Overview

Extend the pipeline visualization page with an interactive profile builder. Users can click nodes to toggle steps/models on/off, rearrange preprocessing step order by dragging, and save the configuration as a pipeline profile. The graph updates in real-time as users make changes.

---

## Implementation Details

### 1. `frontend/src/components/pipeline/PipelineProfileBuilder.tsx`

```tsx
import { useState, useCallback, useMemo } from "react";
import {
  ReactFlow,
  Background,
  Controls,
  type Node,
  type Edge,
  type NodeChange,
  type NodePositionChange,
  applyNodeChanges,
} from "@xyflow/react";

import type { StepDescriptor, ModelDescriptor } from "../../api/types";
import { buildNodesAndEdges, type StepNodeData } from "./PipelineGraph";

interface PipelineProfileBuilderProps {
  steps: StepDescriptor[];
  models: ModelDescriptor[];
  enableLlm: boolean;
  enabledSteps: Set<string>;
  enabledModels: Set<string>;
  onToggleStep: (name: string) => void;
  onToggleModel: (name: string) => void;
}

export default function PipelineProfileBuilder({
  steps,
  models,
  enableLlm,
  enabledSteps,
  enabledModels,
  onToggleStep,
  onToggleModel,
}: PipelineProfileBuilderProps) {
  const { nodes: baseNodes, edges } = buildNodesAndEdges(
    steps,
    models,
    enableLlm
  );

  const patchedNodes = baseNodes.map((n) => {
    const data = n.data as StepNodeData;
    if (data.type === "preprocess" && n.id.startsWith("preprocess-")) {
      const stepName = n.id.replace("preprocess-", "");
      return { ...n, data: { ...data, enabled: enabledSteps.has(stepName) } };
    }
    if (data.type === "ocr" && n.id.startsWith("ocr-")) {
      const modelName = n.id.replace("ocr-", "");
      return { ...n, data: { ...data, enabled: enabledModels.has(modelName) } };
    }
    return n;
  });

  const [nodes, setNodes] = useState(patchedNodes);

  const onNodesChange = useCallback(
    (changes: NodeChange[]) => {
      const positionChanges = changes.filter(
        (c): c is NodePositionChange => c.type === "position"
      );
      if (positionChanges.length > 0) {
        setNodes((nds) => applyNodeChanges(changes, nds));
      }
    },
    []
  );

  const onNodeClick = useCallback(
    (_: React.MouseEvent, node: Node) => {
      if (node.id.startsWith("preprocess-")) {
        onToggleStep(node.id.replace("preprocess-", ""));
      } else if (node.id.startsWith("ocr-")) {
        onToggleModel(node.id.replace("ocr-", ""));
      }
    },
    [onToggleStep, onToggleModel]
  );

  return (
    <div className="h-[500px] w-full rounded-lg border border-highlight/10 bg-panel">
      <ReactFlow
        nodes={nodes}
        edges={edges}
        onNodesChange={onNodesChange}
        onNodeClick={onNodeClick}
        fitView
      >
        <Background color="#1a2030" gap={20} />
        <Controls />
      </ReactFlow>
    </div>
  );
}
```

### 2. `frontend/src/pages/ProfileBuilder.tsx`

Full page combining graph builder with save-as-profile form:

```tsx
import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import {
  getPreprocessSteps,
  getOCRModels,
  createProfile,
} from "../api/client";
import type { StepDescriptor, ModelDescriptor } from "../api/types";
import PipelineProfileBuilder from "../components/pipeline/PipelineProfileBuilder";
import { DsoCard, DsoButton, DsoInput } from "../components/dso";

export default function ProfileBuilder() {
  const navigate = useNavigate();
  const [steps, setSteps] = useState<StepDescriptor[]>([]);
  const [models, setModels] = useState<ModelDescriptor[]>([]);
  const [enabledSteps, setEnabledSteps] = useState<Set<string>>(new Set());
  const [enabledModels, setEnabledModels] = useState<Set<string>>(new Set());
  const [enableLlm, setEnableLlm] = useState(true);
  const [profileName, setProfileName] = useState("");
  const [profileDesc, setProfileDesc] = useState("");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    Promise.all([getPreprocessSteps(), getOCRModels()]).then(([s, m]) => {
      setSteps(s);
      setModels(m);
      setEnabledSteps(new Set(s.map((st) => st.name)));
      setEnabledModels(new Set(m.filter((mo) => mo.name === "tesseract").map((mo) => mo.name)));
    });
  }, []);

  const toggleStep = (name: string) => {
    setEnabledSteps((prev) => {
      const next = new Set(prev);
      next.has(name) ? next.delete(name) : next.add(name);
      return next;
    });
  };

  const toggleModel = (name: string) => {
    setEnabledModels((prev) => {
      const next = new Set(prev);
      next.has(name) ? next.delete(name) : next.add(name);
      return next;
    });
  };

  const handleSave = async () => {
    if (!profileName.trim()) return;
    setSaving(true);
    setError(null);
    try {
      await createProfile({
        name: profileName,
        description: profileDesc,
        preprocess_steps: steps
          .filter((s) => enabledSteps.has(s.name))
          .map((s) => ({ name: s.name, enabled: true, params: {} })),
        ocr_models: [...enabledModels],
        enable_llm: enableLlm,
      });
      navigate("/profiles");
    } catch (e: any) {
      setError(e.message);
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold text-bright">Pipeline Profile Builder</h1>

      {error && (
        <div className="neo-inset rounded-lg p-3 text-sm text-amber">{error}</div>
      )}

      <DsoCard variant="flat">
        <PipelineProfileBuilder
          steps={steps}
          models={models}
          enableLlm={enableLlm}
          enabledSteps={enabledSteps}
          enabledModels={enabledModels}
          onToggleStep={toggleStep}
          onToggleModel={toggleModel}
        />
      </DsoCard>

      <DsoCard variant="flat">
        <p className="tech-label mb-3 text-xs text-muted">
          Click a node to toggle it on/off. Drag to reposition.
        </p>
        <div className="flex items-center gap-6 text-sm">
          <span className="text-bright">
            Steps: {enabledSteps.size}/{steps.length}
          </span>
          <span className="text-bright">
            Models: {enabledModels.size}/{models.length}
          </span>
          <label className="flex items-center gap-2 text-bright">
            <input
              type="checkbox"
              checked={enableLlm}
              onChange={(e) => setEnableLlm(e.target.checked)}
              className="accent-teal"
            />
            LLM Post-Processing
          </label>
        </div>
      </DsoCard>

      <DsoCard variant="flat">
        <h3 className="tech-label mb-3 text-xs text-muted">Save as Profile</h3>
        <div className="space-y-3">
          <div>
            <label className="mb-1 block text-xs text-muted">Profile Name</label>
            <input
              type="text"
              value={profileName}
              onChange={(e) => setProfileName(e.target.value)}
              className="neo-inset w-full rounded border-highlight/20 bg-inset px-3 py-2 text-sm text-bright"
              placeholder="My pipeline profile"
            />
          </div>
          <div>
            <label className="mb-1 block text-xs text-muted">Description</label>
            <input
              type="text"
              value={profileDesc}
              onChange={(e) => setProfileDesc(e.target.value)}
              className="neo-inset w-full rounded border-highlight/20 bg-inset px-3 py-2 text-sm text-bright"
              placeholder="Optional description"
            />
          </div>
          <DsoButton
            variant="primary"
            onClick={handleSave}
            disabled={saving || !profileName.trim()}
          >
            {saving ? "Saving..." : "Save Profile"}
          </DsoButton>
        </div>
      </DsoCard>
    </div>
  );
}
```

### 3. `frontend/src/App.tsx` (addition)

```tsx
import ProfileBuilder from "./pages/ProfileBuilder";

<Route path="/pipeline/builder" element={<ProfileBuilder />} />

// In "Config" dropdown:
<Link to="/pipeline/builder">Profile Builder</Link>
```

---

## Acceptance Criteria

- [ ] `/pipeline/builder` renders interactive pipeline graph with clickable nodes
- [ ] Clicking a preprocessing step node toggles it on/off (LED indicator updates)
- [ ] Clicking an OCR model node toggles it on/off
- [ ] Node counts update in real-time (e.g., "Steps: 3/5")
- [ ] LLM toggle adds/removes LLM node
- [ ] Nodes can be dragged to reposition
- [ ] Profile name and description inputs
- [ ] "Save Profile" creates a `PipelineProfile` via API with selected steps/models/LLM flag
- [ ] Redirects to `/profiles` after save
- [ ] Error handling for save failures
- [ ] DSO dark theme applied throughout

---

## Test Specifications

Manual UI testing:
- Navigate to `/pipeline/builder`, verify graph renders with all steps/models
- Click a preprocessing node — verify it toggles off (grayed out, LED off)
- Click an OCR model node — verify toggle
- Toggle LLM off — verify LLM node removed from graph
- Fill profile name, click Save — verify redirect to `/profiles`
- Save with empty name — verify button disabled
