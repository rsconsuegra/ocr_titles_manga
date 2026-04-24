# Preprocessing Playground User Stories

These user stories cover the Preprocessing Playground feature — an interactive workbench for testing image preprocessing transformations, composing pipelines, and exporting configurations.

**Design decisions**:
- Preprocessing only (no OCR execution in playground)
- Canonical step order enforced: roi → grayscale → upscale → denoise → binarize
- All intermediate results shown in pipeline preview
- Stateless server (image sent with each request)

---

## US-PP1: Browse Available Preprocessing Steps

> As an operator, I want to see all available preprocessing steps with their descriptions and configurable parameters so that I know what transformations I can apply to my images.

**Acceptance Criteria**:
- `GET /api/v1/preprocess/steps` returns a list of all 5 step descriptors in canonical order
- Each descriptor includes: name, display_name, description, category, is_available, params
- Parameter descriptors include: type, default value, and constraints (options/min/max/step)
- Steps with unavailable runtime dependencies have `is_available=false`
- Response is static (no database dependency) — derived from the step registry
- Frontend renders an accordion-style step catalog at `/playground`

---

## US-PP2: Preview Single Preprocessing Step

> As an operator, I want to upload an image, configure a single preprocessing step, and see the original vs transformed image side by side so that I can evaluate the effect before committing to a full pipeline.

**Acceptance Criteria**:
- `POST /api/v1/preprocess/preview/step` accepts multipart: image file + JSON `{step_name, config}`
- Returns base64-encoded PNG image as a data URL alongside metadata and processing time
- The uploaded image is decoded, the specified step is applied, and the result is encoded back
- Invalid step names return 422
- Invalid parameter values return 422 with descriptive error
- Supported image formats: PNG, JPG, WEBP, TIFF, BMP
- Max image size: 20MB
- Frontend displays original and transformed images side by side
- Metadata (processing time, step-specific data like threshold values) is shown below the preview
- Clicking Preview on different steps updates the right panel independently

---

## US-PP3: Compose and Preview Pipeline

> As an operator, I want to enable multiple steps in canonical order, configure each independently, and see the cumulative effect with intermediate results after each step so that I can design an optimal preprocessing pipeline.

**Acceptance Criteria**:
- `POST /api/v1/preprocess/preview/pipeline` accepts multipart: image file + JSON `{steps: [{step_name, enabled, config}]}`
- Steps are always executed in canonical order: roi → grayscale → upscale → denoise → binarize
- Each step's output feeds as input to the next enabled step
- Response includes one `StepIntermediate` per canonical step (5 total), with:
  - `enabled`: whether the step was requested
  - `success`: whether the step completed without error
  - `image`: base64 data URL of the step's output (null if disabled/failed)
  - `metadata`: step-specific output data
  - `processing_time_ms`: execution time
- Response also includes `final_image` (last successful step's output) and `total_processing_time_ms`
- Disabled steps pass the previous image through unchanged
- Frontend displays a horizontal filmstrip of intermediate images
- Each step can be toggled on/off in the pipeline section
- Pipeline config section shows all 5 steps in canonical order with toggle switches

---

## US-PP4: Export Pipeline Configuration

> As an operator, I want to export my configured pipeline as a YAML file so that I can reuse it in automated processing via `config/preprocess.yaml`.

**Acceptance Criteria**:
- `POST /api/v1/preprocess/export` accepts JSON `{steps: [{step_name, enabled, config}]}`
- Returns YAML string matching the exact format of `config/preprocess.yaml`
- Top-level key is `preprocessing` with `enabled: true` and `debug: true`
- Each step appears as a nested key with `enabled` flag and configured parameters
- Disabled steps have `enabled: false` and include only default parameters
- Parameter values use appropriate YAML types (strings, integers, floats, booleans)
- The exported YAML is directly usable as `config/preprocess.yaml` without modification
- Frontend provides a "Export YAML" button that triggers a file download
- Filename defaults to `preprocess.yaml`

---

## US-PP5: Interactive Parameter Configuration

> As an operator, I want parameter controls that match the parameter types (dropdowns for enums, sliders for ranges, toggles for booleans) so that I can quickly adjust settings and see results.

**Acceptance Criteria**:
- Frontend renders parameter forms dynamically from the step descriptors returned by the API
- `select` type params render as `<select>` dropdowns with options from the descriptor
- `int`/`float` type params render as range sliders with min/max/step from the descriptor and a numeric readout
- `bool` type params render as toggle switches
- Default values are pre-populated from the descriptor
- Parameter changes are reflected in preview requests immediately
- "Add to Pipeline" button copies current parameter values into the pipeline config for that step
- Step cards expand/collapse independently (accordion pattern)
- Currently expanded step is visually highlighted
