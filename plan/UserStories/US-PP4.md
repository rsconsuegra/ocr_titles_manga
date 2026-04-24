# US-PP4: Export Pipeline Configuration

**Feature**: Preprocessing Playground
**Depends on**: US-PP1 (step registry), US-PP3 (pipeline config format)
**Blocks**: None

---

## Overview

Create an API endpoint that converts a pipeline configuration into a YAML string matching the exact format of `config/preprocess.yaml`. The frontend provides a download button so users can save the config and use it in automated processing.

---

## Implementation Details

### 1. `ocr_manga_title/api/schemas/preprocess.py` (additions)

```python
class ExportPipelineRequest(BaseModel):
    steps: list[PipelineStepConfig]

class ExportPipelineResponse(BaseModel):
    yaml: str
```

### 2. `ocr_manga_title/api/routes/preprocess.py` (additions)

```python
import yaml as yaml_lib

@router.post("/export", response_model=ExportPipelineResponse)
async def export_pipeline(request: ExportPipelineRequest):
    # Validate step names
    for s in request.steps:
        if s.step_name not in STEP_REGISTRY:
            raise HTTPException(422, f"Unknown step: {s["step_name"]}")
    
    # Build YAML structure matching config/preprocess.yaml format
    steps_lookup = {s.step_name: s for s in request.steps}
    
    preprocessing = {"enabled": True, "debug": True}
    
    for step_name in STEP_ORDER:
        cfg = steps_lookup.get(step_name)
        if cfg and cfg.enabled:
            step_dict = {"enabled": True, **cfg.config}
        else:
            # Disabled step with defaults from registry
            descriptor = STEP_REGISTRY[step_name]
            defaults = {k: v["default"] for k, v in descriptor["params"].items()}
            step_dict = {"enabled": False, **defaults}
        preprocessing[step_name] = step_dict
    
    output = {"preprocessing": preprocessing}
    yaml_str = yaml_lib.dump(output, default_flow_style=False, sort_keys=False)
    
    return ExportPipelineResponse(yaml=yaml_str)
```

### 3. Frontend: Export button

On the playground page, "Export YAML" button:
1. Collects current pipeline config (all 5 steps with enabled flags and current param values)
2. Calls `exportPipeline(steps)` API function
3. Creates a Blob from the YAML string
4. Triggers download with filename `preprocess.yaml`

```typescript
export async function exportPipeline(
    steps: PipelineStepConfig[]
): Promise<string> {
    const res = await apiFetch<{ yaml: string }>("/api/v1/preprocess/export", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ steps }),
    });
    return res.yaml;
}
```

---

## Acceptance Criteria

- [ ] `POST /api/v1/preprocess/export` accepts JSON `{steps: [{step_name, enabled, config}]}`
- [ ] Returns YAML string with top-level `preprocessing` key
- [ ] YAML includes `enabled: true` and `debug: true` at top level
- [ ] Each step appears as a nested key under `preprocessing`
- [ ] Enabled steps include their configured parameter values
- [ ] Disabled steps have `enabled: false` with default parameter values
- [ ] Parameter values use correct YAML types (int, float, bool, string)
- [ ] Output YAML is directly usable as `config/preprocess.yaml`
- [ ] Returns 422 for unknown step names
- [ ] Frontend "Export YAML" button downloads `preprocess.yaml`
- [ ] Downloaded file contains valid YAML

---

## Test Specifications

**File**: `tests/test_api/test_preprocess.py` (additions)

Tests:
- `test_export_full_pipeline`: All 5 enabled with custom configs → valid YAML with all steps enabled
- `test_export_partial_pipeline`: 2 enabled, 3 disabled → correct enabled flags
- `test_export_all_disabled`: All disabled → YAML has `enabled: false` for each step
- `test_export_yaml_format`: Parse output with PyYAML → verify structure matches `preprocessing.{step_name}.enabled`
- `test_export_unknown_step`: Include unknown step → 422
- `test_export_matches_preprocess_yaml_format`: Output YAML has same keys as `config/preprocess.yaml`
