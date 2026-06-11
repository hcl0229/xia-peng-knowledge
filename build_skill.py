"""
xia-peng-knowledge 构建脚本
============================
用法:
  python build_skill.py              # 构建 .skill 包
  python build_skill.py --clean      # 清理 + 重建
  python build_skill.py --verify     # 验证 .skill 包内容
"""

import os
import sys
import zipfile
import shutil
from datetime import datetime


SKILL_DIR = os.path.dirname(os.path.abspath(__file__))
SKILL_NAME = "xia-peng-knowledge"
OUTPUT_FILE = os.path.join(SKILL_DIR, f"{SKILL_NAME}.skill")

# 纳入分发的文件/目录清单
INCLUDE_LIST = [
    "SKILL.md",
    "CHANGELOG.md",
    "references/",        # 全部 references
    "scripts/",           # ← Phase 2: 纳入 scripts/
    "assets/",            # ← Phase 2: 纳入 assets/
]

# 排除的文件模式
EXCLUDE_PATTERNS = [
    "__pycache__",
    "*.pyc",
    "*.pyo",
    ".DS_Store",
    "Thumbs.db",
    "*.skill",            # 不要把自己打包进去
    "build_skill.py",     # 构建脚本本身不打包
    "telemetry/",         # 遥测数据不打包
]


def should_include(filepath: str, skill_prefix: str) -> bool:
    """判断文件是否应纳入分发包。"""
    relative = filepath.replace(skill_prefix + "/", "", 1) if filepath.startswith(skill_prefix + "/") else filepath

    for pattern in EXCLUDE_PATTERNS:
        if pattern.startswith("*"):
            if filepath.endswith(pattern[1:]):
                return False
        elif pattern.endswith("/"):
            if relative.startswith(pattern) or filepath.startswith(pattern):
                return False
        elif pattern in filepath or pattern in relative:
            return False
    return True


def build_skill():
    """构建 .skill ZIP 包。"""
    print(f"[{datetime.now():%H:%M:%S}] 开始构建 {SKILL_NAME}.skill ...")

    # 收集所有文件
    entries = []
    for item in INCLUDE_LIST:
        full_path = os.path.join(SKILL_DIR, item)
        if not os.path.exists(full_path):
            print(f"  ⚠️  跳过不存在: {item}")
            continue

        if os.path.isfile(full_path):
            entries.append(full_path)
        elif os.path.isdir(full_path):
            for root, dirs, files in os.walk(full_path):
                for fname in files:
                    entries.append(os.path.join(root, fname))

    # 构建 ZIP
    if os.path.exists(OUTPUT_FILE):
        os.remove(OUTPUT_FILE)
        print("  🗑️  已清理旧包")

    count = 0
    with zipfile.ZipFile(OUTPUT_FILE, "w", zipfile.ZIP_DEFLATED) as zf:
        for entry in sorted(entries):
            arcname = os.path.relpath(entry, SKILL_DIR).replace("\\", "/")
            if not should_include(arcname, SKILL_NAME):
                continue
            zf.write(entry, arcname)
            count += 1

    size_kb = os.path.getsize(OUTPUT_FILE) / 1024
    print(f"  ✅ 打包完成: {count} 个文件, {size_kb:.1f} KB")
    print(f"    输出: {OUTPUT_FILE}")


def verify_skill():
    """验证 .skill 包内容。"""
    if not os.path.exists(OUTPUT_FILE):
        print("  ❌ .skill 包不存在，请先执行 build")
        return

    print(f"\n--- {SKILL_NAME}.skill 内容验证 ---")
    total_size = 0
    with zipfile.ZipFile(OUTPUT_FILE, "r") as zf:
        for info in zf.infolist():
            total_size += info.file_size
            print(f"  {info.filename:55s} {info.file_size:>8,} bytes")
        file_count = len(zf.infolist())

    print(f"\n  总计: {file_count} 个文件, {total_size:,} bytes ({total_size/1024:.1f} KB)")

    # 检查必须文件
    with zipfile.ZipFile(OUTPUT_FILE, "r") as zf:
        names = zf.namelist()

    checks = {
        "SKILL.md": any("SKILL.md" in n for n in names),
        "references/": any("references/" in n for n in names),
        "scripts/": any("scripts/" in n for n in names),
        "scenario_matcher.py": any("scenario_matcher.py" in n for n in names),
        "router_v2.py": any("router_v2.py" in n for n in names),
        "auto_test.py": any("auto_test.py" in n for n in names),
    }

    print("\n  完整性检查:")
    all_ok = True
    for check, passed in checks.items():
        icon = "✅" if passed else "❌"
        if not passed:
            all_ok = False
        print(f"    {icon} {check}")

    if all_ok:
        print("\n  🎉 所有检查通过，可分发给生产环境！")
    else:
        print("\n  ⚠️  存在缺失项，请检查 build_skill.py 中的 INCLUDE_LIST")
        sys.exit(1)


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description=f"构建 {SKILL_NAME}.skill")
    parser.add_argument("--verify", action="store_true", help="仅验证不构建")
    parser.add_argument("--clean", action="store_true", help="清理旧包后重建")
    args = parser.parse_args()

    if args.verify:
        verify_skill()
    else:
        if args.clean and os.path.exists(OUTPUT_FILE):
            os.remove(OUTPUT_FILE)
            print("🗑️  已清理旧包")
        build_skill()
        verify_skill()
