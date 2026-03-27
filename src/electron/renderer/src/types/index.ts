/**
 * TypeScript 类型定义
 */

export enum TaskStatus {
  PENDING = "pending",
  RUNNING = "running",
  COMPLETED = "completed",
  FAILED = "failed",
  CANCELLED = "cancelled",
}

export enum TaskType {
  SUBTITLE = "subtitle",
  AUDIO = "audio",
  TRANSCRIBE = "transcribe",
  TRANSLATE = "translate",
  ENHANCE = "enhance",
  DOWNLOAD = "download",
}

export interface Task {
  id: string;
  name: string;
  type: string; // TaskType value
  inputPath: string; // camelCase，匹配后端返回
  outputPath?: string; // camelCase，匹配后端返回
  status: TaskStatus;
  progress: number;
  message: string;
  stage?: string;
  error?: string; // 后端直接返回 error 字段
}

export interface TaskConfig {
  task_type: TaskType;
  input_path: string;
  output_path?: string;
  source_lang?: string;
  target_lang?: string;
  use_llm?: boolean;
  llm_preset?: string;
  output_format?: string;
  bilingual?: boolean;
  bilingual_layout?: string;
  style_preset?: string;
  audio_sample_rate?: number;
  audio_channels?: number;
  audio_filter_enabled?: boolean;
  audio_highpass_freq?: number;
  audio_lowpass_freq?: number;
  audio_volume?: number;
  audio_output_format?: string;
  enhancement_scale?: number;
  enhancement_model?: string;
  enhancement_denoise?: boolean;
  enhancement_temporal?: boolean;
}

export interface ModelStatus {
  name: string;
  loaded: boolean;
  available: boolean;
  enabled: boolean;
}

export interface TranslationModelInfo {
  id: string;
  name: string;
  tier: string;
  memory: string;
  downloaded: boolean;
}

export interface EnhancementModelInfo {
  id: string;
  name: string;
  size: string;
  memory: string;
  description: string;
  downloaded: boolean;
}

export interface DenoiseModelInfo {
  id: string;
  name: string;
  size: string;
  memory: string;
  description: string;
  downloaded: boolean;
}

export interface AllModelsStatus {
  whisper: ModelStatus;
  translation: ModelStatus & {
    models: TranslationModelInfo[];
  };
  llm: ModelStatus & {
    config?: LLMApiConfig;
  };
  enhancement: {
    name: string;
    models: EnhancementModelInfo[];
  };
  denoise: {
    name: string;
    models: DenoiseModelInfo[];
  };
}

export interface AppConfig {
  whisper: WhisperConfig;
  model: ModelConfig;
  llm_api?: LLMApiConfig;
  openai_compatible?: Record<string, LLMProviderConfig>;
}

export interface WhisperConfig {
  beam_size: number;
  vad_filter: boolean;
  vad_threshold: number;
  word_timestamps?: boolean;
}

export interface ModelConfig {
  local_model_path?: string;
  download_source?: string;
  models_dir?: string;
}

export interface LLMApiConfig {
  current_preset?: string;
  timeout?: number;
  max_retries?: number;
}

export interface LLMProviderConfig {
  api_key: string;
  base_url: string;
  model: string;
}

export interface LLMPresetInfo {
  display_name: string;
  base_url: string;
  model_examples: string[];
  configured: boolean;
  has_api_key: boolean;
  connection_available?: boolean;
  model?: string;
}

export interface ProgressData {
  task_id: string;
  status: TaskStatus;
  progress: number;
  message: string;
  stage?: string;
  file_index?: number;
  total_files?: number;
}

// WebSocket 消息类型
export type WebSocketEventType =
  | "progress"
  | "task_created"
  | "task_complete"
  | "task_completed"
  | "task_failed"
  | "task_cancelled"
  | "model_status"
  | "config_changed";

export interface WebSocketMessage {
  type: WebSocketEventType;
  [key: string]: unknown;
}

export interface WebSocketProgressMessage extends WebSocketMessage {
  type: "progress";
  task_id: string;
  data: ProgressData;
}

// API 响应/错误类型
export interface ApiErrorResponse {
  detail?: string;
  message?: string;
  error?: string;
}

export interface BatchOperationResponse {
  started?: number;
  cancelled?: number;
  cleared?: number;
}

export interface TestConnectionResponse {
  success: boolean;
  error?: string;
  latency_ms?: number;
}
