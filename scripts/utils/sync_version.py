#!/usr/bin/env python3
"""
版本号同步脚本

用法:
    python scripts/utils/sync_version.py 0.2.1       # 更新所有文件版本号
    python scripts/utils/sync_version.py --check     # 检查版本号一致性
    python scripts/utils/sync_version.py --current   # 显示当前版本号
"""

import argparse
import re
import sys
from pathlib import Path

# 项目根目录
PROJECT_ROOT = Path(__file__).parent.parent.parent

# 需要同步的文件配置
# key: 文件路径（相对于项目根目录）
# value: (匹配模式, 替换模板)
VERSION_FILES = {
    "pyproject.toml": (
        r'^version = "(\d+\.\d+\.\d+)"',
        'version = "{version}"',
    ),
    "src/electron/package.json": (
        r'"version":\s*"(\d+\.\d+\.\d+)"',
        '"version": "{version}"',
    ),
    "README.md": [
        (r'dist/MediaFactory-(\d+\.\d+\.\d+)\.dmg', 'dist/MediaFactory-{version}.dmg'),
        (r'dist/MediaFactory-Setup-(\d+\.\d+\.\d+)\.exe', 'dist/MediaFactory-Setup-{version}.exe'),
        (r'PRODUCT_VERSION = "(\d+\.\d+\.\d+)"', 'PRODUCT_VERSION = "{version}"'),
        (r'#define AppVersion "(\d+\.\d+\.\d+)"', '#define AppVersion "{version}"'),
    ],
    "README_zh.md": [
        (r'dist/MediaFactory-(\d+\.\d+\.\d+)\.dmg', 'dist/MediaFactory-{version}.dmg'),
        (r'dist/MediaFactory-Setup-(\d+\.\d+\.\d+)\.exe', 'dist/MediaFactory-Setup-{version}.exe'),
        (r'PRODUCT_VERSION = "(\d+\.\d+\.\d+)"', 'PRODUCT_VERSION = "{version}"'),
        (r'#define AppVersion "(\d+\.\d+\.\d+)"', '#define AppVersion "{version}"'),
    ],
    "BUILD.md": [
        (r'version = "(\d+\.\d+\.\d+)"', 'version = "{version}"'),
        (r'git-cliff --tag v(\d+\.\d+\.\d+) --unreleased', 'git-cliff --tag v{version} --unreleased'),
        (r'bump version to (\d+\.\d+\.\d+)', 'bump version to {version}'),
        (r'git tag v(\d+\.\d+\.\d+)', 'git tag v{version}'),
        (r'git push origin v(\d+\.\d+\.\d+)', 'git push origin v{version}'),
        (r'git-cliff v[\d.]+\.\.v(\d+\.\d+\.\d+)', 'git-cliff v0.1.0..v{version}'),
        (r'git-cliff --tag v(\d+\.\d+\.\d+) --prepend', 'git-cliff --tag v{version} --prepend'),
        (r'git-cliff --tag v(\d+\.\d+\.\d+) --unreleased', 'git-cliff --tag v{version} --unreleased'),
    ],
    "scripts/pyinstaller/README_PYINSTALLER.md": [
        (r'MediaFactory-(\d+\.\d+\.\d+)-\{platform\}\.zip', 'MediaFactory-{version}-{{platform}}.zip'),
        (r'PRODUCT_VERSION = "(\d+\.\d+\.\d+)"', 'PRODUCT_VERSION = "{version}"'),
        (r'MediaFactory-Installer-(\d+\.\d+\.\d+)\.pkg', 'MediaFactory-Installer-{version}.pkg'),
        (r'MediaFactory-Setup-(\d+\.\d+\.\d+)\.exe', 'MediaFactory-Setup-{version}.exe'),
    ],
}


def get_current_version() -> str | None:
    """从 pyproject.toml 获取当前版本号"""
    pyproject_path = PROJECT_ROOT / "pyproject.toml"
    if not pyproject_path.exists():
        print(f"❌ 文件不存在: {pyproject_path}")
        return None

    content = pyproject_path.read_text(encoding="utf-8")
    match = re.search(r'^version = "(\d+\.\d+\.\d+)"', content, re.MULTILINE)
    if match:
        return match.group(1)
    return None


def check_consistency() -> bool:
    """检查所有文件版本号是否一致"""
    current_version = get_current_version()
    if not current_version:
        print("❌ 无法获取当前版本号")
        return False

    print(f"📋 当前版本: {current_version}")
    print("-" * 50)

    all_consistent = True

    for file_path, patterns in VERSION_FILES.items():
        if file_path == "pyproject.toml":
            continue  # 跳过源文件

        full_path = PROJECT_ROOT / file_path
        if not full_path.exists():
            print(f"⚠️  文件不存在: {file_path}")
            continue

        content = full_path.read_text(encoding="utf-8")

        # 处理单个模式或模式列表
        if isinstance(patterns, tuple):
            patterns = [patterns]

        file_consistent = True
        for pattern, _ in patterns:
            matches = re.findall(pattern, content)
            for match in matches:
                if match != current_version:
                    print(f"❌ {file_path}: 发现不一致版本 '{match}'")
                    file_consistent = False
                    all_consistent = False

        if file_consistent:
            print(f"✅ {file_path}")

    print("-" * 50)
    if all_consistent:
        print("✅ 所有版本号一致")
    else:
        print("❌ 存在不一致的版本号")

    return all_consistent


def update_version(new_version: str, dry_run: bool = False) -> bool:
    """更新所有文件中的版本号"""
    # 验证版本号格式
    if not re.match(r"^\d+\.\d+\.\d+$", new_version):
        print(f"❌ 无效版本号格式: {new_version}")
        return False

    if dry_run:
        print(f"🔍 [DRY RUN] 将更新版本号到: {new_version}")
    else:
        print(f"📝 更新版本号到: {new_version}")

    print("-" * 50)

    for file_path, patterns in VERSION_FILES.items():
        full_path = PROJECT_ROOT / file_path
        if not full_path.exists():
            print(f"⚠️  文件不存在: {file_path}")
            continue

        content = full_path.read_text(encoding="utf-8")
        original_content = content

        # 处理单个模式或模式列表
        if isinstance(patterns, tuple):
            patterns = [patterns]

        changes = 0
        for pattern, template in patterns:
            # 使用模板中的版本占位符进行替换
            replacement = template.format(version=new_version)
            new_content, count = re.subn(pattern, replacement, content)
            if count > 0:
                content = new_content
                changes += count

        if changes > 0:
            if dry_run:
                print(f"🔍 [DRY RUN] {file_path}: {changes} 处修改")
            else:
                full_path.write_text(content, encoding="utf-8")
                print(f"✅ {file_path}: {changes} 处修改")
        else:
            print(f"⏭️  {file_path}: 无需修改")

    print("-" * 50)
    if not dry_run:
        print(f"✅ 版本号已更新到 {new_version}")
    return True


def main():
    parser = argparse.ArgumentParser(
        description="MediaFactory 版本号同步工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
    python scripts/utils/sync_version.py 0.2.1       # 更新所有文件版本号
    python scripts/utils/sync_version.py --check     # 检查版本号一致性
    python scripts/utils/sync_version.py --current   # 显示当前版本号
    python scripts/utils/sync_version.py 0.2.1 --dry-run  # 预览修改
        """,
    )

    parser.add_argument(
        "version",
        nargs="?",
        help="要设置的新版本号 (格式: X.Y.Z)",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="检查所有文件版本号是否一致",
    )
    parser.add_argument(
        "--current",
        action="store_true",
        help="显示当前版本号",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="预览修改而不实际写入文件",
    )

    args = parser.parse_args()

    # 显示当前版本
    if args.current:
        version = get_current_version()
        if version:
            print(f"当前版本: {version}")
            return 0
        else:
            print("❌ 无法获取当前版本号")
            return 1

    # 检查一致性
    if args.check:
        return 0 if check_consistency() else 1

    # 更新版本
    if args.version:
        success = update_version(args.version, dry_run=args.dry_run)
        return 0 if success else 1

    # 无参数时显示帮助
    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
