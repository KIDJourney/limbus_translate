# Handoff

本文档维护最近一次工作交接记录。每次完成实质性变更后，把本轮结果追加到顶部。

## 2026-06-13 — Limbus Translate 初版工具骨架

### 已完成

- 使用 `ai-workspace-init` 初始化 `/Users/kidjourney/Project/limbus_translate`，验证通过 31 个 Markdown 文件。
- 克隆并研究 LocalizeLimbusCompany 临时 checkout：`/tmp/limbus-translate-work/LocalizeLimbusCompany`。
- 新增 Python CLI 包 `limbus_translate`：
  - `scan`：扫描 `KR` 与 `LLC_zh-CN` 的待译单元。
  - `glossary sync-paratranz`：同步 Paratranz 项目 `6860` 术语。
  - `glossary import`：离线导入 CSV / JSON 术语。
  - `translate`：用 provider 生成同结构输出，默认 `dry-run`。
  - `lore import`：把 Markdown / JSON / JSONL / CSV / TXT 世界观资料导成可召回 cache。
  - `context.py`：为 provider 构建结构化 `TranslationContextBundle`，包含位置、风险、术语、同文件邻近文本、同文件 TM、跨文件相似 TM 示例和 lore 片段。
  - `qa`：检查韩文残留、占位符、标签、数字、换行、术语命中和路径/risk 字符级 length policy，并输出 MQM 风格类别汇总。
  - `tm build`：构建 exact-match 翻译记忆。
  - `terms extract`：从新增文本提取候选术语/短语缓存。
  - `terms refine`：用 `rules` / `openai` provider 将候选分为 `term` / `not_term` / `needs_review`，写入 refined cache。
  - `terms promote`：把已确认且有译名的 refined term 写成本地 glossary cache，可与 Paratranz cache 合并。
  - `state init`：初始化 `new` / `reviewed` / `locked` 单元状态，翻译时跳过锁定单元。
- 新增测试夹具和直接单元测试入口。
- 新增调研文档：[translation-framework.md](../research/translation-framework.md) 与 [localize-data-study.md](../tech/localize-data-study.md)。

### 验证状态

- `python3 -m limbus_translate.cli scan --source tests/fixtures/localize/KR --target tests/fixtures/localize/LLC_zh-CN --output /tmp/limbus-missing.json`：通过，输出 2 条。
- 直接调用 `tests.test_scanner` 和 `tests.test_glossary`：通过。
- `python3 -m limbus_translate.cli glossary sync-paratranz --page-size 1000 --output /tmp/limbus-paratranz.json`：通过，同步 1963 条。
- `python3 -m limbus_translate.cli translate ... --provider dry-run`：通过，输出同结构 JSON。
- 真实 Localize checkout 扫描：通过；默认输出 19 条 `target_same_as_source`，全部为 `StoryData/*.content` 高风险文本；`--include-internal` 可审计 263 条完整同源残留。
- 真实 Localize TM 构建：通过，输出 92337 条 exact-match 记忆。
- 真实新增文本术语候选提取：通过，输出 19 条候选；heuristic 会包含短语/整句，需 LLM 或人工二筛。
- `terms refine --provider rules`：fixture smoke 通过，输出 3 条 refined 记录，决策分布为 `needs_review=1`、`not_term=2`；真实 Localize 候选 19 条 refine 通过，输出 `needs_review=10`、`not_term=9`。
- `terms promote`：单元测试验证只导出 `decision=term` 且有 `suggested_target` 的记录；fixture smoke 通过，生成 `build/local-refined-glossary.json`；真实 rules refined promote 通过但输出 0 条，因为 rules provider 不生成建议译名。
- 缺失 `dataList` record 写回：fixture 测试通过，`translate` 会 append 源 record 并替换待译字段。
- `reviewed` / `locked` 状态：fixture 测试通过，锁定单元不会被 `translate` 覆盖。
- 结构化上下文包：`tests.test_context.test_translate_provider_receives_structured_context` 和 `tests.test_context.test_context_includes_cross_file_similar_memory` 通过，provider 收到术语、邻近文本、同文件 TM、跨文件相似 TM 示例和 lore 片段；真实 Localize checkout 带 `cache/tm/exact.json` dry-run translate 限制 3 条通过。
- 世界观资料缓存：`tests.test_lore` 验证 Markdown / JSON 导入、cache roundtrip、anchors 召回；`make smoke` 验证 `lore import --input tests/fixtures/lore` 和 `translate --lore build/lore.json` 链路。
- QA 简繁、长度风险、路径/risk 字符级 length policy 和 MQM category/summary：fixture 测试通过；真实 dry-run QA 小样本输出 19 条 accuracy 类 issue，报告字段落盘正常；`make smoke` 已验证 `qa --length-policy config/length-policy.sample.json` 可读。
- `python3 -m pytest -q` 未运行成功，因为系统 Python 没有安装 `pytest`；已用无依赖直接测试替代。

### 风险

- 当前扫描支持唯一、非 `-1` 的 `dataList[*].id` 主键对齐；重复 id 或 `id=-1` 会回退 JSON path，避免 StoryData 误对齐。
- 当前 QA 已覆盖韩文残留、占位符、标签、数字、换行、术语命中、疑似繁体、路径/risk 字符级 length policy 和 MQM 风格分类，但还没有像素级 UI 长度。
- 当前 lore cache 是关键词/anchors 召回，不是向量检索；真实世界观资料仍需整理为本地笔记或外部知识源导入。
- 当前术语候选提取和 rules refiner 只是自动粗筛；OpenAI provider 也只能给建议译名，正式术语仍需人工确认后通过 `terms promote` 进入 termbase。
- Chrome 插件连接 Paratranz 页面失败，但子任务已通过公开 API 证明术语可读；若要用 Chrome，需要用户允许打开 Chrome 窗口刷新扩展连接。

### 下一步

- 补像素级 UI 长度检查和具体 UI 容器策略。
- 把本地 promoted glossary 与 Paratranz 或审校系统的正式 termbase 同步，并把 lore cache 升级为向量检索和经过 gold set 调参的相似句检索。
- 建立 500-1000 条 gold set，用于模型赛马和 prompt 回归。

## 2026-06-09 — 文档骨架初版

### 已完成

- 创建根目录 `AGENTS.md`、`CLAUDE.md`、`README.md`。
- 创建 `docs/product/`、`docs/design/`、`docs/tech/`、`docs/test/`、`docs/verification/`、`docs/agent/`、`docs/templates/`。
- 创建最小文档验证脚本 `scripts/validate-docs.sh` 和 `Makefile` 入口。
- 将验证记录从 `docs/test/` 拆到 `docs/verification/`，支持按业务场景维护验证方法和证据。
- 创建 `scripts/init-ai-workspace.sh`，用于把模板复制到其他项目且不覆盖已有文件。
- 创建用户级 skill `ai-workspace-init`，用于让 Codex 按固定流程初始化 AI Workspace 文档结构。

### 验证状态

- `make validate-docs`：通过，输出见最新验证记录。

### 风险

- 当前只是文档系统初版，未绑定具体应用技术栈。
- 验证脚本只检查结构和链接，不检查内容质量。

### 下一步

- 根据用户观察反馈调整目录命名、文档粒度和模板。
- 如果确认结构可用，补充初始化脚本或真实应用代码目录。
