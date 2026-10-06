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
  metadata?: Record<string, unknown>; // 结果附加数据（如 translation_stats）
  createdAt?: number; // epoch 秒（表格时间列；旧任务可能缺失）
}

export interface ModelStatus {
  name: string;
  loaded: boolean;
  available: boolean;
  enabled: boolean;
}

// 注册表模型条目（enhancement/denoise/whisper/face_restoration 共用同一结构）
export interface RegistryModelInfo {
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
    models?: RegistryModelInfo[];
  };
  llm: ModelStatus & {
    config?: LLMApiConfig;
  };
  enhancement: {
    name: string;
    models: RegistryModelInfo[];
  };
  denoise: {
    name: string;
    models: RegistryModelInfo[];
  };
  face_restoration: {
    name: string;
    models: RegistryModelInfo[];
  };
}

export interface LocalModelInfo {
  name: string;
  size: number;
  parameterSize: string;
  quantizationLevel: string;
  modifiedAt: string;
}

export interface PullProgress {
  name: string;
  progress: number;
  taskId: string;
}

export interface LocalModelsStatus {
  available: boolean;
  models: LocalModelInfo[];
  /** 在飞拉取任务快照（轮询渲染进度行） */
  pulling?: PullProgress[];
}

export interface ModelReadiness {
  whisper_ready: boolean;
  enhancement_ready: boolean;
  llm: {
    configured_presets: string[];
    current_preset: string | null;
    current_ready: boolean;
    llm_available: boolean;
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
  download_source?: string;
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
