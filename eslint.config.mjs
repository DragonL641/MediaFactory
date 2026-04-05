import js from "@eslint/js";
import tseslint from "typescript-eslint";
import reactPlugin from "eslint-plugin-react";
import reactHooksPlugin from "eslint-plugin-react-hooks";
import reactRefreshPlugin from "eslint-plugin-react-refresh";

export default tseslint.config(
  // 全局忽略
  {
    ignores: [
      "dist/**",
      "release/**",
      "out/**",
      "node_modules/**",
      "src/electron/renderer/src/locales/**",
    ],
  },

  // 基础 JS 推荐规则
  js.configs.recommended,

  // TypeScript 文件配置
  ...tseslint.configs.recommended,

  // React 相关配置（renderer 目录）
  {
    files: ["src/electron/renderer/**/*.{ts,tsx}"],
    plugins: {
      react: reactPlugin,
      "react-hooks": reactHooksPlugin,
      "react-refresh": reactRefreshPlugin,
    },
    settings: {
      react: {
        version: "detect",
      },
    },
    rules: {
      // React Hooks — 必须规则
      "react-hooks/rules-of-hooks": "error",
      "react-hooks/exhaustive-deps": "error",

      // React Refresh — 仅检查组件导出
      "react-refresh/only-export-components": [
        "warn",
        { allowConstantExport: true },
      ],
    },
  },

  // 全局 TypeScript 规则覆盖
  {
    files: ["src/electron/**/*.{ts,tsx}"],
    rules: {
      // 允许 _ 前缀的未使用变量
      "@typescript-eslint/no-unused-vars": [
        "error",
        { argsIgnorePattern: "^_", varsIgnorePattern: "^_" },
      ],

      // 关闭 no-explicit-any — 原型阶段，逐步收紧
      "@typescript-eslint/no-explicit-any": "off",

      // 关闭 no-empty-object-type — Ant Design 组件 props 常见
      "@typescript-eslint/no-empty-object-type": "off",
    },
  }
);
