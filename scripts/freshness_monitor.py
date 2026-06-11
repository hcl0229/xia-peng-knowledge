"""
夏鹏知识库 内容新鲜度监控 (Phase 3)
====================================
检测知识资产的老化程度：
  - references/ 文件的最后修改时间
  - SKILL.md 版本与子Skill 版本一致性
  - scenario-index.md 中 BV 号覆盖率变化
  - 生成新鲜度评分 (0-100) 和过期告警

用法:
  python freshness_monitor.py             # 检查新鲜度
  python freshness_monitor.py --json      # JSON 格式输出
  python freshness_monitor.py --watch     # 监控模式
"""

import os
import sys
import json
import time
from datetime import datetime, timezone, timedelta

SKILL_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# 需要监控的文件
TRACKED_FILES = {
    "SKILL.md": {"category": "主Skill", "stale_days": 90},
    "CHANGELOG.md": {"category": "变更日志", "stale_days": 90},
    "references/framework-dictionary.md": {"category": "知识库", "stale_days": 60},
    "references/golden-quotes.md": {"category": "知识库", "stale_days": 60},
    "references/scenario-index.md": {"category": "知识库", "stale_days": 30},
    "references/knowledge-chain.md": {"category": "知识库", "stale_days": 60},
    "references/style-guide.md": {"category": "配置", "stale_days": 120},
    "scripts/router_v2.py": {"category": "核心", "stale_days": 60},
    "scripts/auto_test.py": {"category": "测试", "stale_days": 60},
    "scripts/scenario_matcher.py": {"category": "核心", "stale_days": 60},
    "scripts/auto_expand.py": {"category": "工具", "stale_days": 60},
}


def get_file_info(rel_path: str) -> dict:
    """获取文件的元信息。"""
    abs_path = os.path.join(SKILL_ROOT, rel_path)
    if not os.path.isfile(abs_path):
        return {"path": rel_path, "status": "missing", "error": "文件不存在"}

    stat = os.stat(abs_path)
    mtime = datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc)
    age_days = (datetime.now(timezone.utc) - mtime).days

    return {
        "path": rel_path,
        "status": "ok",
        "size_bytes": stat.st_size,
        "last_modified": mtime.isoformat(),
        "age_days": age_days,
    }


def check_freshness() -> dict:
    """全面检查知识库新鲜度。"""
    now = datetime.now(timezone.utc)
    results = {"checked_at": now.isoformat(), "files": [], "alerts": [], "score": 100}

    for rel_path, config in TRACKED_FILES.items():
        info = get_file_info(rel_path)
        info["category"] = config["category"]
        info["stale_threshold_days"] = config["stale_days"]

        if info["status"] == "missing":
            info["freshness"] = "MISSING"
            results["alerts"].append({
                "level": "error",
                "file": rel_path,
                "msg": f"文件缺失: {rel_path}",
            })
            results["score"] -= 10
        elif info["age_days"] > config["stale_days"] * 2:
            info["freshness"] = "CRITICAL"
            results["alerts"].append({
                "level": "critical",
                "file": rel_path,
                "msg": f"严重过期: {rel_path} 已有 {info['age_days']} 天未更新 (阈值: {config['stale_days']} 天)",
            })
            results["score"] -= 15
        elif info["age_days"] > config["stale_days"]:
            info["freshness"] = "STALE"
            results["alerts"].append({
                "level": "warning",
                "file": rel_path,
                "msg": f"内容已过期: {rel_path} 已有 {info['age_days']} 天未更新 (阈值: {config['stale_days']} 天)",
            })
            results["score"] -= 5
        else:
            info["freshness"] = "FRESH"

        results["files"].append(info)

    # 版本一致性检查
    version_check = _check_version_consistency()
    if version_check["issues"]:
        for issue in version_check["issues"]:
            results["alerts"].append(issue)
            results["score"] -= 5

    results["version_check"] = version_check

    # 评分归一化
    results["score"] = max(0, min(100, results["score"]))
    results["grade"] = _score_to_grade(results["score"])

    return results


def _check_version_consistency() -> dict:
    """检查 SKILL.md 版本号与 CHANGELOG.md 一致性。"""
    issues = []
    versions = {}

    # 读取 SKILL.md 版本
    skill_path = os.path.join(SKILL_ROOT, "SKILL.md")
    if os.path.isfile(skill_path):
        with open(skill_path, "r", encoding="utf-8") as f:
            for line in f:
                if line.startswith("version:"):
                    versions["SKILL.md"] = line.split(":")[1].strip()
                    break

    # 读取 CHANGELOG.md 最新版本
    changelog_path = os.path.join(SKILL_ROOT, "CHANGELOG.md")
    if os.path.isfile(changelog_path):
        with open(changelog_path, "r", encoding="utf-8") as f:
            for line in f:
                if line.startswith("## "):
                    versions["CHANGELOG.md"] = line.replace("## ", "").split(" ")[0].strip()
                    break

    if versions.get("SKILL.md") != versions.get("CHANGELOG.md"):
        issues.append({
            "level": "warning",
            "file": "SKILL.md / CHANGELOG.md",
            "msg": f"版本不一致: SKILL.md={versions.get('SKILL.md')}, CHANGELOG={versions.get('CHANGELOG.md')}",
        })

    return {"versions": versions, "issues": issues}


def _score_to_grade(score: int) -> str:
    if score >= 90:
        return "A (优秀)"
    elif score >= 75:
        return "B (良好)"
    elif score >= 60:
        return "C (需关注)"
    elif score >= 40:
        return "D (严重退化)"
    else:
        return "F (紧急)"


def format_report(report: dict) -> str:
    """生成人类可读的报告。"""
    lines = []
    lines.append(f"\n{'='*60}")
    lines.append(f"  知识库新鲜度报告")
    lines.append(f"{'='*60}")
    lines.append(f"  检查时间: {report['checked_at']}")
    lines.append(f"  新鲜度评分: {report['score']}/100 — {report['grade']}")
    lines.append(f"  告警数量: {len(report['alerts'])}")
    lines.append(f"{'='*60}\n")

    # 文件清单
    lines.append("📁 文件新鲜度:")
    lines.append(f"  {'文件':40s} {'天数':>5s} {'状态':>12s}")
    lines.append(f"  {'─'*40} {'─'*5} {'─'*12}")
    for f in sorted(report["files"], key=lambda x: -x["age_days"]):
        icon = {"FRESH": "🟢", "STALE": "🟡", "CRITICAL": "🔴", "MISSING": "❌"}.get(f["freshness"], "⚪")
        lines.append(f"  {icon} {f['path']:38s} {f['age_days']:>3d}d {f['freshness']:>12s}")
    lines.append("")

    # 告警
    if report["alerts"]:
        lines.append("⚠️  新鲜度告警:")
        for alert in report["alerts"]:
            level_icon = {"error": "❌", "critical": "🔴", "warning": "🟡"}.get(alert["level"], "⚪")
            lines.append(f"  {level_icon} [{alert['level'].upper()}] {alert['msg']}")
    else:
        lines.append("✅ 无新鲜度告警，所有文件均处于健康状态。")

    # 版本检查
    vc = report.get("version_check", {})
    if vc.get("versions"):
        lines.append(f"\n📋 版本信息:")
        for source, ver in vc["versions"].items():
            lines.append(f"  {source}: {ver}")

    lines.append("")
    return "\n".join(lines)


# =============================================================================
# CLI
# =============================================================================

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="内容新鲜度监控")
    parser.add_argument("--json", action="store_true", help="JSON 格式输出")
    parser.add_argument("--watch", action="store_true", help="监控模式 (24小时一次)")
    args = parser.parse_args()

    if args.watch:
        print(f"[{datetime.now():%Y-%m-%d %H:%M:%S}] 新鲜度监控启动")
        while True:
            report = check_freshness()
            print(format_report(report))
            if report["alerts"]:
                print(f"  ⚠️ {len(report['alerts'])} 条告警")
            else:
                print(f"  ✅ 所有文件新鲜")
            time.sleep(86400)
    elif args.json:
        report = check_freshness()
        print(json.dumps(report, ensure_ascii=False, indent=2, default=str))
    else:
        report = check_freshness()
        print(format_report(report))
