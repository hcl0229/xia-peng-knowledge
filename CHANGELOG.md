# 变更日志

## 3.0.0 (2026-06-11)
- Phase 3 完成
  - 关键词自动扩展引擎 (auto_expand.py): 208→81 缺口 (61%减少)
  - Telemetry 反馈回路 (analyze 命令): MISS 分析 + 路由分布 + 自适应阈值
  - 自适应路由 (match_adaptive): 置信度分级 HIGH/MEDIUM/LOW
  - 内容新鲜度监控 (freshness_monitor.py): 11个文件追踪 + 版本一致性
  - 127个高置信度关键词自动合并到 SCENARIO_MAP

## 2.1.0 (2026-06-11)
- Phase 2 优化完成
  - `.skill` 打包纳入 `scripts/` 目录（build_skill.py + 完整性验证）
  - `validate_routing_table()` v2.1 精确解析器（过滤句子/BV号/金句ID）
  - GitHub CI 集成（.github/workflows/auto_test.yml — push/PR/每日触发）
  - GitHub Repo: https://github.com/hcl0229/xia-peng-knowledge

## 2.0 (2026-06-11)
- Router v2：大小写不敏感 + Circuit Breaker + Telemetry
- Auto Test Suite（31 测试用例 + 监控模式）
- P0 关键词缺口修复（6个）
- 边缘场景命中率：42% → 96.8%
- 动态路径解析（消除硬编码）

## 1.0.0 (2026-06-10)
- 初始版本
