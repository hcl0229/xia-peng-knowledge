"""
夏鹏知识库 自动化影子测试 + 关键词缺口检测
=============================================
自主优化架构核心组件: 在后台持续运行回归测试套件,
当发现关键词缺口或路由退化时自动生成优化建议。

用法:
  python auto_test.py              # 运行完整测试套件
  python auto_test.py --watch      # 监控模式（定期运行）
  python auto_test.py --report     # 生成JSON报告
"""

import json
import os
import sys
import time
from datetime import datetime, timezone
from typing import Any

# 将 scripts 目录加入路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from router_v2 import match, SCENARIO_MAP, validate_routing_table


# =============================================================================
# 1. 测试套件
# =============================================================================

# 基础场景（预期命中）
BASELINE_TESTS = [
    ("我要写周报了",                "career", "upward-management"),
    ("老板给我派杂活怎么办",          "career", "upward-management"),
    ("想跳槽但不确定",               "career", "upward-management"),
    ("怎么跟领导提涨薪",             "career", "upward-management"),
    ("用夏鹏的方式写年终总结",        "career", "upward-management"),
    ("夏鹏关于AI怎么说的",           "knowledge", "shared"),
    ("最近情绪不好老内耗",            "growth", "growth-scenarios"),
    ("怎么拒绝同事的请求",            "career", "workplace-comm"),
    ("如何培养气场",                 "growth", "growth-scenarios"),
    ("刚当上管理者应该注意什么",      "career", "leadership"),
    ("团队执行力太差怎么办",          "career", "team-management"),
    ("想做个副业",                   "growth", "side-learning"),
    ("最近很焦虑怎么办",             "growth", "growth-scenarios"),
    ("怎么跟老板谈加薪",             "career", "upward-management"),
    ("年终述职PPT怎么做",            "career", "upward-management"),
]

# P0 修复验证（预期现在命中）
P0_REGRESSION_TESTS = [
    ("我领导不好相处",              "career", "upward-management"),  # "领导"  修复
    ("领导总让我加班",              "career", "upward-management"),  # "领导"  修复
    ("ChatGPT最新版本怎么样",       "knowledge", "shared"),          # "ChatGPT" 修复
    ("如何做复盘",                  "career", "upward-management"),  # "复盘"  修复
    ("工作中被针对了",              "career", "upward-management"),  # "被针对" 修复
    ("经常被PIP怎么办",             "career", "upward-management"),  # "PIP"   修复
]

# 边缘场景（压力测试）
EDGE_TESTS = [
    ("deepseek怎么用",             "knowledge", "shared"),
    ("跟老板提离职话术",            "career", "upward-management"),
    ("年终述职PPT模板",             "career", "upward-management"),
    ("如何拒绝领导的安排",           "career", "workplace-comm"),
    ("怎么跟领导说辞职",            "career", "upward-management"),
    ("被同事甩锅了怎么办",          "career", "upward-management"),
    ("遇到小人应该怎么应对",        "growth", "people-skills"),
    ("创业做什么方向好",            "growth", "side-learning"),
    ("如何有效向上管理",            "career", "upward-management"),
    ("最近心态崩了",                "growth", "growth-scenarios"),
]

ALL_TESTS = BASELINE_TESTS + P0_REGRESSION_TESTS + EDGE_TESTS


# =============================================================================
# 2. 测试执行引擎
# =============================================================================

def run_test_suite(tests: list) -> dict:
    """执行测试套件并返回详细结果。"""
    results = {"passed": 0, "failed": 0, "warned": 0, "details": [], "latency_ms": []}

    for query, expected_skill, expected_domain in tests:
        t0 = time.time()
        matched = match(query)
        latency = (time.time() - t0) * 1000
        results["latency_ms"].append(latency)

        top = matched[0]
        actual_skill, actual_domain, confidence = top

        passed = actual_skill == expected_skill and actual_domain == expected_domain
        warned = (
            not passed
            and confidence == 0
            and expected_skill != "knowledge"  # 未命中但预期也应未命中不算warn
        )

        status = "PASS" if passed else ("WARN" if warned else "FAIL")

        if passed:
            results["passed"] += 1
        elif warned:
            results["warned"] += 1
        else:
            results["failed"] += 1

        results["details"].append({
            "query": query,
            "status": status,
            "expected": f"{expected_skill}/{expected_domain}",
            "actual": f"{actual_skill}/{actual_domain}",
            "confidence": confidence,
            "latency_ms": round(latency, 2),
        })

    return results


def analyze_gaps() -> list[dict]:
    """分析关键词缺口：scenario-index.md 中有但 SCENARIO_MAP 中无的词。
    
    只提取纯关键词（短词，2-8字），过滤掉：
      - 表格分隔符（---）
      - 场景名/核心建议（完整句子）
      - BV号（视频ID）
      - 金句ID（Q001等）
    """
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    scenario_path = os.path.join(root, "references", "scenario-index.md")
    if not os.path.isfile(scenario_path):
        return []

    with open(scenario_path, "r", encoding="utf-8") as f:
        lines = f.readlines()

    gaps = []
    seen = set()

    for line in lines:
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue

        # 跳过分隔线、标题行
        if all(c in "|- " for c in stripped):
            continue
        if "BV号" in stripped or "场景" in stripped or "金句" in stripped:
            continue

        cols = [c.strip() for c in stripped.split("|")]
        if len(cols) < 3:
            continue

        # 关键列: cols[2] 是 "关键词" 列, cols[3] 可能是 "匹配关键词" 列（视表格而定）
        candidate_cols = []
        for idx in [2, 3]:
            if idx < len(cols) and cols[idx]:
                candidate_cols.append(cols[idx])

        for cell in candidate_cols:
            for kw in cell.split(","):
                kw = kw.strip()
                if not kw:
                    continue
                # 过滤：只保留 2-10 字的短关键词，排除句子、BV号、金句ID
                if len(kw) > 10 or len(kw) < 2:
                    continue
                if kw.startswith("BV") or kw.startswith("Q"):
                    continue
                # 排除完整句子（含中文空格或超过1个标点）
                if any(p in kw for p in "，。！？的"):
                    continue

                kw_key = kw.lower()
                if kw_key in seen:
                    continue
                seen.add(kw_key)

                map_lower = {k.lower() for k in SCENARIO_MAP}
                if kw not in SCENARIO_MAP and kw.lower() not in map_lower:
                    # 判断是否被更短关键词部分覆盖（如"工作周报" 被 "周报"覆盖）
                    partially_covered = any(
                        len(k) >= 2 and k.lower() in kw.lower()
                        for k in SCENARIO_MAP
                    )
                    gaps.append({
                        "keyword": kw,
                        "partially_covered": partially_covered,
                        "suggested_map": map_suggested_domain(kw),
                    })

    return gaps


def map_suggested_domain(kw: str) -> str:
    """根据关键词上下文推测其应归属的领域。"""
    kw_lower = kw.lower()
    career_words = {"工作", "汇报", "管理", "领导", "晋升", "团队", "面试", "跳槽", "加薪", "离职", "offer"}
    growth_words = {"学习", "自律", "习惯", "读书", "焦虑", "人脉", "副业", "创业", "心态", "思维"}
    ai_words = {"ai", "chatgpt", "人工智能", "模型", "提示词", "prompt"}

    if any(w in kw_lower for w in ai_words):
        return "knowledge/shared (AI相关)"
    if any(w in kw for w in career_words):
        return "career/upward-management 或 career/leadership"
    if any(w in kw for w in growth_words):
        return "growth/growth-scenarios 或 growth/side-learning"
    return "待人工判断"


# =============================================================================
# 3. 报告生成
# =============================================================================

def generate_report() -> dict:
    """生成完整优化报告。"""
    suite_result = run_test_suite(ALL_TESTS)
    gap_analysis = analyze_gaps()
    validation = validate_routing_table()

    total = suite_result["passed"] + suite_result["failed"] + suite_result["warned"]
    pass_rate = suite_result["passed"] / total * 100 if total else 0
    avg_latency = sum(suite_result["latency_ms"]) / len(suite_result["latency_ms"]) if suite_result["latency_ms"] else 0

    return {
        "report_generated": datetime.now(timezone.utc).isoformat(),
        "summary": {
            "total_tests": total,
            "passed": suite_result["passed"],
            "failed": suite_result["failed"],
            "warned": suite_result["warned"],
            "pass_rate": f"{pass_rate:.1f}%",
            "avg_latency_ms": round(avg_latency, 2),
            "verdict": "PASS" if pass_rate >= 90 else ("WARN" if pass_rate >= 75 else "FAIL"),
        },
        "failures": [d for d in suite_result["details"] if d["status"] in ("FAIL", "WARN")],
        "all_results": suite_result["details"],
        "keyword_gaps": {
            "count": len(gap_analysis),
            "gaps": gap_analysis,
            "recommendation": (
                "无缺口，SCENARIO_MAP 已覆盖所有场景关键词"
                if not gap_analysis
                else f"发现 {len(gap_analysis)} 个待补充关键词，建议按需添加到 SCENARIO_MAP"
            ),
        },
        "routing_validation": validation,
    }


# =============================================================================
# 4. 监控模式
# =============================================================================

def watch_mode(interval_seconds: int = 3600):
    """持续监控模式：每小时运行一次回归测试，检测路由退化。"""
    print(f"[{datetime.now():%Y-%m-%d %H:%M:%S}] 监控启动，检测间隔: {interval_seconds}s")
    report_dir = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "telemetry"
    )
    os.makedirs(report_dir, exist_ok=True)

    while True:
        report = generate_report()
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_path = os.path.join(report_dir, f"auto_test_{timestamp}.json")

        with open(report_path, "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2)

        verdict = report["summary"]["verdict"]
        print(
            f"[{datetime.now():%Y-%m-%d %H:%M:%S}] "
            f"Pass Rate: {report['summary']['pass_rate']}, "
            f"Verdict: {verdict}, "
            f"Gaps: {report['keyword_gaps']['count']}, "
            f"Report: {report_path}"
        )

        if verdict == "FAIL":
            print(f"  ⚠️ 检测到路由退化！{report['summary']['failed']} 项测试失败")

        time.sleep(interval_seconds)


# =============================================================================
# 5. CLI
# =============================================================================

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="夏鹏知识库自动测试")
    parser.add_argument("--report", action="store_true", help="生成 JSON 报告")
    parser.add_argument("--watch", action="store_true", help="监控模式")
    parser.add_argument("--interval", type=int, default=3600, help="监控间隔（秒）")
    parser.add_argument("--gaps", action="store_true", help="仅输出关键词缺口")
    parser.add_argument("--p0-only", action="store_true", help="仅运行 P0 回归测试")

    args = parser.parse_args()

    if args.watch:
        watch_mode(args.interval)

    elif args.gaps:
        gaps = analyze_gaps()
        if not gaps:
            print("✅ 无关键词缺口")
        else:
            print(f"🔍 发现 {len(gaps)} 个关键词缺口:\n")
            for g in gaps:
                coverage = "部分覆盖" if g["partially_covered"] else "完全缺失"
                print(f"  [{coverage}] {g['keyword']}")
                print(f"    来源: {g['line']}\n")

    elif args.p0_only:
        result = run_test_suite(P0_REGRESSION_TESTS)
        print(f"P0 回归: {result['passed']}/{result['passed'] + result['failed'] + result['warned']} 通过")
        for d in result["details"]:
            icon = "✅" if d["status"] == "PASS" else "❌"
            print(f"  {icon} {d['query'][:30]:30s} → {d['actual']} (期望: {d['expected']})")

    elif args.report:
        report = generate_report()
        print(json.dumps(report, ensure_ascii=False, indent=2))

    else:
        # 默认：完整测试套件
        report = generate_report()
        s = report["summary"]
        print(f"\n{'='*60}")
        print(f"  夏鹏知识库 v2 自动化测试报告")
        print(f"{'='*60}")
        print(f"  生成时间: {report['report_generated']}")
        print(f"  总用例:   {s['total_tests']}")
        print(f"  通过:     {s['passed']} ✅")
        print(f"  失败:     {s['failed']} ❌")
        print(f"  警告:     {s['warned']} ⚠️")
        print(f"  通过率:   {s['pass_rate']}")
        print(f"  平均延迟: {s['avg_latency_ms']}ms")
        print(f"  判定:     {s['verdict']}")
        print(f"  缺口:     {report['keyword_gaps']['count']} 个")
        print(f"{'='*60}\n")

        if report["failures"]:
            print("失败详情:")
            for f in report["failures"]:
                print(f"  [{f['status']}] {f['query']}")
                print(f"    期望: {f['expected']} | 实际: {f['actual']} (置信度: {f['confidence']}%)\n")

        if report["keyword_gaps"]["gaps"]:
            print("关键词缺口:")
            for g in report["keyword_gaps"]["gaps"]:
                coverage = "部分覆盖" if g["partially_covered"] else "完全缺失"
                print(f"  [{coverage}] {g['keyword']}")
            print()
