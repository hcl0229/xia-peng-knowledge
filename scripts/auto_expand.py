"""
夏鹏知识库 关键词自动扩展引擎 (Phase 3)
========================================
分析 scenario-index.md 中的缺口关键词，按置信度自动归类，
生成可直接合并到 SCENARIO_MAP 的补丁代码。

用法:
  python auto_expand.py              # 分析并生成补丁
  python auto_expand.py --apply      # 分析并自动应用到 router_v2.py
  python auto_expand.py --dry-run    # 仅预览，不修改文件
  python auto_expand.py --safe-only  # 仅生成高置信度补丁
"""

import os
import re
import sys
import json
from collections import defaultdict
from typing import Any

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# ── 从 scenario-index.md 提取的缺口关键词 (与 validate 输出一致) ──
# 来源: router_v2.py validate_routing_table() 的精确解析结果

SKILL_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ROUTER_PATH = os.path.join(SKILL_ROOT, "scripts", "router_v2.py")
SCENARIO_PATH = os.path.join(SKILL_ROOT, "references", "scenario-index.md")

# ── 领域映射规则 (用于推断缺口关键词的目标领域) ──

DOMAIN_PATTERNS = {
    # pattern -> (skill, domain)
    # 向上汇报
    "周报": ("career", "upward-management"),
    "总结": ("career", "upward-management"),
    "年终": ("career", "upward-management"),
    "述职": ("career", "upward-management"),
    "汇报": ("career", "upward-management"),
    "报告": ("career", "upward-management"),
    "同步": ("career", "upward-management"),
    "进展": ("career", "upward-management"),
    "反馈": ("career", "upward-management"),
    "曝光": ("career", "upward-management"),
    "存在感": ("career", "upward-management"),
    "露脸": ("career", "upward-management"),
    "年度": ("career", "upward-management"),
    # 向上管理
    "选老板": ("career", "upward-management"),
    "相处": ("career", "upward-management"),
    "威信": ("career", "upward-management"),
    "信任": ("career", "upward-management"),
    "靠谱": ("career", "upward-management"),
    "可靠": ("career", "upward-management"),
    "送礼": ("career", "upward-management"),
    "礼物": ("career", "upward-management"),
    "感恩": ("career", "upward-management"),
    "人情": ("career", "upward-management"),
    "节日": ("career", "upward-management"),
    "择主": ("career", "upward-management"),
    "关系": ("career", "upward-management"),
    # 跳槽面试
    "换工作": ("career", "upward-management"),
    "裸辞": ("career", "upward-management"),
    "offer": ("career", "upward-management"),
    "转行": ("career", "upward-management"),
    # 领导力
    "评估": ("career", "leadership"),
    "威严": ("career", "leadership"),
    "权威": ("career", "leadership"),
    "标准": ("career", "leadership"),
    "升职": ("career", "leadership"),
    "升职条件": ("career", "leadership"),
    # 团队管理
    "会议": ("career", "team-management"),
    "目标": ("career", "team-management"),
    "OKR": ("career", "team-management"),
    "KPI": ("career", "team-management"),
    "方向": ("career", "team-management"),
    "士气": ("career", "team-management"),
    "干劲": ("career", "team-management"),
    "驱动": ("career", "team-management"),
    "高效": ("career", "team-management"),
    "效率": ("career", "team-management"),
    "凝聚力": ("career", "team-management"),
    "团结": ("career", "team-management"),
    "归属感": ("career", "team-management"),
    "开人": ("career", "team-management"),
    "辞退": ("career", "team-management"),
    "淘汰": ("career", "team-management"),
    "优化": ("career", "team-management"),
    "炒人": ("career", "team-management"),
    "考核": ("career", "team-management"),
    "绩效": ("career", "team-management"),
    "打分": ("career", "team-management"),
    # 职场沟通
    "说不": ("career", "workplace-comm"),
    "推掉": ("career", "workplace-comm"),
    "口才": ("career", "workplace-comm"),
    "演讲": ("career", "workplace-comm"),
    "说话": ("career", "workplace-comm"),
    "谈判": ("career", "workplace-comm"),
    "争取": ("career", "workplace-comm"),
    "推销": ("career", "workplace-comm"),
    "提案": ("career", "workplace-comm"),
    "冷场": ("career", "workplace-comm"),
    "说话艺术": ("career", "workplace-comm"),
    "人际关系": ("career", "workplace-comm"),
    # 个人成长
    "行动力": ("growth", "growth-scenarios"),
    "拖延": ("growth", "growth-scenarios"),
    "懒惰": ("growth", "growth-scenarios"),
    "自控": ("growth", "growth-scenarios"),
    "坚持": ("growth", "growth-scenarios"),
    "自我管理": ("growth", "growth-scenarios"),
    "气质": ("growth", "growth-scenarios"),
    "魅力": ("growth", "growth-scenarios"),
    "思考": ("growth", "growth-scenarios"),
    "分析": ("growth", "growth-scenarios"),
    "理性": ("growth", "growth-scenarios"),
    "深度思考": ("growth", "growth-scenarios"),
    "认知": ("growth", "growth-scenarios"),
    "视野": ("growth", "growth-scenarios"),
    "大局观": ("growth", "growth-scenarios"),
    "眼界": ("growth", "growth-scenarios"),
    "洞见": ("growth", "growth-scenarios"),
    "认知升级": ("growth", "growth-scenarios"),
    # 情绪管理
    "稳定": ("growth", "growth-scenarios"),
    "冷静": ("growth", "growth-scenarios"),
    "发脾气": ("growth", "growth-scenarios"),
    "纠结": ("growth", "growth-scenarios"),
    "想太多": ("growth", "growth-scenarios"),
    "消耗": ("growth", "growth-scenarios"),
    "自卑": ("growth", "growth-scenarios"),
    "信心": ("growth", "growth-scenarios"),
    "自我怀疑": ("growth", "growth-scenarios"),
    "压力": ("growth", "growth-scenarios"),
    "不安": ("growth", "growth-scenarios"),
    "恐慌": ("growth", "growth-scenarios"),
    "担心": ("growth", "growth-scenarios"),
    # 人际关系
    "圈子": ("growth", "people-skills"),
    "搭讪": ("growth", "people-skills"),
    "接话": ("growth", "people-skills"),
    "对话": ("growth", "people-skills"),
    "聊天技巧": ("growth", "people-skills"),
    "回应": ("growth", "people-skills"),
    "识人": ("growth", "people-skills"),
    "看人": ("growth", "people-skills"),
    "分辨": ("growth", "people-skills"),
    "人品": ("growth", "people-skills"),
    "判断人": ("growth", "people-skills"),
    # 副业学习
    "数字游民": ("growth", "side-learning"),
    "变现": ("growth", "side-learning"),
    "兼职": ("growth", "side-learning"),
    # AI
    "大模型": ("knowledge", "shared"),
    "数字化": ("knowledge", "shared"),
    "自动化": ("knowledge", "shared"),
    "智能管理": ("knowledge", "shared"),
}


def extract_gap_keywords() -> list[dict]:
    """从 scenario-index.md 提取缺口关键词（复用精确解析器）。"""
    from router_v2 import validate_routing_table

    result = validate_routing_table()
    if result[0]["severity"] == "ok":
        return []
    return result[0].get("missing_keywords", [])


def classify_and_rank(gaps: list[dict]) -> dict:
    """按置信度分级 + 按场景分组。"""
    high_conf = []    # 可直接合并
    medium_conf = []  # 需人工确认
    low_conf = []     # 建议保留在 scenario-index 即可

    for gap in gaps:
        kw = gap["keyword"]
        partially = gap.get("partially_covered", False)
        scenario = gap.get("scenario", "未知")

        # 查找领域映射
        mapped = None
        for pattern, target in DOMAIN_PATTERNS.items():
            if pattern in kw or kw in pattern:
                mapped = target
                break

        entry = {"keyword": kw, "scenario": scenario, "target": mapped, "partially_covered": partially}

        if partially:
            low_conf.append(entry)      # 已被现有关键词部分覆盖
        elif mapped is not None:
            high_conf.append(entry)     # 有明确领域映射
        else:
            medium_conf.append(entry)   # 关键词短且无明确映射

    return {
        "high": high_conf,
        "medium": medium_conf,
        "low": low_conf,
        "summary": {
            "total_gaps": len(gaps),
            "auto_mergeable": len(high_conf),
            "needs_review": len(medium_conf),
            "already_covered": len(low_conf),
        },
    }


def generate_map_patch(entries: list[dict], prefix_comment: str = "") -> str:
    """生成可直接插入到 SCENARIO_MAP 的关键词条目。"""
    lines = []
    if prefix_comment:
        lines.append(f"    # ── {prefix_comment} ──")
    for e in entries:
        skill, domain = e["target"]
        kw = e["keyword"]
        lines.append(f'    "{kw}":       ("{skill}", "{domain}"),')
    return "\n".join(lines)


def preview_expansion(classified: dict):
    """预览扩展效果：模拟合并后对比命中率。"""
    print(f"\n{'='*60}")
    print(f"  关键词自动扩展分析")
    print(f"{'='*60}")
    s = classified["summary"]
    print(f"  总缺口:     {s['total_gaps']}")
    print(f"  可自动合并: {s['auto_mergeable']}  ✅")
    print(f"  需人工确认: {s['needs_review']}  ⚠️")
    print(f"  已被覆盖:   {s['already_covered']}  ℹ️")
    print(f"  合并后剩余: {s['needs_review']}")
    print(f"{'='*60}\n")

    # 按领域分组展示可自动合并的关键词
    if classified["high"]:
        print("📦 可自动合并关键词（高置信度）:\n")
        by_domain = defaultdict(list)
        for e in classified["high"]:
            key = f"{e['target'][0]}/{e['target'][1]}"
            by_domain[key].append(e["keyword"])

        for domain, keywords in sorted(by_domain.items()):
            print(f"  [{domain}]: {', '.join(keywords)}")
        print()

    if classified["medium"]:
        print("⚠️  需人工确认（无明确领域映射）:\n")
        for e in classified["medium"]:
            print(f"  · {e['keyword']} (场景: {e['scenario']})")
        print()

    # 生成代码补丁预览
    print("\n--- 生成的 SCENARIO_MAP 补丁代码 ---\n")
    print("# 复制以下代码添加到 router_v2.py 的 SCENARIO_MAP 中\n")
    patch = generate_map_patch(classified["high"], "Phase 3 自动扩展 — 高置信度")
    print(patch)
    print()


def apply_to_router(classified: dict) -> bool:
    """将高置信度关键词自动合并到 router_v2.py 的 SCENARIO_MAP。"""
    high = classified["high"]
    if not high:
        print("无可自动合并的关键词。")
        return False

    from router_v2 import SCENARIO_MAP

    new_count = 0
    for e in high:
        kw = e["keyword"]
        if kw not in SCENARIO_MAP:
            SCENARIO_MAP[kw] = e["target"]
            new_count += 1

    # 写回文件 — 重新生成 SCENARIO_MAP 区域
    with open(ROUTER_PATH, "r", encoding="utf-8") as f:
        content = f.read()

    # 找到 SCENARIO_MAP 定义位置并插入新条目
    # 在现有的 AI 分类后追加
    marker = '    "工具":       ("knowledge", "shared"),'
    lines_to_insert = []
    # 按领域分组
    by_domain = defaultdict(list)
    for e in high:
        by_domain[e["target"]].append(e["keyword"])

    domain_names = {
        ("career", "upward-management"): "向上管理/汇报 (Phase 3 扩展)",
        ("career", "leadership"): "领导力 (Phase 3 扩展)",
        ("career", "team-management"): "团队管理 (Phase 3 扩展)",
        ("career", "workplace-comm"): "职场沟通 (Phase 3 扩展)",
        ("growth", "growth-scenarios"): "个人成长/情绪 (Phase 3 扩展)",
        ("growth", "people-skills"): "人际关系 (Phase 3 扩展)",
        ("growth", "side-learning"): "副业学习 (Phase 3 扩展)",
        ("knowledge", "shared"): "AI/知识 (Phase 3 扩展)",
    }

    for target, keywords in sorted(by_domain.items()):
        domain_name = domain_names.get(target, str(target))
        lines_to_insert.append(f"\n    # ── {domain_name} ──")
        for kw in sorted(keywords):
            lines_to_insert.append(f'    "{kw}":       {target},')

    insert_block = "\n".join(lines_to_insert) + "\n"

    if marker in content:
        content = content.replace(marker, marker + "\n" + insert_block)
    else:
        print("⚠️  未找到 SCENARIO_MAP 插入位置，无法自动合并。")
        return False

    with open(ROUTER_PATH, "w", encoding="utf-8") as f:
        f.write(content)

    print(f"✅ 已将 {new_count} 个关键词自动合并到 {ROUTER_PATH}")
    return True


# =============================================================================
# CLI
# =============================================================================

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="关键词自动扩展引擎")
    parser.add_argument("--apply", action="store_true", help="自动应用到 router_v2.py")
    parser.add_argument("--safe-only", action="store_true", help="仅合并高置信度关键词")
    parser.add_argument("--dry-run", action="store_true", help="仅预览不修改文件")
    parser.add_argument("--json", action="store_true", help="JSON格式输出")

    args = parser.parse_args()

    gaps = extract_gap_keywords()
    if not gaps:
        print("✅ 无缺口关键词，SCENARIO_MAP 已完整覆盖！")
        sys.exit(0)

    classified = classify_and_rank(gaps)

    if args.json:
        print(json.dumps({
            "summary": classified["summary"],
            "auto_merge": [e["keyword"] for e in classified["high"]],
            "needs_review": [e["keyword"] for e in classified["medium"]],
            "already_covered": [e["keyword"] for e in classified["low"]],
        }, ensure_ascii=False, indent=2))
        sys.exit(0)

    preview_expansion(classified)

    if args.apply:
        apply_to_router(classified)
        print("\n📊 建议运行 auto_test.py 验证合并后的路由准确性。")
