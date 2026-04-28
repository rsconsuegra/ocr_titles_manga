export interface PipelineRunResponse {
  id: string;
  input_image_path: string;
  status: string;
  error_message: string | null;
  created_at: string;
  completed_at: string | null;
}

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  limit: number;
  offset: number;
}

export interface PostProcessingResultDetail {
  id: string;
  title_en: string | null;
  title_ja: string | null;
  code: string | null;
  confidence: number;
  processing_type: string;
  created_at: string;
}

export interface OCRResultDetail {
  id: string;
  model_name: string;
  raw_text: string;
  confidence: number;
  processing_time_ms: number;
  error: string | null;
  created_at: string;
  post_processing_results: PostProcessingResultDetail[];
}

export interface RunDetailResponse {
  id: string;
  input_image_path: string;
  status: string;
  error_message: string | null;
  created_at: string;
  completed_at: string | null;
  ocr_results: OCRResultDetail[];
}

export interface CatalogEntryResponse {
  id: string;
  title_en: string | null;
  title_ja: string | null;
  code: string | null;
  source_run_id: string;
  confidence: number;
  status: string;
  created_at: string;
  updated_at: string | null;
}

export interface ParamDescriptor {
  name: string;
  type: string;
  default: unknown;
  label: string;
  description: string;
  options?: string[];
  disabled_options?: Record<string, string>;
  min?: number;
  max?: number;
  step?: number;
}

export interface StepDescriptor {
  name: string;
  label: string;
  description: string;
  params: ParamDescriptor[];
}

export interface PreviewStepResponse {
  image: string;
  step_name: string;
  metadata: Record<string, unknown>;
  processing_time_ms: number;
  success: boolean;
  error: string | null;
}

export interface PipelineStepResult {
  step_name: string;
  enabled: boolean;
  success: boolean;
  image: string | null;
  metadata: Record<string, unknown>;
  processing_time_ms: number;
  error: string | null;
}

export interface PreviewPipelineResponse {
  steps: PipelineStepResult[];
  total_processing_time_ms: number;
}

export interface ModelDescriptorResponse {
  name: string;
  label: string;
  description: string;
  params: ParamDescriptor[];
  available: boolean;
  enabled: boolean;
}

export interface OCRResultData {
  raw_text: string;
  model_name: string;
  confidence: number;
  processing_time_ms: number;
  error: string | null;
}

export interface LLMResultData {
  title_en: string | null;
  title_ja: string | null;
  code: string | null;
  confidence: number;
  source_method: string;
}

export interface OCRRunResponse {
  ocr: OCRResultData;
  llm: LLMResultData | null;
}

export interface QuickRunResponse {
  ocr_results: OCRResultData[];
  llm: LLMResultData | null;
  total_processing_time_ms: number;
}

export interface BatchRunResponse {
  id: string;
  name: string | null;
  status: string;
  total_count: number;
  completed_count: number;
  failed_count: number;
  created_at: string;
  completed_at: string | null;
}

export interface BatchRunDetailResponse extends BatchRunResponse {
  runs: PipelineRunResponse[];
}

export interface LLMPromptConfig {
  system_prompt?: string;
  user_prompt_template?: string;
  temperature?: number;
  max_ocr_chars?: number;
}

export interface ProfileResponse {
  id: string;
  name: string;
  description: string | null;
  preprocess_steps: Record<string, Record<string, unknown>> | null;
  ocr_models: Record<string, Record<string, unknown>> | null;
  enable_llm: boolean;
  llm_provider: string;
  llm_config: LLMPromptConfig | null;
  is_default: boolean;
  created_at: string;
  updated_at: string | null;
}

export interface ProfileCreateRequest {
  name: string;
  description?: string;
  preprocess_steps?: Record<string, Record<string, unknown>>;
  ocr_models?: Record<string, Record<string, unknown>>;
  enable_llm?: boolean;
  llm_provider?: string;
  llm_config?: LLMPromptConfig | null;
  is_default?: boolean;
}

export interface ProfileUpdateRequest {
  name?: string;
  description?: string | null;
  preprocess_steps?: Record<string, Record<string, unknown>> | null;
  ocr_models?: Record<string, Record<string, unknown>> | null;
  enable_llm?: boolean;
  llm_provider?: string;
  llm_config?: LLMPromptConfig | null;
  is_default?: boolean;
}

export interface LLMProvider {
  name: string;
  label: string;
  available: boolean;
  configured?: boolean;
  model_count?: number;
}

export interface LLMProvidersResponse {
  providers: LLMProvider[];
}

export interface OllamaModelInfo {
  name: string;
  size: number;
  modified_at: string;
  parameter_size: string;
  quantization: string;
}

export interface OllamaStatusResponse {
  configured: boolean;
  base_url: string;
  default_model: string;
  default_vision_model: string;
}

export interface OllamaSettingsResponse {
  base_url: string;
  configured: boolean;
  default_model: string;
  default_vision_model: string;
  available_llm_models: OllamaModelInfo[];
  available_vision_models: OllamaModelInfo[];
}

export interface OllamaUrlUpdateResponse {
  base_url: string;
  default_model: string;
  default_vision_model: string;
  available_llm_models: OllamaModelInfo[];
  available_vision_models: OllamaModelInfo[];
  validated: boolean;
  message: string;
}

export interface CredentialInfo {
  service: string;
  has_key: boolean;
  masked_key: string | null;
  source: string | null;
  is_active: boolean;
}

export interface CredentialValidateResponse {
  valid: boolean;
  message: string;
}
