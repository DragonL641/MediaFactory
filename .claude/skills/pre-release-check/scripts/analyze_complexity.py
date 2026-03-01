#!/usr/bin/env python3
"""
MediaFactory 代码复杂度分析脚本

分析代码复杂度：
1. 圈复杂度 (Cyclomatic Complexity)
2. 函数长度
3. 嵌套深度
4. 类长度

Usage:
    python analyze_complexity.py [--path PATH] [--threshold N]
"""

import argparse
import ast
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional


@dataclass
class ComplexityIssue:
    """复杂度问题"""
    file_path: str
    line_number: int
    name: str
    issue_type: str  # "function_length", "nesting_depth", "cyclomatic", "class_length"
    value: int
    threshold: int
    severity: str


class ComplexityAnalyzer(ast.NodeVisitor):
    """AST 复杂度分析器"""

    def __init__(self, file_path: str, thresholds: dict):
        self.file_path = file_path
        self.thresholds = thresholds
        self.issues: List[ComplexityIssue] = []
        self.current_class: Optional[str] = None
        self.nesting_level = 0

    def visit_ClassDef(self, node: ast.ClassDef):
        """检查类长度"""
        old_class = self.current_class
        self.current_class = node.name

        # 计算类中的行数
        if hasattr(node, 'end_lineno') and node.lineno:
            class_length = node.end_lineno - node.lineno
            threshold = self.thresholds.get('class_length', 300)
            if class_length > threshold:
                self.issues.append(ComplexityIssue(
                    file_path=self.file_path,
                    line_number=node.lineno,
                    name=node.name,
                    issue_type="class_length",
                    value=class_length,
                    threshold=threshold,
                    severity="high" if class_length > threshold * 1.5 else "medium"
                ))

        self.generic_visit(node)
        self.current_class = old_class

    def visit_FunctionDef(self, node: ast.FunctionDef):
        """检查函数复杂度"""
        # 计算函数长度
        if hasattr(node, 'end_lineno'):
            func_length = node.end_lineno - node.lineno
            threshold = self.thresholds.get('function_length', 50)
            if func_length > threshold:
                self.issues.append(ComplexityIssue(
                    file_path=self.file_path,
                    line_number=node.lineno,
                    name=f"{self.current_class}.{node.name}" if self.current_class else node.name,
                    issue_type="function_length",
                    value=func_length,
                    threshold=threshold,
                    severity="high" if func_length > threshold * 2 else "medium"
                ))

        # 计算圈复杂度
        complexity = self._calculate_cyclomatic_complexity(node)
        threshold = self.thresholds.get('cyclomatic', 10)
        if complexity > threshold:
            self.issues.append(ComplexityIssue(
                file_path=self.file_path,
                line_number=node.lineno,
                name=f"{self.current_class}.{node.name}" if self.current_class else node.name,
                issue_type="cyclomatic",
                value=complexity,
                threshold=threshold,
                severity="high" if complexity > threshold * 2 else "medium"
            ))

        # 检查嵌套深度
        max_nesting = self._calculate_max_nesting(node)
        threshold = self.thresholds.get('nesting_depth', 4)
        if max_nesting > threshold:
            self.issues.append(ComplexityIssue(
                file_path=self.file_path,
                line_number=node.lineno,
                name=f"{self.current_class}.{node.name}" if self.current_class else node.name,
                issue_type="nesting_depth",
                value=max_nesting,
                threshold=threshold,
                severity="high" if max_nesting > threshold * 1.5 else "medium"
            ))

        self.generic_visit(node)

    def _calculate_cyclomatic_complexity(self, node: ast.FunctionDef) -> int:
        """计算圈复杂度"""
        complexity = 1  # 基础复杂度

        for child in ast.walk(node):
            # 每个决策点增加复杂度
            if isinstance(child, (ast.If, ast.While, ast.For, ast.AsyncFor)):
                complexity += 1
            elif isinstance(child, ast.ExceptHandler):
                complexity += 1
            elif isinstance(child, (ast.And, ast.Or)):
                complexity += 1
            elif isinstance(child, ast.Match):  # Python 3.10+
                complexity += len(child.cases)

        return complexity

    def _calculate_max_nesting(self, node: ast.FunctionDef) -> int:
        """计算最大嵌套深度"""
        max_depth = 0

        def count_nesting(n, depth=0):
            nonlocal max_depth
            max_depth = max(max_depth, depth)
            for child in ast.iter_child_nodes(n):
                if isinstance(child, (ast.If, ast.While, ast.For, ast.AsyncFor,
                                      ast.With, ast.AsyncWith, ast.Try,
                                      ast.Lambda, ast.ListComp, ast.DictComp,
                                      ast.SetComp, ast.GeneratorExp)):
                    count_nesting(child, depth + 1)
                else:
                    count_nesting(child, depth)

        count_nesting(node)
        return max_depth


def analyze_file(file_path: Path, thresholds: dict) -> List[ComplexityIssue]:
    """分析单个文件"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            source = f.read()

        tree = ast.parse(source, filename=str(file_path))
        analyzer = ComplexityAnalyzer(str(file_path), thresholds)
        analyzer.visit(tree)
        return analyzer.issues
    except (SyntaxError, UnicodeDecodeError) as e:
        return []


def find_python_files(path: Path) -> List[Path]:
    """查找所有 Python 文件"""
    if path.is_file() and path.suffix == '.py':
        return [path]

    python_files = []
    for item in path.rglob('*.py'):
        # 跳过虚拟环境和构建目录
        if 'venv' not in str(item) and 'build' not in str(item):
            python_files.append(item)
    return python_files


def generate_report(issues: List[ComplexityIssue], thresholds: dict) -> str:
    """生成复杂度分析报告"""
    if not issues:
        return "# 代码复杂度分析报告\n\n✅ 未发现复杂度问题。\n"

    # 统计
    type_counts = {}
    severity_counts = {}
    for issue in issues:
        type_counts[issue.issue_type] = type_counts.get(issue.issue_type, 0) + 1
        severity_counts[issue.severity] = severity_counts.get(issue.severity, 0) + 1

    lines = [
        "# 代码复杂度分析报告\n",
        "## 问题统计\n",
        f"- **总问题数**: {len(issues)} 个\n",
        "### 按类型\n",
    ]

    for issue_type, count in sorted(type_counts.items()):
        lines.append(f"- **{issue_type}**: {count} 个")

    lines.extend([
        "\n### 按严重程度\n",
        f"- **高**: {severity_counts.get('high', 0)} 个",
        f"- **中**: {severity_counts.get('medium', 0)} 个\n",
        "## 详细问题\n",
    ])

    # 按严重程度和类型排序
    severity_order = {"high": 0, "medium": 1}
    issues.sort(key=lambda x: (severity_order.get(x.severity, 2), x.issue_type, x.value))

    for issue in issues:
        icon = "🟠" if issue.severity == "high" else "🟡"
        lines.extend([
            f"### {icon} {issue.issue_type.replace('_', ' ').title()}\n",
            f"**位置**: `{issue.file_path}:{issue.line_number}`\n",
            f"**名称**: `{issue.name}`\n",
            f"**当前值**: {issue.value}",
            f"**阈值**: {issue.threshold}\n",
            "#### 修复建议\n",
        ])

        if issue.issue_type == "function_length":
            lines.append("函数过长，建议拆分为多个小函数。\n")
        elif issue.issue_type == "nesting_depth":
            lines.append("嵌套过深，建议使用提前返回或提取函数。\n")
        elif issue.issue_type == "cyclomatic":
            lines.append("圈复杂度过高，建议简化条件逻辑。\n")
        elif issue.issue_type == "class_length":
            lines.append("类过长，建议拆分为多个类或提取混入。\n")

        lines.append("---\n")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="分析代码复杂度")
    parser.add_argument(
        "--path",
        type=Path,
        default=Path.cwd(),
        help="要分析的路径（文件或目录）"
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="输出报告文件路径"
    )
    parser.add_argument(
        "--function-length",
        type=int,
        default=50,
        help="函数长度阈值"
    )
    parser.add_argument(
        "--nesting-depth",
        type=int,
        default=4,
        help="嵌套深度阈值"
    )
    parser.add_argument(
        "--cyclomatic",
        type=int,
        default=10,
        help="圈复杂度阈值"
    )
    parser.add_argument(
        "--class-length",
        type=int,
        default=300,
        help="类长度阈值"
    )
    args = parser.parse_args()

    thresholds = {
        'function_length': args.function_length,
        'nesting_depth': args.nesting_depth,
        'cyclomatic': args.cyclomatic,
        'class_length': args.class_length,
    }

    print(f"分析路径: {args.path}")

    python_files = find_python_files(args.path)
    print(f"找到 {len(python_files)} 个 Python 文件")

    all_issues = []
    for file_path in python_files:
        issues = analyze_file(file_path, thresholds)
        all_issues.extend(issues)

    report = generate_report(all_issues, thresholds)

    if args.output:
        args.output.write_text(report, encoding='utf-8')
        print(f"\n报告已保存到: {args.output}")
    else:
        print("\n" + report)


if __name__ == "__main__":
    main()
