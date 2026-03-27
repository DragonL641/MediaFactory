/**
 * 任务表单共享常量
 */

// 语言选项
export const LANGUAGE_OPTIONS = [
  { value: "auto", label: "Auto Detect" },
  { value: "en", label: "English" },
  { value: "zh", label: "Chinese" },
  { value: "ja", label: "Japanese" },
  { value: "ko", label: "Korean" },
  { value: "fr", label: "French" },
  { value: "de", label: "German" },
  { value: "es", label: "Spanish" },
  { value: "ru", label: "Russian" },
];

// 目标语言选项（不含 auto）
export const TARGET_LANGUAGE_OPTIONS = LANGUAGE_OPTIONS.filter(
  (opt) => opt.value !== "auto"
);

// 输出格式选项
export const OUTPUT_FORMAT_OPTIONS = [
  { value: "srt", label: "SRT Subtitles" },
  { value: "ass", label: "ASS Subtitles (Styled)" },
  { value: "txt", label: "Plain Text (.txt)" },
];

// ASS 样式预设选项
export const STYLE_PRESET_OPTIONS = [
  { value: "default", label: "Default" },
  { value: "science", label: "Science" },
  { value: "anime", label: "Anime" },
  { value: "news", label: "News" },
];

// 双语布局选项
export const BILINGUAL_LAYOUT_OPTIONS = [
  { value: "translate_on_top", label: "Translation on Top" },
  { value: "original_on_top", label: "Original on Top" },
  { value: "translate_only", label: "Only Translation" },
  { value: "original_only", label: "Only Original" },
];

// 文件类型过滤器
export const FILE_FILTERS = {
  video: [
    { name: "Video Files", extensions: ["mp4", "avi", "mov", "mkv", "wmv", "flv", "webm"] },
  ],
  audio_video: [
    { name: "Audio/Video Files", extensions: ["mp4", "avi", "mov", "mkv", "wav", "mp3", "m4a", "flac", "webm", "ogg"] },
  ],
  srt: [
    { name: "SRT Files", extensions: ["srt"] },
  ],
};
