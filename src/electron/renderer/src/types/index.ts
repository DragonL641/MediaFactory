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
  type: TaskType;
  inputPath: string; // camelCase，匹配后端返回
  outputPath?: string; // camelCase，匹配后端返回
  status: TaskStatus;
  progress: number;
  message: string;
  stage?: string;
  error?: string; // 后端直接返回 error 字段
}

export interface AudioConfig {
  sample_rate?: number;
  channels?: number;
  filter_enabled?: boolean;
  highpass_freq?: number;
  lowpass_freq?: number;
  volume?: number;
  output_format?: string;
}

export interface SubtitleConfig {
  output_format?: string;
  bilingual?: boolean;
  bilingual_layout?: string;
  style_preset?: string;
}

export interface EnhancementConfig {
  scale?: number;
  model?: string;
  denoise?: boolean;
  temporal?: boolean;
}

export interface TaskConfig {
  task_type: TaskType;
  input_path: string;
  output_path?: string;
  source_lang?: string;
  target_lang?: string;
  use_llm?: boolean;
  llm_preset?: string;
  audio_config?: AudioConfig;
  subtitle_config?: SubtitleConfig;
  enhancement_config?: EnhancementConfig;
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
  purpose: string;
  tier: string;
  size: string;
  memory: string;
  vram?: string;
  downloaded: boolean;
  complete: boolean;
}

export interface EnhancementModelInfo {
  id: string;
  name: string;
  purpose: string;
  size: string;
  memory: string;
  vram?: string;
  description: string;
  downloaded: boolean;
  complete: boolean;
}

export interface DenoiseModelInfo {
  id: string;
  name: string;
  purpose: string;
  size: string;
  memory: string;
  vram?: string;
  description: string;
  downloaded: boolean;
  complete: boolean;
}

export interface DiarizationModelInfo {
  id: string;
  name: string;
  purpose: string;
  size: string;
  memory: string;
  vram?: string;
  description: string;
  downloaded: boolean;
  complete: boolean;
}

export interface WhisperModelInfo {
  id: string;
  name: string;
  purpose: string;
  size: string;
  memory: string;
  vram?: string;
  description: string;
  downloaded: boolean;
  complete: boolean;
}

export interface AllModelsStatus {
  whisper: ModelStatus & {
    models?: WhisperModelInfo[];
  };
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
  diarization: {
    name: string;
    models: DiarizationModelInfo[];
  };
}

export interface AppSettings {
  language?: string;
}

export interface LoggingConfig {
  retention_days?: number;
  max_files?: number;
}

export interface AppConfig {
  whisper: WhisperConfig;
  model: ModelConfig;
  llm_api?: LLMApiConfig;
  openai_compatible?: Record<string, LLMProviderConfig>;
  logging?: LoggingConfig;
  app?: AppSettings;
}

export interface WhisperConfig {
  beam_size: number;
  no_speech_threshold?: number;
  condition_on_previous_text?: boolean;
  word_timestamps?: boolean;
  vad_filter: boolean;
  vad_threshold: number;
  vad_min_speech_duration_ms?: number;
  vad_min_silence_duration_ms?: number;
}

export interface ModelConfig {
  local_model_path?: string;
  download_source?: string;
  download_timeout?: number;
  models_dir?: string;
  available_translation_models?: string[];
  whisper_models?: string[];
}

export interface LLMApiConfig {
  current_preset?: string;
  timeout?: number;
  temperature?: number;
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
  status: string; // TaskStatus 枚举值 + "downloading" 等扩展状态
  progress: number;
  message: string;
  stage?: string;
  file_index?: number;
  total_files?: number;
}

// WebSocket 消息类型（与后端 websocket.py 对齐）
export type WebSocketEventType =
  | "progress"
  | "task_complete"
  | "subscribed"
  | "server_shutdown";

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
