# Test Plan

本文档维护 Limbus Translate 当前测试策略和验收口径。

## 测试目标

1. 确认 JSON 扫描能识别目标缺失、目标为空、目标等于韩文源文的待译单元。
2. 确认 Paratranz 术语缓存能同步或离线导入。
3. 确认 dry-run 翻译能生成同结构输出 JSON。
4. 确认文档骨架和 Markdown 相对链接不损坏。

## 当前覆盖

| 测试 | 覆盖范围 | 命令 |
|---|---|---|
| 文档结构检查 | 根目录入口、关键目录、关键 README 是否存在 | `make validate-docs` |
| Markdown 链接检查 | `docs/` 和根目录入口中的相对 Markdown 链接 | `make validate-docs` |
| 直接单元测试 | 扫描器、术语匹配、refined term promote、MQM category/summary、QA length policy、ContextBundle/provider context 传递、跨文件相似 TM 召回核心行为 | `make test` |
| CLI smoke | fixture 扫描、TM 构建、state 初始化、dry-run 同结构输出、带 length policy 的 QA 报告、术语候选缓存、rules 二次提炼缓存和 promoted glossary cache | `make smoke` |
| Paratranz smoke | 项目 `6860` 术语同步 | `make sync-glossary` |
| TODO / 待确认扫描 | 发现未解决问题和阻塞项 | `rg "TODO|待确认|阻塞" docs` |

## 验收标准

1. `make validate-docs` 通过。
2. `make test` 通过。
3. `make smoke` 通过，输出 `build/missing-units.json`、`build/tm.json`、`build/state.json`、`build/LLC_zh-CN/Sample.json`、按 `config/length-policy.sample.json` 检查的 `build/qa-report.json`、`build/term-candidates.json`、`build/refined-terms.json` 和 `build/local-refined-glossary.json`。
4. `make sync-glossary` 能同步 1963 条左右术语；若 Paratranz API 不可用，应使用离线导入兜底。
5. 真实 Localize checkout 扫描结果需要人工审查，不能把内部标识直接当缺译上线。

## 回归要求

以下变化必须重新执行对应验证：

- 修改 `json_paths.py` 或 `scanner.py`：执行 `make test` 和真实 checkout 扫描。
- 修改 `glossary.py`：执行 `make test` 和 `make sync-glossary`。
- 修改 `context.py`、`translator.py` 或 provider：执行 `make test` 和 `make smoke`。
- 修改 `terms.py` 或 term refiner provider：执行 `make test` 和 `make smoke`；OpenAI term refiner 变化至少需要 mock/fixture 验证，真实 API 调用单独记录。
- 修改 `qa.py` 或 `config/length-policy.sample.json`：执行 `make test` 和 `make smoke`。
- 修改文档或 Markdown 链接：执行 `make validate-docs`。
