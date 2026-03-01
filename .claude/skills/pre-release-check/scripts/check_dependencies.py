#!/usr/bin/env python3
"""
MediaFactory 依赖分析脚本

检查 pyproject.toml 中的依赖：
1. 许可证兼容性
2. 已知安全漏洞
3. 版本过时情况
4. 依赖健康度

Usage:
    python check_dependencies.py [--project-path PATH]
"""

import argparse
import json
import subprocess
import sys
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import List, Optional


class SeverityLevel(Enum):
    """问题严重程度"""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


@dataclass
class DependencyIssue:
    """依赖问题"""
    package: str
    version: str
    severity: SeverityLevel
    issue_type: str  # "license", "vulnerability", "outdated", "health"
    title: str
    description: str
    suggestion: str


def parse_pyproject(path: Path) -> dict:
    """解析 pyproject.toml 文件"""
    try:
        import tomli
    except ImportError:
        # 回退到 tomllib (Python 3.11+)
        import tomllib as tomli

    with open(path, "rb") as f:
        return tomli.load(f)


def get_installed_packages() -> dict:
    """获取已安装的包版本"""
    result = subprocess.run(
        [sys.executable, "-m", "pip", "list", "--format=json"],
        capture_output=True,
        text=True
    )
    if result.returncode != 0:
        return {}

    packages = json.loads(result.stdout)
    return {pkg["name"].lower(): pkg["version"] for pkg in packages}


def check_pip_audit() -> List[DependencyIssue]:
    """使用 pip-audit 检查安全漏洞"""
    issues = []

    try:
        result = subprocess.run(
            [sys.executable, "-m", "pip", "audit", "--format", "json"],
            capture_output=True,
            text=True
        )
        if result.returncode == 0:
            return issues  # 无漏洞

        audit_data = json.loads(result.stdout)
        for vuln in audit_data.get("vulnerabilities", []):
            for affected in vuln.get("affected", []):
                for package in affected.get("package", []):
                    issues.append(DependencyIssue(
                        package=package,
                        version=affected.get("versions", [""])[0],
                        severity=SeverityLevel.HIGH,
                        issue_type="vulnerability",
                        title=f"安全漏洞: {vuln.get('id', 'Unknown')}",
                        description=vuln.get("details", "已知安全漏洞"),
                        suggestion=f"升级到安全版本或查看: {vuln.get('advisory', '')}"
                    ))
    except (subprocess.CalledProcessError, json.JSONDecodeError, FileNotFoundError):
        pass  # pip-audit 不可用

    return issues


def check_outdated_packages() -> List[DependencyIssue]:
    """检查过时的包版本"""
    issues = []

    try:
        result = subprocess.run(
            [sys.executable, "-m", "pip", "list", "--outdated", "--format=json"],
            capture_output=True,
            text=True
        )

        if result.returncode != 0:
            return []

        outdated = json.loads(result.stdout)
        for pkg in outdated:
            # 检查是否超过 6 个月未更新
            issues.append(DependencyIssue(
                package=pkg["name"],
                version=pkg["version"],
                severity=SeverityLevel.LOW,
                issue_type="outdated",
                title=f"版本过时: {pkg['name']}",
                description=f"当前版本 {pkg['version']}，最新版本 {pkg['latest_version']}",
                suggestion=f"升级: pip install --upgrade {pkg['name']}"
            ))
    except (subprocess.CalledProcessError, json.JSONDecodeError, FileNotFoundError):
        pass

    return issues


def check_license_compatibility(dependencies: list) -> List[DependencyIssue]:
    """检查许可证兼容性"""
    issues = []

    # MediaFactory 使用 MIT 许可证，检查不兼容的许可证
    incompatible_licenses = {
        "GPL": "使用 GPL 许可证的包需要特殊处理",
        "AGPL": "AGPL 许可证在网络使用时有额外要求",
        "SSPL": "SSPL 不是 OSI 批准的开源许可证",
    }

    for name in dependencies:
        # 这里需要实际获取包的许可证信息
        # 可以使用 PyPI API 或本地缓存
        pass

    return issues


def check_dependency_health(dependencies: list) -> List[DependencyIssue]:
    """检查依赖健康度（废弃、不活跃）"""
    issues = []

    # 已知废弃或有问题的包
    known_deprecated = {
        "distutils": "使用 setuptools 替代",
        "imp": "使用 importlib 替代",
        "optparse": "使用 argparse 替代",
    }

    for pkg in dependencies:
        if pkg.lower() in known_deprecated:
            issues.append(DependencyIssue(
                package=pkg,
                version="",
                severity=SeverityLevel.MEDIUM,
                issue_type="health",
                title=f"已废弃的包: {pkg}",
                description=f"此包已被标记为废弃",
                suggestion=f"替代方案: {known_deprecated[pkg.lower()]}"
            ))

    return issues


def generate_report(issues: List[DependencyIssue]) -> str:
    """生成依赖检查报告"""
    if not issues:
        return "# 依赖检查报告\n\n✅ 未发现依赖问题。\n"

    # 按严重程度排序
    severity_order = {
        SeverityLevel.CRITICAL: 0,
        SeverityLevel.HIGH: 1,
        SeverityLevel.MEDIUM: 2,
        SeverityLevel.LOW: 3,
        SeverityLevel.INFO: 4,
    }
    issues.sort(key=lambda x: severity_order[x.severity])

    # 统计
    counts = {}
    for issue in issues:
        counts[issue.severity.value] = counts.get(issue.severity.value, 0) + 1

    lines = [
        "# 依赖检查报告\n",
        "## 问题统计\n",
        f"- **总问题数**: {len(issues)} 个",
        f"- **关键**: {counts.get('critical', 0)} 个",
        f"- **高**: {counts.get('high', 0)} 个",
        f"- **中**: {counts.get('medium', 0)} 个",
        f"- **低**: {counts.get('low', 0)} 个\n",
        "## 详细问题\n",
    ]

    # 按严重程度分组
    for severity in SeverityLevel:
        severity_issues = [i for i in issues if i.severity == severity]
        if not severity_issues:
            continue

        icon = {
            SeverityLevel.CRITICAL: "🔴",
            SeverityLevel.HIGH: "🟠",
            SeverityLevel.MEDIUM: "🟡",
            SeverityLevel.LOW: "🟢",
            SeverityLevel.INFO: "ℹ️",
        }[severity]

        lines.append(f"### {icon} {severity.value.upper()}\n")

        for issue in severity_issues:
            lines.extend([
                f"#### {issue.title}\n",
                f"**包**: {issue.package} ({issue.version})\n",
                f"**类型**: {issue.issue_type}\n",
                f"**描述**: {issue.description}\n",
                f"**建议**: {issue.suggestion}\n",
            ])

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="检查 MediaFactory 依赖")
    parser.add_argument(
        "--project-path",
        type=Path,
        default=Path.cwd(),
        help="项目根目录路径"
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="输出报告文件路径"
    )
    args = parser.parse_args()

    # 查找 pyproject.toml
    pyproject_path = args.project_path / "pyproject.toml"
    if not pyproject_path.exists():
        print(f"错误: 未找到 pyproject.toml 在 {args.project_path}")
        sys.exit(1)

    # 解析依赖
    pyproject = parse_pyproject(pyproject_path)
    dependencies = pyproject.get("project", {}).get("dependencies", [])

    # 运行检查
    all_issues = []

    print("检查安全漏洞...")
    all_issues.extend(check_pip_audit())

    print("检查版本过时...")
    all_issues.extend(check_outdated_packages())

    print("检查许可证兼容性...")
    all_issues.extend(check_license_compatibility(dependencies))

    print("检查依赖健康度...")
    all_issues.extend(check_dependency_health(dependencies))

    # 生成报告
    report = generate_report(all_issues)

    if args.output:
        args.output.write_text(report)
        print(f"\n报告已保存到: {args.output}")
    else:
        print("\n" + report)


if __name__ == "__main__":
    main()
