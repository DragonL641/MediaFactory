/**
 * TanStack Query hooks
 *
 * 提供 API 查询和变更的 React Query hooks
 * 使用 WebSocket 实时推送 + 页面可见性感知 refetch
 */

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { getApiClient } from "./client";
import type { AllModelsStatus } from "../types";

// Query Keys
export const queryKeys = {
  tasks: ["tasks"] as const,
  taskStatus: (id: string) => ["tasks", id] as const,
  modelsStatus: ["models", "status"] as const,
  config: ["config"] as const,
  llmPresets: ["config", "llm", "presets"] as const,
};

// ============ Tasks ============

/**
 * 获取任务列表
 * 仅首次加载 + 页面可见时 refetch，不再固定轮询
 */
export function useTasksQuery() {
  return useQuery({
    queryKey: queryKeys.tasks,
    queryFn: async () => {
      const client = getApiClient();
      const response = await client.get("/api/processing/tasks");
      return response.data;
    },
    staleTime: 30000,
  });
}

/**
 * 获取单个任务状态
 */
export function useTaskStatusQuery(taskId: string) {
  return useQuery({
    queryKey: queryKeys.taskStatus(taskId),
    queryFn: async () => {
      const client = getApiClient();
      const response = await client.get(`/api/processing/status/${taskId}`);
      return response.data;
    },
    enabled: !!taskId,
  });
}

/**
 * 创建字幕任务
 */
export function useCreateSubtitleTaskMutation() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (params: {
      video_path: string;
      source_lang: string;
      target_lang: string;
      use_llm: boolean;
      output_format: string;
      bilingual?: boolean;
      bilingual_layout?: string;
      style_preset?: string;
      llm_preset?: string;
      diarization_enabled?: boolean;
    }) => {
      const client = getApiClient();
      const response = await client.post("/api/processing/subtitle", params);
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.tasks });
    },
  });
}

/**
 * 创建音频提取任务
 */
export function useCreateAudioTaskMutation() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (params: {
      video_path: string;
      output_format?: string;
      sample_rate?: number;
      channels?: number;
      filter_enabled?: boolean;
      highpass_freq?: number;
      lowpass_freq?: number;
      volume?: number;
    }) => {
      const client = getApiClient();
      const response = await client.post("/api/processing/audio", params);
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.tasks });
    },
  });
}

/**
 * 创建转录任务
 */
export function useCreateTranscribeTaskMutation() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (params: {
      audio_path: string;
      source_lang: string;
      output_format?: string;
      style_preset?: string;
      diarization_enabled?: boolean;
    }) => {
      const client = getApiClient();
      const response = await client.post("/api/processing/transcribe", params);
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.tasks });
    },
  });
}

/**
 * 创建翻译任务
 */
export function useCreateTranslateTaskMutation() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (params: {
      srt_path?: string;
      text?: string;
      source_lang: string;
      target_lang: string;
      use_llm: boolean;
      llm_preset?: string;
    }) => {
      const client = getApiClient();
      const response = await client.post("/api/processing/translate", params);
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.tasks });
    },
  });
}

/**
 * 创建视频增强任务
 */
export function useCreateEnhanceTaskMutation() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (params: {
      video_path: string;
      scale: number;
      model_type: string;
      denoise?: boolean;
      temporal?: boolean;
    }) => {
      const client = getApiClient();
      const response = await client.post("/api/processing/enhance", params);
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.tasks });
    },
  });
}

/**
 * 启动单个任务
 */
export function useStartTaskMutation() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (taskId: string) => {
      const client = getApiClient();
      const response = await client.post(`/api/processing/start/${taskId}`);
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.tasks });
    },
  });
}

/**
 * 获取任务配置（用于编辑回显）
 */
export function useTaskConfigQuery(taskId: string) {
  return useQuery({
    queryKey: ["tasks", taskId, "config"],
    queryFn: async () => {
      const client = getApiClient();
      const response = await client.get(`/api/processing/tasks/${taskId}/config`);
      return response.data;
    },
    enabled: !!taskId,
  });
}

/**
 * 更新任务配置
 */
export function useUpdateTaskConfigMutation() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({
      taskId,
      config,
    }: {
      taskId: string;
      config: Record<string, unknown>;
    }) => {
      const client = getApiClient();
      const response = await client.put(
        `/api/processing/tasks/${taskId}/config`,
        config
      );
      return response.data;
    },
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: queryKeys.tasks });
      queryClient.invalidateQueries({
        queryKey: ["tasks", variables.taskId, "config"],
      });
    },
  });
}

/**
 * 批量启动所有待执行任务
 */
export function useBatchStartMutation() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async () => {
      const client = getApiClient();
      const response = await client.post("/api/processing/batch/start");
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.tasks });
    },
  });
}

/**
 * 批量取消所有运行中任务
 */
export function useBatchCancelMutation() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async () => {
      const client = getApiClient();
      const response = await client.post("/api/processing/batch/cancel");
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.tasks });
    },
  });
}

/**
 * 批量清除已完成/失败/已取消任务
 */
export function useBatchClearMutation() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async () => {
      const client = getApiClient();
      const response = await client.delete("/api/processing/batch/clear");
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.tasks });
    },
  });
}

/**
 * 取消任务
 */
export function useCancelTaskMutation() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (taskId: string) => {
      const client = getApiClient();
      const response = await client.post(`/api/processing/cancel/${taskId}`);
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.tasks });
    },
  });
}

/**
 * 删除任务
 */
export function useDeleteTaskMutation() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (taskId: string) => {
      const client = getApiClient();
      await client.delete(`/api/processing/tasks/${taskId}`);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.tasks });
    },
  });
}

/**
 * 重试失败/取消的任务
 */
export function useRetryTaskMutation() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (taskId: string) => {
      const client = getApiClient();
      const response = await client.post(`/api/processing/retry/${taskId}`);
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.tasks });
    },
  });
}

// ============ Models ============

/**
 * 获取模型状态
 * 仅首次加载 + 页面可见时 refetch
 */
export function useModelsStatusQuery() {
  return useQuery<AllModelsStatus>({
    queryKey: queryKeys.modelsStatus,
    queryFn: async () => {
      const client = getApiClient();
      const response = await client.get("/api/models/status");
      return response.data;
    },
    staleTime: 60000,
  });
}

/**
 * 下载模型
 */
export function useDownloadModelMutation() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (modelId: string) => {
      const client = getApiClient();
      const response = await client.post(`/api/models/download/${modelId}`);
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.modelsStatus });
    },
  });
}

/**
 * 删除模型
 */
export function useDeleteModelMutation() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (modelId: string) => {
      const client = getApiClient();
      await client.delete(`/api/models/${modelId}`);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.modelsStatus });
    },
  });
}

/**
 * 测试 LLM 连接
 */
export function useTestLLMMutation() {
  return useMutation({
    mutationFn: async (preset: string) => {
      const client = getApiClient();
      const response = await client.post("/api/models/llm/test", { preset });
      return response.data;
    },
  });
}

/**
 * 测试所有 LLM 连接
 */
export function useTestAllLLMMutation() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async () => {
      const client = getApiClient();
      const response = await client.post("/api/models/llm/test-all");
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.modelsStatus });
    },
  });
}

// ============ Config ============

/**
 * 获取配置
 */
export function useConfigQuery() {
  return useQuery({
    queryKey: queryKeys.config,
    queryFn: async () => {
      const client = getApiClient();
      const response = await client.get("/api/config/");
      return response.data;
    },
    staleTime: 30000,
  });
}

/**
 * 获取 LLM 预设列表
 */
export function useLLMPresetsQuery() {
  return useQuery({
    queryKey: queryKeys.llmPresets,
    queryFn: async () => {
      const client = getApiClient();
      const response = await client.get("/api/config/llm/presets");
      return response.data;
    },
    staleTime: 30000,
  });
}

/**
 * 更新 LLM 预设配置
 */
export function useUpdateLLMPresetMutation() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({
      presetId,
      ...data
    }: {
      presetId: string;
      api_key?: string;
      base_url?: string;
      model?: string;
    }) => {
      const client = getApiClient();
      const response = await client.put(
        `/api/config/llm/preset/${presetId}`,
        data
      );
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.llmPresets });
      queryClient.invalidateQueries({ queryKey: queryKeys.modelsStatus });
    },
  });
}

/**
 * 删除 LLM 预设
 */
export function useDeleteLLMPresetMutation() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (presetId: string) => {
      const client = getApiClient();
      const response = await client.delete(
        `/api/config/llm/preset/${presetId}`
      );
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.llmPresets });
      queryClient.invalidateQueries({ queryKey: queryKeys.modelsStatus });
    },
  });
}

/**
 * 设置当前使用的 LLM 预设
 */
export function useSetCurrentLLMPresetMutation() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (preset: string) => {
      const client = getApiClient();
      const response = await client.put(
        "/api/config/llm/current-preset",
        { preset }
      );
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.config });
      queryClient.invalidateQueries({ queryKey: queryKeys.modelsStatus });
    },
  });
}

/**
 * 更新配置
 */
export function useUpdateConfigMutation() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (config: Record<string, unknown>) => {
      const client = getApiClient();
      const response = await client.put("/api/config/", config);
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.config });
    },
  });
}

/**
 * 保存配置到磁盘
 */
export function useSaveConfigMutation() {
  return useMutation({
    mutationFn: async () => {
      const client = getApiClient();
      const response = await client.post("/api/config/save");
      return response.data;
    },
  });
}

/**
 * 重新加载配置
 */
export function useReloadConfigMutation() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async () => {
      const client = getApiClient();
      const response = await client.post("/api/config/reload");
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.config });
    },
  });
}
