---
name: pre-release-check
description: 对MediaFactory项目进行发布前全面代码质量审查，涵盖8个维度：代码质量、架构、性能安全、规范、功能逻辑、用户体验、测试和文档。自动调用open-source-auditor检查开源依赖。当用户提及发布前审查、代码质量检查、或项目发布准备时触发。
---

# MediaFactory 发布前代码质量审查

## 概述

本技能对 MediaFactory 项目进行全面的发布前代码质量审查，覆盖代码质量、架构设计、性能安全、代码规范、功能逻辑、用户体验、测试质量和文档等 8 个维度。

审查将按优先级（🔴关键/🟠高/🟡中/🟢低）分类问题，并提供具体的修复建议和代码示例。默认会调用 open-source-auditor agent 检查开源软件依赖情况。

---

## 工作流程

### Phase 1: 准备阶段

1. **加载项目文档**
   - 读取 `CLAUDE.md` 了解项目架构和约定
   - 读取 `README.md` 了解项目功能和使用方式
   - 读取 `pyproject.toml` 获取依赖和配置信息
   - 获取当前 git commit hash 作为审查版本标识

2. **确认审查范围**
   ```
   请选择审查范围：
   1. 全项目审查（默认）
   2. 特定模块审查（请指定模块路径）
   ```

3. **确认依赖检查**
   ```
   是否需要检查开源依赖？（默认：是）
   - 这将调用 open-source-auditor agent 进行全面的依赖审查
   ```

### Phase 2: 多维度分析

并行执行以下检查（根据用户选择）：

| 维度 | 检查内容 | 参考文档 |
|------|----------|----------|
| 代码质量 | 冗余代码、坏味道、资源管理、错误处理 | `references/check_dimensions.md` |
| 架构问题 | 耦合度、内聚性、设计模式 | `references/check_dimensions.md` |
| 性能与安全 | 性能风险、安全隐患、可扩展性 | `references/check_dimensions.md` |
| 代码规范 | 一致性、最佳实践、类型安全 | `references/check_dimensions.md` |
| 功能逻辑 | 业务逻辑错误、数据一致性、API设计 | `references/check_dimensions.md` |
| 用户体验 | 前端UX、API UX、监控可观测性 | `references/check_dimensions.md` |
| 测试质量 | 测试覆盖、测试质量、测试环境 | `references/check_dimensions.md` |
| 文档 | 代码注释、文档同步、部署文档 | `references/check_dimensions.md` |
| 开源依赖 | 依赖合规性、安全漏洞、版本过时 | open-source-auditor agent |

**特别说明**：MediaFactory 项目是一个轻量化的本地多媒体处理工具，审查时应重点关注：
- 功能正确性优于性能优化
- 代码可维护性优于过度设计
- 避免自研可用现成开源库替代的功能

### Phase 3: 报告生成

**重要**：所有报告必须生成到项目根目录（`/Users/liuziyi/IdeaProjects/VideoDub/`）

生成结构化的审查报告 `PRE_RELEASE_CHECK.md`，包含：

1. **执行摘要** - 问题总数、各级别问题数量
2. **按优先级分类** - 🔴关键 / 🟠高 / 🟡中 / 🟢低
3. **按维度分类** - 9 个维度的详细问题列表
4. **修复路线图** - 按优先级排序的修复建议

**辅助脚本输出路径**：
```bash
# 确保脚本输出到项目根目录
python .claude/skills/pre-release-check/scripts/analyze_complexity.py \
    --path src/mediafactory \
    --output /Users/liuziyi/IdeaProjects/VideoDub/COMPLEXITY_REPORT.md

python .claude/skills/pre-release-check/scripts/check_consistency.py \
    --path src/mediafactory \
    --output /Users/liuziyi/IdeaProjects/VideoDub/CONSISTENCY_REPORT.md

python .claude/skills/pre-release-check/scripts/check_dependencies.py \
    --project-path /Users/liuziyi/IdeaProjects/VideoDub \
    --output /Users/liuziyi/IdeaProjects/VideoDub/DEPENDENCY_AUDIT_REPORT.md
```

---

## 详细执行步骤

### Phase 1: 准备阶段

```python
# 1. 读取项目文档
claude_documents = [
    "CLAUDE.md",
    "README.md",
    "pyproject.toml"
]

for doc in claude_documents:
    read_file(doc)

# 2. 获取 git 版本信息
git_commit = run_bash("git rev-parse --short HEAD")

# 3. 询问审查范围（如果用户未指定）
if not user_specified_scope:
    use_ask_user_question([
        {"全项目审查": "审查所有模块"},
        {"特定模块": "仅审查指定路径的模块"}
    ])

# 4. 确认依赖检查（除非用户明确跳过）
if not skip_dependency_check:
    use_ask_user_question([
        {"检查依赖": "调用 open-source-auditor agent"},
        {"跳过依赖": "不检查开源依赖"}
    ])
```

### Phase 2: 多维度分析

#### 2.1 代码库探索

根据审查范围使用 Explore agent 进行代码库探索：

```python
# 全项目审查
Task(
    subagent_type="Explore",
    prompt="探索 MediaFactory 项目的完整代码库结构，关注：
    - src/mediafactory/ 下的所有模块
    - 架构层次（GUI层、服务层、工具层、流水线层、引擎层）
    - 关键设计模式和约定
    返回完整的模块结构报告。"
)

# 特定模块审查
Task(
    subagent_type="Explore",
    prompt=f"探索以下模块的代码结构：{user_specified_modules}"
)
```

#### 2.2 八维度检查

对每个维度执行以下检查流程：

```python
def check_dimension(dimension_name: str) -> List[Issue]:
    """
    执行单维度检查

    Returns:
        List[Issue]: 按优先级排序的问题列表
    """
    issues = []

    # 1. 使用 Grep 搜索特定模式
    patterns = load_dimension_patterns(dimension_name)
    for pattern in patterns:
        results = grep(pattern)
        issues.extend(analyze_pattern_results(results))

    # 2. 读取关键文件进行深度分析
    key_files = get_key_files_for_dimension(dimension_name)
    for file_path in key_files:
        content = read_file(file_path)
        issues.extend(analyze_file_content(content, dimension_name))

    # 3. 使用 Glob 查找潜在问题文件
    suspicious_patterns = load_suspicious_patterns(dimension_name)
    for pattern in suspicious_patterns:
        files = glob(pattern)
        issues.extend(analyze_files(files, dimension_name))

    return prioritize_issues(issues)
```

#### 2.3 开源依赖检查

**默认调用 open-source-auditor agent**：

```python
if check_dependencies:
    Task(
        subagent_type="open-source-auditor",
        prompt="对 MediaFactory 项目进行全面的开源依赖审计：

        项目信息：
        - 项目类型：Python 多媒体处理工具
        - 依赖文件：pyproject.toml
        - 构建工具：PyInstaller

        请检查：
        1. 依赖许可证合规性
        2. 已知安全漏洞
        3. 版本过时情况
        4. 依赖健康度（维护状态）
        "
    )
```

**回退方案**：如果 open-source-auditor 不可用，使用本地脚本：

```bash
# 确保输出到项目根目录
python .claude/skills/pre-release-check/scripts/check_dependencies.py \
    --project-path /Users/liuziyi/IdeaProjects/VideoDub \
    --output /Users/liuziyi/IdeaProjects/VideoDub/DEPENDENCY_AUDIT_REPORT.md
```

### Phase 3: 报告生成

#### 3.1 输出路径规范

**所有报告必须生成到项目根目录**：
```
/Users/liuziyi/IdeaProjects/VideoDub/
├── PRE_RELEASE_CHECK.md           # 主报告
├── COMPLEXITY_REPORT.md           # 复杂度分析报告
├── CONSISTENCY_REPORT.md          # 一致性检查报告
└── DEPENDENCY_AUDIT_REPORT.md     # 依赖审计报告
```

#### 3.2 报告模板

```markdown
# MediaFactory 发布前代码质量审查报告

**生成时间**: {timestamp}
**审查范围**: {scope}
**审查版本**: {git_commit}

## 执行摘要

- **总问题数**: {total_issues}
- **关键问题**: {critical_count} 个
- **高优先级**: {high_count} 个
- **中优先级**: {medium_count} 个
- **低优先级**: {low_count} 个

## 按优先级分类

### 🔴 关键问题 (必须修复)

{critical_issues_list}

### 🟠 高优先级 (强烈建议修复)

{high_priority_issues_list}

### 🟡 中优先级 (建议修复)

{medium_priority_issues_list}

### 🟢 低优先级 (可选优化)

{low_priority_issues_list}

## 按维度分类

### 1. 代码质量问题
{dimension_1_issues}

### 2. 架构问题
{dimension_2_issues}

### 3. 性能与安全
{dimension_3_issues}

### 4. 代码规范
{dimension_4_issues}

### 5. 功能逻辑
{dimension_5_issues}

### 6. 用户体验
{dimension_6_issues}

### 7. 测试质量
{dimension_7_issues}

### 8. 文档
{dimension_8_issues}

### 9. 开源依赖
{dependency_issues}

## 修复路线图

### 立即修复（本周内）
1. {critical_issue_1}
2. {critical_issue_2}

### 近期修复（两周内）
1. {high_priority_issue_1}
2. {high_priority_issue_2}

### 中期优化（一个月内）
1. {medium_priority_issue_1}
2. {medium_priority_issue_2}

### 长期优化（有时间时）
1. {low_priority_issue_1}
2. {low_priority_issue_2}

---

*报告由 pre-release-check skill 生成*
```

#### 3.3 问题条目格式

每个问题应包含以下字段：

```markdown
#### [{issue_id}] {brief_title}

**优先级**: 🔴关键 / 🟠高 / 🟡中 / 🟢低
**维度**: [dimension_name]
**位置**: `file_path:line_number`
**影响范围**: [impact_description]

**问题描述**:
[detailed_problem_description]

**修复建议**:
[specific_suggestions_with_code_example]

```python
# 示例代码或修复方案
def fixed_version():
    # 修复说明
    pass
```
```

---

## open-source-auditor 集成

### 调用时机

在 Phase 2 开始时，与八维度检查并行执行。

### 调用参数

```python
Task(
    subagent_type="open-source-auditor",
    prompt=f"""
请对 MediaFactory 项目进行全面的开源依赖审计。

项目上下文：
- 项目路径：{project_root}
- 依赖配置：pyproject.toml
- 项目类型：Python 多媒体处理工具
- 构建方式：PyInstaller 冻结构建

审计重点：
1. 许可证合规性（MIT/Apache-2.0 兼容性）
2. 已知安全漏洞（CVE 检查）
3. 依赖版本过时（超过 6 个月未更新）
4. 维护健康度（废弃/不活跃的包）
5. 传递性依赖风险

请返回结构化的审计结果，包含问题优先级和修复建议。
"""
)
```

### 回退处理

```python
try:
    agent_result = invoke_agent("open-source-auditor", {...})
    dependency_issues = parse_agent_result(agent_result)
except AgentUnavailable:
    # 回退到本地脚本
    run_bash("python .claude/skills/pre-release-check/scripts/check_dependencies.py")
    dependency_issues = parse_script_output()
```

---

## 检查维度详解

详细的检查项目和标准请参考：

- `references/check_dimensions.md` - 8 维度详细检查指南
- `references/report_template.md` - 报告生成模板
- `references/mediafactory_context.md` - MediaFactory 项目上下文
- `references/python_best_practices.md` - Python 最佳实践参考

---

## 辅助脚本

| 脚本 | 功能 | 使用方式 |
|------|------|----------|
| `scripts/check_dependencies.py` | 依赖分析 | `python scripts/check_dependencies.py` |
| `scripts/analyze_complexity.py` | 圈复杂度分析 | `python scripts/analyze_complexity.py src/` |
| `scripts/check_consistency.py` | 一致性检查 | `python scripts/check_consistency.py` |

---

## 快速开始

### 全项目审查（默认）

```
请对 MediaFactory 项目进行发布前代码质量审查
```

### 跳过依赖检查

```
请进行发布前审查，不需要检查开源依赖
```

### 特定模块审查

```
请检查 src/mediafactory/engine/ 和 src/mediafactory/pipeline/ 模块的代码质量
```

### 仅检查依赖

```
请检查项目的开源依赖情况
```
