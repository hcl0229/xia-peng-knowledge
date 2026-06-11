"""夏鹏场景匹配器 — 关键词路由"""

SCENARIO_MAP = {
    # 向上汇报 (长关键词优先)
    "年终总结": ("career", "upward-management"),
    "周报": ("career", "upward-management"),
    "述职": ("career", "upward-management"),
    "汇报": ("career", "upward-management"),
    "加薪": ("career", "upward-management"),
    "涨薪": ("career", "upward-management"),
    "谈薪": ("career", "upward-management"),

    # 向上管理 (不含"领导力"避免冲突)
    "向上管理": ("career", "upward-management"),
    "PUA": ("career", "upward-management"),
    "派杂活": ("career", "upward-management"),
    "老板": ("career", "upward-management"),
    "背刺": ("career", "upward-management"),
    "甩锅": ("career", "upward-management"),

    # 跳槽与面试
    "跳槽": ("career", "upward-management"),
    "离职": ("career", "upward-management"),
    "辞职": ("career", "upward-management"),
    "面试": ("career", "upward-management"),
    "求职": ("career", "upward-management"),

    # 领导力 (必须放在"领导"前)
    "领导力": ("career", "leadership"),
    "管理者": ("career", "leadership"),
    "领导者": ("career", "leadership"),
    "晋升": ("career", "leadership"),
    "空降": ("career", "leadership"),
    "提拔": ("career", "leadership"),
    "领导团队": ("career", "leadership"),

    # 团队管理
    "团队": ("career", "team-management"),
    "执行力": ("career", "team-management"),
    "团队执行力": ("career", "team-management"),
    "下属": ("career", "team-management"),
    "带人": ("career", "team-management"),
    "授权": ("career", "team-management"),
    "激励": ("career", "team-management"),
    "开会": ("career", "team-management"),
    "员工": ("career", "team-management"),

    # 职场沟通
    "沟通": ("career", "workplace-comm"),
    "情商": ("career", "workplace-comm"),
    "拒绝": ("career", "workplace-comm"),
    "表达": ("career", "workplace-comm"),
    "说服": ("career", "workplace-comm"),
    "尬聊": ("career", "workplace-comm"),

    # 个人成长
    "成长": ("growth", "growth-scenarios"),
    "自律": ("growth", "growth-scenarios"),
    "习惯": ("growth", "growth-scenarios"),
    "执行力": ("growth", "growth-scenarios"),
    "格局": ("growth", "growth-scenarios"),
    "气场": ("growth", "growth-scenarios"),
    "逻辑": ("growth", "growth-scenarios"),
    "思维": ("growth", "growth-scenarios"),
    "内卷": ("growth", "growth-scenarios"),
    "摆烂": ("growth", "growth-scenarios"),

    # 情绪管理
    "情绪": ("growth", "growth-scenarios"),
    "焦虑": ("growth", "growth-scenarios"),
    "内耗": ("growth", "growth-scenarios"),
    "心态": ("growth", "growth-scenarios"),
    "自信": ("growth", "growth-scenarios"),

    # 人际关系
    "人脉": ("growth", "people-skills"),
    "社交": ("growth", "people-skills"),
    "破冰": ("growth", "people-skills"),
    "小人": ("growth", "people-skills"),
    "站队": ("growth", "people-skills"),

    # 副业学习
    "副业": ("growth", "side-learning"),
    "赚钱": ("growth", "side-learning"),
    "创业": ("growth", "side-learning"),
    "学习": ("growth", "side-learning"),
    "读书": ("growth", "side-learning"),
    "新领域": ("growth", "side-learning"),
    "自学": ("growth", "side-learning"),

    # AI
    "AI": ("knowledge", "shared"),
    "人工智能": ("knowledge", "shared"),
    "DeepSeek": ("knowledge", "shared"),
    "工具": ("knowledge", "shared"),
}


def match(query: str, threshold: int = 1) -> list:
    """匹配用户输入到场景路由。
    长关键词优先匹配，短关键词只作为补充。
    """
    results = {}
    # 先按关键词长度排序（长优先），避免"领导"吃掉"领导力"
    sorted_keys = sorted(SCENARIO_MAP.keys(), key=lambda k: -len(k))
    for keyword in sorted_keys:
        if keyword in query:
            skill, domain = SCENARIO_MAP[keyword]
            key = f"{skill}/{domain}"
            results[key] = results.get(key, 0) + (1 if len(keyword) <= 2 else 2)
    ranked = [(s.split("/")[0], s.split("/")[1], c) for s, c in sorted(results.items(), key=lambda x: -x[1])]
    if not ranked:
        return [("knowledge", "shared", 0)]
    total = sum(r[2] for r in ranked)
    return [(s, d, round(c / total * 100)) for s, d, c in ranked]


if __name__ == "__main__":
    test_queries = [
        "我要写周报了",
        "老板给我派杂活怎么办",
        "想跳槽但不确定",
        "怎么跟领导提涨薪",
        "工作没动力了",
        "用夏鹏的方式写年终总结",
        "夏鹏关于AI怎么说的",
        "最近情绪不好老内耗",
        "怎么拒绝同事的请求",
        "如何培养气场",
    ]
    for q in test_queries:
        result = match(q)
        print(f"  {q:25s} → {result}")
