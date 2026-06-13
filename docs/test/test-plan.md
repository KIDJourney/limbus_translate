# Test Plan

本文档维护 Limbus Translate 当前测试策略和验收口径。

## 测试目标

1. 确认 JSON 扫描能识别目标缺失、目标为空、目标等于韩文源文、源文相对 baseline 变化的待译单元。
2. 确认 Paratranz 术语缓存能同步、离线导入，并能被审计出明显质量问题。
3. 确认 dry-run 翻译能生成同结构输出 JSON，并能记录候选缓存与逐条 trace。
4. 确认文档骨架和 Markdown 相对链接不损坏。

## 当前覆盖

| 测试 | 覆盖范围 | 命令 |
|---|---|---|
| 文档结构检查 | 根目录入口、关键目录、关键 README 是否存在 | `make validate-docs` |
| Markdown 链接检查 | `docs/` 和根目录入口中的相对 Markdown 链接 | `make validate-docs` |
| 直接单元测试 | 扫描器、scan policy include/exclude、changed-files 文件级增量扫描、source-baseline JSON path 级源文变化扫描、术语匹配、glossary audit、lore cache 导入/anchors 召回/TF-IDF 相似召回/lore index roundtrip 与搜索、gold set 构建/分层采样/gold review pack/gold review apply/eval report/eval comparison、translation review pack/apply、provider candidate cache 复用、translation trace、refined term promote、term review pack、review CSV apply、MQM category/summary、QA length policy 和估算显示宽度、ContextBundle/provider context 传递、跨文件相似 TM 召回核心行为 | `make test` |
| CLI smoke | 带 scan policy、changed-files 和 source-baseline 的 fixture 扫描、TM 构建、glossary audit、lore import、lore index/search、state 初始化、带 lore index 的 dry-run 同结构输出、candidate cache、translation trace、带 length policy 的 QA 报告、translation review pack/apply、gold set 构建、gold sample、gold review pack、curated gold、eval report、eval compare report、术语候选缓存、rules 二次提炼缓存、review pack、review apply、promoted glossary cache，以及带 glossary audit / candidate cache / trace 的 `workflow run` 端到端 summary 和术语审校包 artifact | `make smoke` |
| Paratranz smoke | 项目 `6860` 术语同步 | `make sync-glossary` |
| TODO / 待确认扫描 | 发现未解决问题和阻塞项 | `rg "TODO|待确认|阻塞" docs` |

## 验收标准

1. `make validate-docs` 通过。
2. `make test` 通过。
3. `make smoke` 通过，输出 `build/changed-files.txt`、`build/missing-units.json`、`build/source-changed-units.json`、`build/tm.json`、`build/glossary-audit.json`、`build/lore.json`、`build/lore-index.json`、`build/lore-search.json`、`build/state.json`、`build/translation-candidates.json`、`build/translation-trace.jsonl`、`build/LLC_zh-CN/Sample.json`、按 `config/length-policy.sample.json` 检查的 `build/qa-report.json`、`build/translation-review/review.csv`、`build/translation-review/review.jsonl`、`build/reviewed-state.json`、`build/gold-set.json`、`build/gold-sample.json`、`build/gold-review/review.csv`、`build/gold-review/review.jsonl`、`build/gold-curated.json`、`build/eval-report.json`、`build/eval-compare-report.json`、`build/term-candidates.json`、`build/refined-terms.json`、`build/term-review/review.csv`、`build/term-review/review.jsonl`、`build/term-review/paratranz-import.csv`、`build/local-reviewed-glossary.json`、`build/local-refined-glossary.json`、`build/workflow/missing-units.json`、`build/workflow/tm.json`、`build/workflow/glossary-audit.json`、`build/workflow/translation-candidates.json`、`build/workflow/translation-trace.jsonl`、`build/workflow/term-candidates.json`、`build/workflow/refined-terms.json`、`build/workflow/term-review/review.csv`、`build/workflow/term-review/review.jsonl`、`build/workflow/term-review/paratranz-import.csv`、`build/workflow/translation-review/review.csv`、`build/workflow/translation-review/review.jsonl`、`build/workflow/lore-index.json`、`build/workflow/qa-report.json`、`build/workflow/summary.json` 和 `build/workflow/LLC_zh-CN/Sample.json`。
4. `make sync-glossary` 能同步 1963 条左右术语；若 Paratranz API 不可用，应使用离线导入兜底。
5. 真实 Localize checkout 扫描结果需要人工审查；`--scan-policy config/scan-policy.sample.json` 可用于沉淀文件类型规则，但不能把未审规则直接当上线依据。

## 回归要求

以下变化必须重新执行对应验证：

- 修改 `json_paths.py`、`scanner.py` 或 `config/scan-policy.sample.json`：执行 `make test`、`make smoke` 和真实 checkout 扫描。
- 修改 `glossary.py`：执行 `make test`、`make smoke`、`make sync-glossary` 和一次真实 glossary audit。
- 修改 `lore.py`、`context.py`、`translator.py`、`translation_cache.py` 或 provider：执行 `make test` 和 `make smoke`。
- 修改 `cli.py` 的 `workflow run` 或其串联模块：执行 `make test`、`make smoke`、`make validate-docs` 和至少一次真实 checkout 小范围 workflow。
- 修改 `evaluation.py` 或 gold set schema：执行 `make test` 和 `make smoke`。
- 修改 `terms.py` 或 term refiner provider：执行 `make test` 和 `make smoke`；OpenAI term refiner 变化至少需要 mock/fixture 验证，真实 API 调用单独记录。
- 修改 `qa.py` 或 `config/length-policy.sample.json`：执行 `make test` 和 `make smoke`。
- 修改 `review.py` 或 review CLI：执行 `make test`、`make smoke` 和真实 checkout review pack/apply 小样本。
- 修改文档或 Markdown 链接：执行 `make validate-docs`。
