# 变更日志

## 2.1 (2026-06-11)
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
