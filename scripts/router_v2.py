r"""
夏鹏知识库路由器 v3 -- 自主优化架构
======================================
v2 -> v3 变更:
  - Phase 3: 关键词自动扩展 (127 个新关键词)
  - Phase 3: 反馈回路 (analyze 命令)
  - Phase 3: 自适应路由 (match_adaptive)
  - Phase 3: 置信度分级 (HIGH/MEDIUM/LOW)
"""

import json
import os
import sys
import time
from collections import defaultdict
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

    # ── 领导力 (Phase 3 扩展) ──
    "升职":       ('career', 'leadership'),
    "升职条件":       ('career', 'leadership'),
    "威严":       ('career', 'leadership'),
    "怎么升职":       ('career', 'leadership'),
    "权威":       ('career', 'leadership'),
    "标准":       ('career', 'leadership'),
    "评估":       ('career', 'leadership'),

    # ── 团队管理 (Phase 3 扩展) ──
    "KPI":       ('career', 'team-management'),
    "OKR":       ('career', 'team-management'),
    "优化":       ('career', 'team-management'),
    "会议":       ('career', 'team-management'),
    "凝聚力":       ('career', 'team-management'),
    "团结":       ('career', 'team-management'),
    "士气":       ('career', 'team-management'),
    "干劲":       ('career', 'team-management'),
    "开人":       ('career', 'team-management'),
    "归属感":       ('career', 'team-management'),
    "打分":       ('career', 'team-management'),
    "效率":       ('career', 'team-management'),
    "方向":       ('career', 'team-management'),
    "淘汰":       ('career', 'team-management'),
    "炒人":       ('career', 'team-management'),
    "目标":       ('career', 'team-management'),
    "绩效":       ('career', 'team-management'),
    "绩效面谈":       ('career', 'team-management'),
    "考核":       ('career', 'team-management'),
    "辞退":       ('career', 'team-management'),
    "驱动":       ('career', 'team-management'),
    "高效":       ('career', 'team-management'),

    # ── 向上管理/汇报 (Phase 3 扩展) ──
    "主动同步":       ('career', 'upward-management'),
    "人情":       ('career', 'upward-management'),
    "人际关系":       ('career', 'upward-management'),
    "信任":       ('career', 'upward-management'),
    "信任积累":       ('career', 'upward-management'),
    "关系":       ('career', 'upward-management'),
    "关系升温":       ('career', 'upward-management'),
    "关系处理":       ('career', 'upward-management'),
    "关系维护":       ('career', 'upward-management'),
    "可靠":       ('career', 'upward-management'),
    "同步":       ('career', 'upward-management'),
    "周总结":       ('career', 'upward-management'),
    "如何相处":       ('career', 'upward-management'),
    "威信":       ('career', 'upward-management'),
    "存在感":       ('career', 'upward-management'),
    "工作反馈":       ('career', 'upward-management'),
    "年度":       ('career', 'upward-management'),
    "年度总结":       ('career', 'upward-management'),
    "年终":       ('career', 'upward-management'),
    "建立威信":       ('career', 'upward-management'),
    "总结":       ('career', 'upward-management'),
    "总结教训":       ('career', 'upward-management'),
    "感恩":       ('career', 'upward-management'),
    "感恩练习":       ('career', 'upward-management'),
    "报告":       ('career', 'upward-management'),
    "择主":       ('career', 'upward-management'),
    "换工作":       ('career', 'upward-management'),
    "曝光":       ('career', 'upward-management'),
    "相处之道":       ('career', 'upward-management'),
    "礼物":       ('career', 'upward-management'),
    "节日":       ('career', 'upward-management'),
    "裸辞":       ('career', 'upward-management'),
    "进展":       ('career', 'upward-management'),
    "送礼":       ('career', 'upward-management'),
    "露脸":       ('career', 'upward-management'),
    "靠谱":       ('career', 'upward-management'),

    # ── 职场沟通 (Phase 3 扩展) ──
    "争取":       ('career', 'workplace-comm'),
    "冷场":       ('career', 'workplace-comm'),
    "口才":       ('career', 'workplace-comm'),
    "推掉":       ('career', 'workplace-comm'),
    "推销":       ('career', 'workplace-comm'),
    "提案":       ('career', 'workplace-comm'),
    "演讲":       ('career', 'workplace-comm'),
    "薪资谈判":       ('career', 'workplace-comm'),
    "说不":       ('career', 'workplace-comm'),
    "说话":       ('career', 'workplace-comm'),
    "说话艺术":       ('career', 'workplace-comm'),
    "谈判":       ('career', 'workplace-comm'),

    # ── 个人成长/情绪 (Phase 3 扩展) ──
    "不安":       ('growth', 'growth-scenarios'),
    "信心":       ('growth', 'growth-scenarios'),
    "冷静":       ('growth', 'growth-scenarios'),
    "分析":       ('growth', 'growth-scenarios'),
    "压力":       ('growth', 'growth-scenarios'),
    "发脾气":       ('growth', 'growth-scenarios'),
    "坚持":       ('growth', 'growth-scenarios'),
    "大局观":       ('growth', 'growth-scenarios'),
    "思考":       ('growth', 'growth-scenarios'),
    "思考力":       ('growth', 'growth-scenarios'),
    "恐慌":       ('growth', 'growth-scenarios'),
    "想太多":       ('growth', 'growth-scenarios'),
    "懒惰":       ('growth', 'growth-scenarios'),
    "担心":       ('growth', 'growth-scenarios'),
    "拖延":       ('growth', 'growth-scenarios'),
    "气质":       ('growth', 'growth-scenarios'),
    "洞见":       ('growth', 'growth-scenarios'),
    "消耗":       ('growth', 'growth-scenarios'),
    "深度思考":       ('growth', 'growth-scenarios'),
    "理性":       ('growth', 'growth-scenarios'),
    "眼界":       ('growth', 'growth-scenarios'),
    "稳定":       ('growth', 'growth-scenarios'),
    "纠结":       ('growth', 'growth-scenarios'),
    "自卑":       ('growth', 'growth-scenarios'),
    "自我怀疑":       ('growth', 'growth-scenarios'),
    "自我消耗":       ('growth', 'growth-scenarios'),
    "自我管理":       ('growth', 'growth-scenarios'),
    "自控":       ('growth', 'growth-scenarios'),
    "行动力":       ('growth', 'growth-scenarios'),
    "视野":       ('growth', 'growth-scenarios'),
    "认知":       ('growth', 'growth-scenarios'),
    "认知升级":       ('growth', 'growth-scenarios'),
    "魅力":       ('growth', 'growth-scenarios'),

    # ── 人际关系 (Phase 3 扩展) ──
    "人品":       ('growth', 'people-skills'),
    "分辨":       ('growth', 'people-skills'),
    "判断人":       ('growth', 'people-skills'),
    "回应":       ('growth', 'people-skills'),
    "圈子":       ('growth', 'people-skills'),
    "对话":       ('growth', 'people-skills'),
    "开启对话":       ('growth', 'people-skills'),
    "怎么接话":       ('growth', 'people-skills'),
    "接话":       ('growth', 'people-skills'),
    "搭讪":       ('growth', 'people-skills'),
    "看人":       ('growth', 'people-skills'),
    "聊天技巧":       ('growth', 'people-skills'),
    "识人":       ('growth', 'people-skills'),

    # ── AI/知识 (Phase 3 扩展) ──
    "大模型":       ('knowledge', 'shared'),
    "数字化":       ('knowledge', 'shared'),
    "智能管理":       ('knowledge', 'shared'),
    "自动化":       ('knowledge', 'shared'),

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
# 7. Phase 3: 反馈回路 — 遥测分析 + 自适应阈值
# =============================================================================

CONFIDENCE_LEVELS = {
    "HIGH": 80,
    "MEDIUM": 50,
    "LOW": 0,
}


def analyze_telemetry(days: int = 7) -> dict:
    """分析遥测数据，生成反馈报告。"""
    tp = _get_telemetry_path()
    if not os.path.isfile(tp):
        return {"status": "no_data", "msg": "遥测文件不存在，尚无路由事件记录"}

    with open(tp, "r", encoding="utf-8") as f:
        events = [json.loads(line) for line in f if line.strip()]

    if not events:
        return {"status": "empty", "msg": "遥测文件为空"}

    # 基本统计
    hits = [e for e in events if e["hit"]]
    misses = [e for e in events if not e["hit"]]
    total = len(events)

    # MISS 模式分析
    miss_queries = defaultdict(list)
    for e in misses:
        miss_queries[e["query"]].append(e)

    freq_misses = sorted(
        [{"query": q, "count": len(entries)} for q, entries in miss_queries.items()],
        key=lambda x: -x["count"],
    )[:10]

    # 路由分布
    route_dist = defaultdict(int)
    for e in events:
        route_dist[f"{e['route_skill']}/{e['route_domain']}"] += 1

    # 延迟趋势
    latencies = [e["latency_ms"] for e in events]
    avg_latency = sum(latencies) / len(latencies) if latencies else 0
    p99_latency = sorted(latencies)[int(len(latencies) * 0.99)] if len(latencies) >= 100 else max(latencies) if latencies else 0

    # 熔断事件
    circuit_opens = [e for e in events if e.get("circuit") == "open"]

    # 自适应阈值建议
    hit_rate = len(hits) / total * 100 if total else 0
    threshold_advice = _recommend_threshold(hit_rate, avg_latency)

    return {
        "status": "ok",
        "period": f"最近 {len(events)} 条事件",
        "metrics": {
            "total_events": total,
            "hit_rate": f"{hit_rate:.1f}%",
            "hits": len(hits),
            "misses": len(misses),
            "avg_latency_ms": round(avg_latency, 2),
            "p99_latency_ms": round(p99_latency, 2),
        },
        "top_miss_queries": freq_misses,
        "route_distribution": dict(sorted(route_dist.items(), key=lambda x: -x[1])),
        "circuit_events": len(circuit_opens),
        "threshold_recommendation": threshold_advice,
        "action_items": _generate_action_items(hit_rate, freq_misses, misses),
    }


def _recommend_threshold(hit_rate: float, avg_latency: float) -> dict:
    """基于历史数据推荐自适应阈值。"""
    if hit_rate >= 95:
        level = "HIGH"
        conf = 85
    elif hit_rate >= 85:
        level = "HIGH"
        conf = 75
    elif hit_rate >= 70:
        level = "MEDIUM"
        conf = 55
    else:
        level = "LOW"
        conf = 35

    return {
        "suggested_confidence_level": level,
        "suggested_threshold": conf,
        "rationale": f"基于 {hit_rate:.1f}% 命中率自动计算",
        "current_hit_rate": round(hit_rate, 1),
    }


def _generate_action_items(hit_rate: float, freq_misses: list, misses: list) -> list:
    """生成可执行的改进建议。"""
    items = []
    if hit_rate < 85:
        items.append({
            "priority": "high",
            "action": "运行 auto_expand.py 补充缺失关键词",
            "detail": f"当前命中率 {hit_rate:.1f}% 低于 85% 阈值",
        })

    if freq_misses:
        top = freq_misses[0]
        items.append({
            "priority": "medium",
            "action": f"高频 MISS: 「{top['query']}」出现 {top['count']} 次",
            "detail": "建议添加相关关键词到 SCENARIO_MAP",
        })

    if len(misses) > 10:
        items.append({
            "priority": "medium",
            "action": "积累足够 MISS 数据后手动审查边缘场景",
            "detail": f"当前 {len(misses)} 条 MISS 事件待审查",
        })

    if not items:
        items.append({
            "priority": "low",
            "action": "系统运行良好，无需立即行动",
            "detail": f"命中率 {hit_rate:.1f}%，路由健康",
        })

    return items


# ── 自适应路由：根据反馈动态调整阈值 ──

def match_adaptive(query: str) -> dict:
    """
    v3 自适应路由：
    基于历史遥测数据动态调整匹配严格度，
    并在低置信度时自动标记需要确认。
    """
    routes = match(query)
    top = routes[0]
    skill, domain, confidence = top

    # 从遥测分析获取建议阈值
    try:
        feedback = analyze_telemetry()
        threshold = feedback["threshold_recommendation"]["suggested_threshold"]
    except Exception:
        threshold = 50  # 默认阈值

    # 置信度分级
    if confidence >= 80:
        level = "HIGH"
        needs_confirm = False
    elif confidence >= threshold:
        level = "MEDIUM"
        needs_confirm = False
    else:
        level = "LOW"
        needs_confirm = confidence > 0  # 完全未命中不要求确认

    return {
        "routes": routes,
        "primary": top,
        "confidence_level": level,
        "needs_confirmation": needs_confirm,
        "adaptive_threshold": threshold,
        "suggestion": (
            None
            if not needs_confirm
            else f"低置信度路由 (LOW/{confidence}%)，建议确认你是否想问关于{get_domain_label(skill, domain)}的问题"
        ),
    }


def get_domain_label(skill: str, domain: str) -> str:
    """领域中文标签。"""
    labels = {
        ("career", "upward-management"): "向上管理/汇报",
        ("career", "leadership"): "领导力",
        ("career", "team-management"): "团队管理",
        ("career", "workplace-comm"): "职场沟通",
        ("growth", "growth-scenarios"): "个人成长/情绪",
        ("growth", "people-skills"): "人际关系",
        ("growth", "side-learning"): "副业/学习",
        ("knowledge", "shared"): "通用知识",
    }
    return labels.get((skill, domain), f"{skill}/{domain}")


# =============================================================================
# 8. CLI 入口
# =============================================================================

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="夏鹏知识库路由器 v3")
    sub = parser.add_subparsers(dest="command")

    # match 子命令
    match_parser = sub.add_parser("match", help="路由匹配")
    match_parser.add_argument("query", nargs="+", help="用户查询文本")
    match_parser.add_argument("--adaptive", action="store_true", help="使用自适应路由")

    # validate 子命令
    validate_parser = sub.add_parser("validate", help="验证路由表一致性")

    # status 子命令
    status_parser = sub.add_parser("status", help="查看熔断器状态")

    # telemetry 子命令
    tele_parser = sub.add_parser("telemetry", help="查看遥测摘要")
    tele_parser.add_argument("--limit", type=int, default=20, help="显示条数")

    # analyze 子命令 (Phase 3 新增)
    analyze_parser = sub.add_parser("analyze", help="遥测分析 + 自适应建议")
    analyze_parser.add_argument("--days", type=int, default=7, help="分析天数")

    args = parser.parse_args()

    if args.command == "match":
        query = " ".join(args.query)
        if args.adaptive:
            result = match_adaptive(query)
        else:
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

    elif args.command == "analyze":
        report = analyze_telemetry(args.days)
        print(json.dumps(report, ensure_ascii=False, indent=2))

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
