#!/usr/bin/env python3
"""
MediaFactory 代码一致性检查脚本

检查代码一致性：
1. 命名风格一致性
2. 导入顺序一致性
3. 字符串引号一致性
4. 格式一致性（空行、缩进）

Usage:
    python check_consistency.py [--path PATH]
"""

import argparse
import ast
import re
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional


@dataclass
class ConsistencyIssue:
    """一致性问题"""
    file_path: str
    line_number: int
    issue_type: str
    description: str
    suggestion: str


class ConsistencyChecker:
    """一致性检查器"""

    def __init__(self):
        self.issues: List[ConsistencyIssue] = []

    def check_file(self, file_path: Path) -> List[ConsistencyIssue]:
        """检查单个文件"""
        self.issues = []
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                lines = content.split('\n')

            # 检查命名一致性
            self._check_naming_consistency(file_path, lines, content)

            # 检查导入顺序
            self._check_import_order(file_path, content)

            # 检查字符串引号一致性
            self._check_string_quotes(file_path, content)

            # 检查格式一致性
            self._check_format_consistency(file_path, lines)

        except (SyntaxError, UnicodeDecodeError):
            pass

        return self.issues

    def _check_naming_consistency(self, file_path: Path, lines: List[str], content: str):
        """检查命名一致性"""
        # 检查类命名（应该是 PascalCase）
        class_pattern = re.compile(r'^class\s+([a-z][a-zA-Z0-9_]*)\s*:')
        for i, line in enumerate(lines, 1):
            match = class_pattern.match(line.strip())
            if match:
                self.issues.append(ConsistencyIssue(
                    file_path=str(file_path),
                    line_number=i,
                    issue_type="naming",
                    description=f"类名 `{match.group(1)}` 应使用 PascalCase",
                    suggestion=f"重命名为 `{match.group(1).title().replace('_', '')}`"
                ))

        # 检查函数命名（应该是 snake_case）
        func_pattern = re.compile(r'^def\s+([A-Z][a-zA-Z0-9_]*)\s*\(')
        for i, line in enumerate(lines, 1):
            match = func_pattern.match(line.strip())
            if match and not match.group(1).startswith('__'):  # 排除魔术方法
                self.issues.append(ConsistencyIssue(
                    file_path=str(file_path),
                    line_number=i,
                    issue_type="naming",
                    description=f"函数名 `{match.group(1)}` 应使用 snake_case",
                    suggestion=f"重命名为 `{self._to_snake_case(match.group(1))}`"
                ))

    def _check_import_order(self, file_path: Path, content: str):
        """检查导入顺序"""
        try:
            tree = ast.parse(content, filename=str(file_path))
        except SyntaxError:
            return

        imports = []
        for node in ast.walk(tree):
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                if isinstance(node, ast.ImportFrom) and node.module:
                    module = node.module.split('.')[0]
                elif isinstance(node, ast.Import) and node.names:
                    module = node.names[0].name.split('.')[0]
                else:
                    continue

                imports.append({
                    'line': node.lineno,
                    'module': module,
                    'type': self._get_import_type(module),
                })

        # 检查顺序：标准库 -> 第三方 -> 本地
        prev_type = None
        for imp in imports:
            if prev_type and imp['type'] < prev_type:
                self.issues.append(ConsistencyIssue(
                    file_path=str(file_path),
                    line_number=imp['line'],
                    issue_type="import_order",
                    description=f"导入 `{imp['module']}` 的顺序不正确",
                    suggestion=f"将导入按顺序排列：标准库、第三方、本地"
                ))
            prev_type = imp['type']

    def _check_string_quotes(self, file_path: Path, content: str):
        """检查字符串引号一致性"""
        # 统计单引号和双引号的使用
        single_quotes = len(re.findall(r"'[^']*'", content))
        double_quotes = len(re.findall(r'"[^"]*"', content))

        # 如果两种都有使用，检查一致性
        if single_quotes > 0 and double_quotes > 0:
            # 计算比例
            total = single_quotes + double_quotes
            single_ratio = single_quotes / total

            # 如果一种占主导（>90%），标记另一种为不一致
            if single_ratio > 0.9:
                self.issues.append(ConsistencyIssue(
                    file_path=str(file_path),
                    line_number=1,
                    issue_type="string_quotes",
                    description=f"混用单引号和双引号（单引号 {single_ratio:.1%}）",
                    suggestion="统一使用单引号"
                ))
            elif single_ratio < 0.1:
                self.issues.append(ConsistencyIssue(
                    file_path=str(file_path),
                    line_number=1,
                    issue_type="string_quotes",
                    description=f"混用单引号和双引号（双引号 {(1-single_ratio):.1%}）",
                    suggestion="统一使用双引号"
                ))

    def _check_format_consistency(self, file_path: Path, lines: List[str]):
        """检查格式一致性"""
        # 检查行尾空格
        for i, line in enumerate(lines, 1):
            if line.endswith(' ') or line.endswith('\t'):
                self.issues.append(ConsistencyIssue(
                    file_path=str(file_path),
                    line_number=i,
                    issue_type="trailing_whitespace",
                    description="行尾有多余空格",
                    suggestion="删除行尾空格"
                ))

        # 检查连续空行（超过 2 行）
        consecutive_empty = 0
        for i, line in enumerate(lines, 1):
            if line.strip() == '':
                consecutive_empty += 1
            else:
                if consecutive_empty > 2:
                    self.issues.append(ConsistencyIssue(
                        file_path=str(file_path),
                        line_number=i - consecutive_empty,
                        issue_type="consecutive_blank_lines",
                        description=f"有 {consecutive_empty} 行连续空行",
                        suggestion="减少到最多 2 行"
                    ))
                consecutive_empty = 0

    def _get_import_type(self, module: str) -> int:
        """获取导入类型（0=标准库，1=第三方，2=本地）"""
        # 标准库模块（部分）
        stdlib_modules = {
            'os', 'sys', 'pathlib', 'typing', 'dataclasses', 'enum',
            'collections', 'itertools', 'functools', 'datetime',
            'json', 're', 'subprocess', 'threading', 'time',
        }

        if module in stdlib_modules:
            return 0
        elif module.startswith('mediafactory'):
            return 2
        else:
            return 1

    def _to_snake_case(self, name: str) -> str:
        """转换为 snake_case"""
        # 处理连续大写字母（如 HTTPServer -> http_server）
        result = re.sub('([A-Z]+)([A-Z][a-z])', r'\1_\2', name)
        # 处理小写字母后跟大写字母
        result = re.sub('([a-z0-9])([A-Z])', r'\1_\2', result)
        return result.lower()


def find_python_files(path: Path) -> List[Path]:
    """查找所有 Python 文件"""
    if path.is_file() and path.suffix == '.py':
        return [path]

    python_files = []
    for item in path.rglob('*.py'):
        if 'venv' not in str(item) and 'build' not in str(item):
            python_files.append(item)
    return python_files


def generate_report(issues: List[ConsistencyIssue]) -> str:
    """生成一致性检查报告"""
    if not issues:
        return "# 代码一致性检查报告\n\n✅ 未发现一致性问题。\n"

    # 统计
    type_counts = defaultdict(int)
    file_counts = defaultdict(int)
    for issue in issues:
        type_counts[issue.issue_type] += 1
        file_counts[issue.file_path] += 1

    lines = [
        "# 代码一致性检查报告\n",
        "## 问题统计\n",
        f"- **总问题数**: {len(issues)} 个",
        f"- **涉及文件**: {len(file_counts)} 个\n",
        "### 按类型\n",
    ]

    for issue_type, count in sorted(type_counts.items()):
        lines.append(f"- **{issue_type}**: {count} 个")

    lines.extend([
        "\n### 按文件\n",
    ])

    for file_path, count in sorted(file_counts.items(), key=lambda x: x[1], reverse=True)[:10]:
        lines.append(f"- `{file_path}`: {count} 个问题")

    lines.extend([
        "\n## 详细问题\n",
    ])

    # 按类型分组
    grouped = defaultdict(list)
    for issue in issues:
        grouped[issue.issue_type].append(issue)

    for issue_type in sorted(grouped.keys()):
        lines.append(f"\n### {issue_type.replace('_', ' ').title()}\n")

        # 每个类型最多显示 20 个问题
        for issue in grouped[issue_type][:20]:
            lines.extend([
                f"#### `{issue.file_path}:{issue.line_number}`\n",
                f"**描述**: {issue.description}\n",
                f"**建议**: {issue.suggestion}\n",
            ])

        if len(grouped[issue_type]) > 20:
            lines.append(f"\n*还有 {len(grouped[issue_type]) - 20} 个类似问题未显示*\n")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="检查代码一致性")
    parser.add_argument(
        "--path",
        type=Path,
        default=Path.cwd(),
        help="要检查的路径（文件或目录）"
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="输出报告文件路径"
    )
    args = parser.parse_args()

    print(f"检查路径: {args.path}")

    python_files = find_python_files(args.path)
    print(f"找到 {len(python_files)} 个 Python 文件")

    checker = ConsistencyChecker()
    all_issues = []

    for file_path in python_files:
        issues = checker.check_file(file_path)
        all_issues.extend(issues)

    report = generate_report(all_issues)

    if args.output:
        args.output.write_text(report, encoding='utf-8')
        print(f"\n报告已保存到: {args.output}")
    else:
        print("\n" + report)


if __name__ == "__main__":
    main()
