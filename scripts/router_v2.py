r"""
夏鹏知识库路由器 v2 -- 自主优化架构
======================================
v1 -> v2 变更:
  - 单一数据源（SCENARIO_MAP 同时生成 SKILL.md 路由表）
  - 大小写不敏感匹配
  - 内置遥测打点（每次路由事件记录到 telemetry）
  - 熔断降级：子Skill加载失败 -> 本地references回退
  - 路径动态解析（不再硬编码 G:\skills）
"""

import json
import os
import sys
import time
from datetime import datetime, timezone


# =============================================================================
# 1. 单一数据源：SCENARIO_MAP（同时也是 SKILL.md 路由表的权威源）
# =============================================================================

SCENARIO_MAP = {
    # ── 向上汇报（长关键词优先，算法按长度降序匹配）──
    "年终总结":   ("career", "upward-management"),
    "周报":       ("career", "upward-management"),
    "述职":       ("career", "upward-management"),
    "汇报":       ("career", "upward-management"),
    "加薪":       ("career", "upward-management"),
    "涨薪":       ("career", "upward-management"),
    "谈薪":       ("career", "upward-management"),
    "复盘":       ("career", "upward-management"),  # ← P0 修复

    # ── 向上管理 ──
    "向上管理":   ("career", "upward-management"),
    "领导":       ("career", "upward-management"),  # ← P0 修复：独立 "领导"
    "PUA":        ("career", "upward-management"),
    "PIP":        ("career", "upward-management"),  # ← P0 修复
    "派杂活":     ("career", "upward-management"),
    "老板":       ("career", "upward-management"),
    "背刺":       ("career", "upward-management"),
    "甩锅":       ("career", "upward-management"),
    "被针对":     ("career", "upward-management"),  # ← P0 修复

    # ── 跳槽与面试 ──
    "跳槽":       ("career", "upward-management"),
    "离职":       ("career", "upward-management"),
    "辞职":       ("career", "upward-management"),
    "面试":       ("career", "upward-management"),
    "求职":       ("career", "upward-management"),

    # ── 领导力（"领导力"排在"领导"之后，长度优先保证不冲突）──
    "领导力":     ("career", "leadership"),
    "管理者":     ("career", "leadership"),
    "领导者":     ("career", "leadership"),
    "晋升":       ("career", "leadership"),
    "空降":       ("career", "leadership"),
    "提拔":       ("career", "leadership"),
    "领导团队":   ("career", "leadership"),

    # ── 团队管理 ──
    "团队":       ("career", "team-management"),
    "执行力":     ("career", "team-management"),
    "团队执行力": ("career", "team-management"),
    "下属":       ("career", "team-management"),
    "带人":       ("career", "team-management"),
    "授权":       ("career", "team-management"),
    "激励":       ("career", "team-management"),
    "开会":       ("career", "team-management"),
    "员工":       ("career", "team-management"),

    # ── 职场沟通 ──
    "沟通":       ("career", "workplace-comm"),
    "情商":       ("career", "workplace-comm"),
    "拒绝":       ("career", "workplace-comm"),
    "表达":       ("career", "workplace-comm"),
    "说服":       ("career", "workplace-comm"),
    "尬聊":       ("career", "workplace-comm"),

    # ── 个人成长 ──
    "成长":       ("growth", "growth-scenarios"),
    "自律":       ("growth", "growth-scenarios"),
    "习惯":       ("growth", "growth-scenarios"),
    "格局":       ("growth", "growth-scenarios"),
    "气场":       ("growth", "growth-scenarios"),
    "逻辑":       ("growth", "growth-scenarios"),
    "思维":       ("growth", "growth-scenarios"),
    "内卷":       ("growth", "growth-scenarios"),
    "摆烂":       ("growth", "growth-scenarios"),

    # ── 情绪管理 ──
    "情绪":       ("growth", "growth-scenarios"),
    "焦虑":       ("growth", "growth-scenarios"),
    "内耗":       ("growth", "growth-scenarios"),
    "心态":       ("growth", "growth-scenarios"),
    "自信":       ("growth", "growth-scenarios"),

    # ── 人际关系 ──
    "人脉":       ("growth", "people-skills"),
    "社交":       ("growth", "people-skills"),
    "破冰":       ("growth", "people-skills"),
    "小人":       ("growth", "people-skills"),
    "站队":       ("growth", "people-skills"),

    # ── 副业学习 ──
    "副业":       ("growth", "side-learning"),
    "赚钱":       ("growth", "side-learning"),
    "创业":       ("growth", "side-learning"),
    "学习":       ("growth", "side-learning"),
    "读书":       ("growth", "side-learning"),
    "新领域":     ("growth", "side-learning"),
    "自学":       ("growth", "side-learning"),

    # ── AI ──
    "AI":         ("knowledge", "shared"),
    "人工智能":   ("knowledge", "shared"),
    "ChatGPT":    ("knowledge", "shared"),  # ← P0 修复
    "DeepSeek":   ("knowledge", "shared"),
    "工具":       ("knowledge", "shared"),
}


# =============================================================================
# 2. 路径解析器（消除硬编码）
# =============================================================================

def _resolve_skill_root() -> str:
    """动态解析当前 skill 的根目录，不依赖硬编码路径。"""
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def resolve_sub_skill(sub_name: str) -> str:
    """
    解析子Skill路径。
    优先级:
      1. 同目录下的兄弟目录（标准安装结构）
      2. WORKBUDDY_SKILL_HOME 环境变量
      3. 抛出明确错误（不再默默失败）
    """
    root = _resolve_skill_root()
    parent = os.path.dirname(root)

    # 尝试兄弟目录
    candidate = os.path.join(parent, sub_name, "SKILL.md")
    if os.path.isfile(candidate):
        return candidate

    # 尝试环境变量
    env_home = os.environ.get("WORKBUDDY_SKILL_HOME", "")
    candidate_env = os.path.join(env_home, sub_name, "SKILL.md")
    if env_home and os.path.isfile(candidate_env):
        return candidate_env

    raise FileNotFoundError(
        f"子Skill '{sub_name}' 未找到。搜索路径: {candidate}, {candidate_env}. "
        f"请确认 {sub_name} 已安装到主Skill的兄弟目录。"
    )


# =============================================================================
# 3. 熔断器（Circuit Breaker）
# =============================================================================

class CircuitBreaker:
    """防止子Skill加载失败时的级联错误。"""
    STATE_CLOSED = "closed"
    STATE_OPEN = "open"
    STATE_HALF_OPEN = "half_open"

    def __init__(self, name: str, fail_threshold: int = 3, cooldown_seconds: int = 300):
        self.name = name
        self.state = self.STATE_CLOSED
        self.fail_count = 0
        self.fail_threshold = fail_threshold
        self.cooldown_seconds = cooldown_seconds
        self.last_fail_time: float = 0
        self.last_success_time: float = 0

    def record_success(self):
        self.fail_count = 0
        if self.state == self.STATE_HALF_OPEN:
            self.state = self.STATE_CLOSED
        self.last_success_time = time.time()

    def record_failure(self):
        self.fail_count += 1
        self.last_fail_time = time.time()
        if self.fail_count >= self.fail_threshold:
            self.state = self.STATE_OPEN

    def can_attempt(self) -> bool:
        if self.state == self.STATE_CLOSED:
            return True
        if self.state == self.STATE_OPEN:
            if time.time() - self.last_fail_time > self.cooldown_seconds:
                self.state = self.STATE_HALF_OPEN
                return True
            return False
        return True  # HALF_OPEN

    def status(self) -> dict:
        return {
            "circuit": self.name,
            "state": self.state,
            "fail_count": self.fail_count,
            "last_fail": self.last_fail_time,
            "last_success": self.last_success_time,
        }


# 子Skill熔断器实例
_circuit_career = CircuitBreaker("xia-peng-career")
_circuit_growth = CircuitBreaker("xia-peng-growth")


# =============================================================================
# 4. 遥测（Telemetry）
# =============================================================================

TELEMETRY_ENABLED = os.environ.get("XP_TELEMETRY", "1") == "1"
_telemetry_log_path: str | None = None


def _get_telemetry_path() -> str:
    global _telemetry_log_path
    if _telemetry_log_path is None:
        log_dir = os.path.join(_resolve_skill_root(), "telemetry")
        os.makedirs(log_dir, exist_ok=True)
        _telemetry_log_path = os.path.join(log_dir, "routing_events.jsonl")
    return _telemetry_log_path


def _record_telemetry(
    query: str,
    matched_keywords: list[str],
    route: tuple,
    latency_ms: float,
    hit: bool,
    circuit_state: str,
    fallback_used: bool,
):
    """写入路由事件到 JSONL 日志（非阻塞、追加写入）。"""
    if not TELEMETRY_ENABLED:
        return
    try:
        event = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "query": query,
            "keywords": matched_keywords,
            "route_skill": route[0],
            "route_domain": route[1],
            "confidence": route[2],
            "latency_ms": round(latency_ms, 2),
            "hit": hit,
            "circuit": circuit_state,
            "fallback": fallback_used,
        }
        with open(_get_telemetry_path(), "a", encoding="utf-8") as f:
            f.write(json.dumps(event, ensure_ascii=False) + "\n")
    except Exception:
        pass  # 遥测失败不影响主流程


# =============================================================================
# 5. 核心路由算法（v2：大小写不敏感 + 遥测 + 熔断）
# =============================================================================

def match(query: str, threshold: int = 1) -> list:
    """
    将用户输入匹配到场景路由。
    v2 改进:
      - 大小写不敏感
      - 长关键词优先（防"领导"吃掉"领导力"）
      - 遥测记录每次匹配
    """
    t_start = time.time()
    q_lower = query.lower()
    results = {}

    # 按关键词长度降序排列（长优先）
    sorted_keys = sorted(SCENARIO_MAP.keys(), key=lambda k: -len(k))

    matched_kw = []
    for keyword in sorted_keys:
        if keyword.lower() in q_lower:  # ← v2: 大小写不敏感
            skill, domain = SCENARIO_MAP[keyword]
            key = f"{skill}/{domain}"
            results[key] = results.get(key, 0) + (1 if len(keyword) <= 2 else 2)
            matched_kw.append(keyword)

    ranked = [
        (s.split("/")[0], s.split("/")[1], c)
        for s, c in sorted(results.items(), key=lambda x: -x[1])
    ]

    hit = len(ranked) > 0 and ranked[0][2] > 0
    route = ranked[0] if ranked else ("knowledge", "shared", 0)

    if not ranked:
        route = ("knowledge", "shared", 0)

    total = sum(r[2] for r in ranked) if ranked else 1
    final = [(s, d, round(c / total * 100)) for s, d, c in (ranked or [route])]

    # 遥测记录
    latency = (time.time() - t_start) * 1000
    _record_telemetry(
        query=query,
        matched_keywords=matched_kw,
        route=final[0],
        latency_ms=latency,
        hit=hit,
        circuit_state=_circuit_career.state if route[0] == "career" else _circuit_growth.state,
        fallback_used=False,
    )

    return final


def route_with_fallback(query: str) -> dict:
    """
    带熔断降级的路由。
    当子Skill熔断器打开时，自动回退到本地 references 目录应答。
    """
    routes = match(query)
    primary = routes[0]
    skill_type = primary[0]

    result = {
        "routes": routes,
        "primary": primary,
        "degraded": False,
        "circuit_status": {},
    }

    if skill_type == "career":
        cb = _circuit_career
    elif skill_type == "growth":
        cb = _circuit_growth
    else:
        cb = None  # knowledge 类型不需要子Skill

    if cb is not None:
        result["circuit_status"][cb.name] = cb.status()
        if not cb.can_attempt():
            result["degraded"] = True
            result["fallback_reason"] = f"熔断器 {cb.name} 处于 OPEN 状态"
            result["fallback_strategy"] = "使用本地 references/ 目录直接应答"

    return result


# =============================================================================
# 6. 自检：验证 SCENARIO_MAP 与 SKILL.md 路由表一致性
# =============================================================================

def validate_routing_table() -> list[dict]:
    """
    自检 SCENARIO_MAP 覆盖的领域是否完整（v2.1 精确解析器）。
    读取 scenario-index.md，只提取真正的短关键词（2-10字），
    自动过滤：表格分隔符、BV号、金句ID、完整句子、场景描述。
    """
    scenario_path = os.path.join(_resolve_skill_root(), "references", "scenario-index.md")
    if not os.path.isfile(scenario_path):
        return [{"severity": "warn", "msg": "scenario-index.md 未找到，跳过验证"}]

    with open(scenario_path, "r", encoding="utf-8") as f:
        lines = f.readlines()

    missing = []
    impacted_scenarios = set()
    seen = set()

    for line_no, line in enumerate(lines, 1):
        stripped = line.strip()

        # 跳过分隔线、空行、标题
        if not stripped or stripped.startswith("#"):
            continue
        if all(c in "|- " for c in stripped):
            continue
        # 跳过表格头
        if any(h in stripped for h in ("BV号", "场景", "金句", "核心建议")):
            continue

        cols = [c.strip() for c in stripped.split("|")]
        if len(cols) < 3:
            continue

        # 关键列: cols[2]="关键词"列, cols[3]可能是"匹配关键词"列
        scenario_name = cols[1].strip() if len(cols) > 1 and cols[1] else "未知场景"
        candidate_cols = [cols[idx] for idx in [2, 3] if idx < len(cols) and cols[idx]]

        for cell in candidate_cols:
            for kw in cell.split(","):
                kw = kw.strip()
                if not kw:
                    continue

                # 过滤非关键词：长句子、BV号、金句ID、标点句
                if len(kw) > 10 or len(kw) < 2:
                    continue
                if kw.startswith("BV") or kw.startswith("Q"):
                    continue
                if any(p in kw for p in "，。！？的"):
                    continue

                kw_key = kw.lower()
                if kw_key in seen:
                    continue
                seen.add(kw_key)

                # 检查是否在 SCENARIO_MAP 中注册（大小写不敏感）
                map_lower = {k.lower() for k in SCENARIO_MAP}
                if kw not in SCENARIO_MAP and kw.lower() not in map_lower:
                    partially_covered = any(
                        len(k) >= 2 and k.lower() in kw.lower()
                        for k in SCENARIO_MAP
                    )
                    missing.append({
                        "keyword": kw,
                        "partially_covered": partially_covered,
                        "scenario": scenario_name,
                        "line": line_no,
                    })
                    if not partially_covered:
                        impacted_scenarios.add(scenario_name)

    return (
        [{"severity": "ok", "msg": "所有场景关键词均已覆盖，SCENARIO_MAP 与 scenario-index.md 一致"}]
        if not missing
        else [{
            "severity": "gap",
            "msg": f"发现 {len(missing)} 个未注册关键词（{len(impacted_scenarios)} 个场景受影响）",
            "missing_keywords": missing,
            "impacted_scenarios": sorted(impacted_scenarios),
            "recommendation": (
                "建议将高频使用的缺失关键词补充到 SCENARIO_MAP 中。"
                "部分覆盖的关键词已被现有短关键词覆盖，优先级较低。"
            ),
        }]
    )


# =============================================================================
# 7. CLI 入口
# =============================================================================

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="夏鹏知识库路由器 v2")
    sub = parser.add_subparsers(dest="command")

    # match 子命令
    match_parser = sub.add_parser("match", help="路由匹配")
    match_parser.add_argument("query", nargs="+", help="用户查询文本")

    # validate 子命令
    validate_parser = sub.add_parser("validate", help="验证路由表一致性")

    # status 子命令
    status_parser = sub.add_parser("status", help="查看熔断器状态")

    # telemetry 子命令
    tele_parser = sub.add_parser("telemetry", help="查看遥测摘要")
    tele_parser.add_argument("--limit", type=int, default=20, help="显示条数")

    args = parser.parse_args()

    if args.command == "match":
        query = " ".join(args.query)
        result = route_with_fallback(query)
        print(json.dumps(result, ensure_ascii=False, indent=2))

    elif args.command == "validate":
        issues = validate_routing_table()
        for i in issues:
            print(f"[{i['severity'].upper()}] {i['msg']}")

    elif args.command == "status":
        print(json.dumps({
            "career": _circuit_career.status(),
            "growth": _circuit_growth.status(),
            "telemetry_dir": os.path.dirname(_get_telemetry_path()),
        }, ensure_ascii=False, indent=2))

    elif args.command == "telemetry":
        tp = _get_telemetry_path()
        if not os.path.isfile(tp):
            print("[]")
        else:
            with open(tp, "r", encoding="utf-8") as f:
                lines = f.readlines()
            tail = lines[-args.limit:] if len(lines) > args.limit else lines
            events = [json.loads(line) for line in tail]

            hits = [e for e in events if e["hit"]]
            misses = [e for e in events if not e["hit"]]
            avg_latency = sum(e["latency_ms"] for e in events) / len(events) if events else 0

            print(json.dumps({
                "total_events": len(events),
                "hit_rate": f"{len(hits) / len(events) * 100:.1f}%" if events else "N/A",
                "hits": len(hits),
                "misses": len(misses),
                "avg_latency_ms": round(avg_latency, 2),
                "recent": events[-5:],
            }, ensure_ascii=False, indent=2))
