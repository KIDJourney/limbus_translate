# Handoff

本文档维护最近一次工作交接记录。每次完成实质性变更后，把本轮结果追加到顶部。

## 2026-06-13 — 翻译审校包与 state 回写

### 已完成

- 新增 `limbus_translate/review.py`，可从候选输出和 QA issue 生成 translation review pack。
- 新增 `review pack` CLI，输出 `review.csv` 和 `review.jsonl`，包含源文、原目标文、候选译文、QA severity/code/message、risk 和定位字段。
- 新增 `review apply` CLI，只接收明确 approved 且有译文的行，写为 `reviewed` / `locked` state；支持 `--merge` 合并既有 state。
- `workflow run` 自动生成 `translation-review/`，并在 `summary.json` 中写入 `translation_review` 与 artifact 路径。
- `make smoke` 已接入 translation review pack、模拟 approved review 和 reviewed state schema 检查。

### 验证状态

- `make test`：通过，直接测试覆盖 QA issue 写入 review pack、approved CSV 回写 reviewed state。
- `python3 -m compileall -q limbus_translate`：通过。
- `make smoke`：通过，fixture 生成 `build/translation-review/review.csv`、`review.jsonl` 和 `build/reviewed-state.json`；workflow summary 包含 translation review artifact。
- 真实 Localize checkout：全量扫描 + `--limit 1` workflow 生成 1 条 translation review；模拟 approve 后回写 1 条 reviewed state。

### 风险

- review pack 解决的是审校载体和 state 回写，不代表 dry-run 候选可发布；正式译文仍需要 reviewer 填写或确认 `revised_target`。

## 2026-06-13 — Workflow run 术语增量闭环

### 已完成

- `workflow run` 默认对本次 `missing-units` 执行术语候选提取、rules refine 和 term review pack 导出。
- 工作目录新增 `term-candidates.json`、`refined-terms.json` 和 `term-review/`。
- `summary.json` 新增 `terms` 统计和 `term_candidates` / `refined_terms` / `term_review_*` artifact 路径。
- 新增 `--terms-provider`、`--terms-min-count`、`--terms-review-dir`、`--terms-include-not-term`、`--terms-min-confidence` 和 `--skip-terms` 参数。
- `make smoke` 已断言 workflow 术语 artifact 和 fixture 候选数量。

### 验证状态

- fixture workflow：通过，3 条候选、3 条 refined、1 条 review pack 记录。
- `make test`：通过。
- `python3 -m compileall -q limbus_translate`：通过。
- `make smoke`：通过，workflow summary 包含术语 artifact 和 `terms` 统计。
- `make validate-docs`：通过，36 个 Markdown 文件。
- `git diff --check`：通过。
- 真实 Localize checkout workflow：通过，全量扫描 19 条待译单元并用 `--limit 1` 控制翻译量，生成 19 条候选、19 条 refined、10 条 review pack 记录。

### 风险

- 默认 rules provider 只做离线粗筛，不会给出可靠译名；需要建议译名时应使用 `--terms-provider openai` 并继续走人工审校。

## 2026-06-13 — Workflow run 端到端更新链路

### 已完成

- 新增 `workflow run` CLI，一条命令串联 scan、TM 构建、可选 lore 导入/index、overlay 目标树、翻译写回、QA 和 summary。
- 工作目录会输出 `missing-units.json`、`tm.json`、可选 `lore.json` / `lore-index.json`、`qa-report.json` 和 `summary.json`。
- `summary.json` 记录待译单元数、实际写入数、缺译原因分布、QA 汇总和 artifact 路径。
- `make smoke` 已接入 fixture workflow，并校验 summary schema。
- README、operations、architecture、PRD、test plan、glossary 和 verification log 已补充 workflow 用法与验收口径。

### 验证状态

- fixture workflow：通过，2 条待译单元、2 条 dry-run 写入、2 条 `hangul_residue` warning，artifact 路径完整。
- `make test`：通过。
- `python3 -m compileall -q limbus_translate`：通过。
- `make smoke`：通过，生成 `build/workflow/summary.json` 并通过 schema 断言。
- `make validate-docs`：通过，36 个 Markdown 文件。
- `git diff --check`：通过。
- 真实 Localize checkout 小范围 workflow：通过，changed-files 指向 `KR/StoryData/3D102A.json`，输出 1 条 `target_same_as_source`、1 条 dry-run 写入、1 条 QA warning，artifact 路径完整。

### 风险

- `workflow run` 是工程串联入口，不替代人工审校；dry-run 输出的韩文残留 warning 是预期质量门禁。
- changed-files 仍是文件级过滤，不是 JSON path 级 diff；同文件内无关待译字段仍需 scan policy、QA 和人工审查兜底。

## 2026-06-13 — Changed-files 增量扫描

### 已完成

- `scan` 新增 `--changed-files` 参数，可读取 `git diff --name-only` 生成的换行文件清单。
- 新增 `read_changed_files` / `normalize_changed_file`，支持 `KR/Foo.json`、`LLC_zh-CN/Foo.json` 和 `Foo.json` 归一化为同一相对路径，并忽略非 JSON 文件。
- `scan_missing` 新增 `include_files` 过滤，只扫描本次变更涉及的 JSON 文件。
- `make smoke` 已用 `build/changed-files.txt` 走增量扫描路径。

### 验证状态

- `make test`：通过，直接单元测试覆盖只扫描变更文件、仓库路径归一化和非 JSON 跳过。
- `python3 -m compileall -q limbus_translate`：通过。
- `make smoke`：通过，fixture changed-files 清单包含 `KR/Sample.json` 和 `README.md`，扫描仍输出 2 条待译单元。
- `git diff --check`：通过。
- 真实 Localize checkout：全量扫描 19 条；changed-files 指向 `KR/StoryData/3D102A.json` 时只输出该文件 1 条，unit_id 与全量扫描子集一致。

### 风险

- 当前按文件过滤，不按 commit diff 中具体 JSON path 过滤；同一 JSON 文件内仍需要 scan policy、QA 和人工审查兜底。

## 2026-06-13 — Lore 离线向量索引

### 已完成

- 新增 `LoreIndex` / `LoreVectorRecord`，用 deterministic hashed n-gram sparse vector 构建离线 lore 索引。
- 新增 `lore index` CLI，从 `LoreEntry[]` cache 生成 `world-index.json`。
- 新增 `lore search` CLI，可独立验证 index 对 query 的召回结果。
- `translate` 新增 `--lore-index`，提供索引时 provider context 优先使用 index 召回 lore。
- `make smoke` 已接入 lore import -> index -> search -> translate with lore index。

### 验证状态

- `make test`：通过，直接单元测试覆盖 index roundtrip/search，context 测试通过 `build_lore_index` 注入 lore。
- `python3 -m compileall -q limbus_translate`：通过。
- `git diff --check`：通过。
- `make smoke`：通过，生成 `build/lore-index.json`、`build/lore-search.json`，并用 `--lore-index` 执行 dry-run 翻译。
- docs lore 小样本：`lore import/index/search` 通过，2 条 lore entry，搜索 `"단테가 전투를 지휘한다"` 命中 `단테`。
- 真实 Localize checkout：scan 19 条、TM 92337 条，带 docs lore index dry-run translate limit 2 通过。

### 风险

- 当前是可离线验证的 hashed-vector 工程索引，不是外部 embedding 服务或专用向量数据库；检索质量仍需用 curated gold set 调参。

## 2026-06-13 — Scan policy 数据 adapter

### 已完成

- 新增 `ScanPolicy` / `ScanPolicyRule`，扫描可按 `include` / `exclude` 规则调整文件、JSON path、key 和 source 内容范围。
- `scan` 新增 `--scan-policy` 参数；不传时保持原有默认扫描行为。
- 新增 `config/scan-policy.sample.json`，把 StoryData 内容保留、无用 desc、内部 name 和 BattleSpeechBubbleDlg 元数据过滤沉淀为配置。
- `make smoke` 已使用 sample policy 执行 fixture 扫描。

### 验证状态

- `make test`：通过，直接单元测试覆盖非默认文本路径 include、噪声路径 exclude 和 risk 覆盖。
- `python3 -m compileall -q limbus_translate`：通过。
- `git diff --check`：通过。
- `make validate-docs`：通过，36 个 Markdown 文件。
- `make smoke`：通过，带 sample policy 的 fixture 扫描仍生成 2 条待译单元。
- 真实 Localize checkout：默认扫描与 `--scan-policy config/scan-policy.sample.json` 均输出 19 条 `target_same_as_source`，且 `unit_id` 顺序一致。

### 风险

- sample policy 只是把当前观察到的噪声规则配置化；更多文件类型仍需要结合真实 diff 和人工抽查继续补规则。

## 2026-06-13 — Gold set 人工审校回写

### 已完成

- 新增 `eval review-pack` CLI，可把 gold/sample gold 导出为 `review.csv` 和 `review.jsonl`。
- 新增 `eval apply-review` CLI，读取审校后的 CSV，只导入 `approved` 明确为真的行，支持用 `revised_expected_text` 修订参考译文。
- `apply-review` 依赖原始 gold 文件做 case_id 匹配，回写 curated gold 时保留原始 glossary、context、tags 和 source_text。
- `make smoke` 已接入 gold sample -> review pack -> simulated approved review -> curated gold 的链路。

### 验证状态

- `make test`：通过，直接单元测试覆盖 review pack 字段、JSONL 结构、approved 判定、修订 expected_text 和保留结构化 gold case。
- `python3 -m compileall -q limbus_translate`：通过。
- `git diff --check`：通过。
- `make validate-docs`：通过，36 个 Markdown 文件。
- `make smoke`：通过，生成 `build/gold-review/review.csv`、`build/gold-review/review.jsonl` 和 1 条 `build/gold-curated.json`。
- 真实 Localize checkout 小样本：`eval build-gold --limit 50` 生成 50 条；`eval sample-gold --per-group 3 --group-by tag --seed 11` 生成 9 条；`eval review-pack` 生成 9 条审校包；模拟确认 1 条后 `eval apply-review` 生成 curated gold，保留 context/tags。

### 风险

- 这解决了 curated gold 的工程闭环，但真实模型赛马仍需要人工实际审校样本，而不是使用 smoke 里的模拟确认。

## 2026-06-13 — Gold set 分层采样

### 已完成

- 新增 `eval sample-gold` CLI，可从已有 gold set 按 `tag`、`risk` 或 `file` 分层采样。
- 支持 `--per-group`、`--limit` 和固定 `--seed`，便于构建可重复的模型赛马样本。
- `make smoke` 已接入 full gold set -> sampled gold set -> eval compare 的链路。

### 验证状态

- `make test`：通过，直接单元测试覆盖按 tag/risk 分层采样和固定 seed 可重复性。
- `python3 -m compileall -q limbus_translate`：通过。
- `git diff --check`：通过。
- `make validate-docs`：通过，36 个 Markdown 文件。
- `make smoke`：通过，生成 `build/gold-sample.json` 并用它执行 `eval compare`。
- 真实 Localize checkout 小样本：`eval build-gold --limit 100` 生成 100 条；`eval sample-gold --per-group 5 --group-by tag --seed 7` 生成 15 条 sampled gold。

### 风险

- 当前是工程化分层采样，不等于人工精选 gold set；正式模型赛马仍需要人工抽查样本质量和覆盖范围。

## 2026-06-13 — Gold set 多 provider 对比评估

### 已完成

- 新增 `eval compare` CLI，可在同一 gold set 上评估多个 provider/model。
- provider spec 支持 `dry-run`、`openai` 和 `openai:<model>`；`eval compare` 支持 `label=spec`，便于记录模型名称。
- 新增 compare report，包含每个 provider 的完整 eval result，以及按 pass rate / avg similarity 排序的 ranking。
- `translate --provider` 和 `eval run --provider` 放宽为 provider spec，支持后续直接指定 OpenAI 模型。

### 验证状态

- `make test`：通过，直接单元测试覆盖好/坏 provider ranking 和 compare report 写盘。
- `python3 -m compileall -q limbus_translate`：通过。
- `git diff --check`：通过。
- `make smoke`：通过，生成 `build/eval-compare-report.json`，包含 `baseline` 和 `candidate` 两个 dry-run provider。
- 真实 Localize checkout 小样本：`eval build-gold --limit 20` 生成 20 条；`eval compare` 对两个 dry-run label 生成完整 ranking。

### 风险

- 当前只验证了 dry-run provider 的 compare 链路；真实 OpenAI 多模型赛马还需要 API key、人工精选 gold set 和成本控制。

## 2026-06-13 — 审校术语回写本地缓存

### 已完成

- 新增 `terms apply-review` CLI，读取人工审校后的 `review.csv` 并写出本地 reviewed glossary cache。
- 只有 `approved` 明确为真且 `target` 非空的行会导入；未确认、空译名和留空候选会跳过。
- `make smoke` 会模拟一条人工确认行，验证 `build/local-reviewed-glossary.json` schema。

### 验证状态

- `make test`：通过，直接单元测试覆盖 approved 判定、空译名跳过和未确认行跳过。
- `python3 -m compileall -q limbus_translate`：通过。
- `git diff --check`：通过。
- `make validate-docs`：通过，36 个 Markdown 文件。
- `make smoke`：通过，模拟 1 条审校确认后生成 `build/local-reviewed-glossary.json`。
- 真实 Localize checkout 小样本：扫描 19 条，review pack 10 条；模拟确认 `찰-칵 -> 喀嚓` 后，`terms apply-review` 生成 1 条 reviewed glossary。

### 风险

- 当前回写目标仍是本地 glossary cache，不直接调用 Paratranz 写 API；平台正式 termbase 仍需要后续导入或 API 写入能力。

## 2026-06-13 — 术语审校与 Paratranz 候选导出包

### 已完成

- 新增 `terms review-pack` CLI，从 refined term cache 生成 `review.csv`、`review.jsonl` 和 `paratranz-import.csv`。
- `review.csv` 面向人工审校，保留空白 `approved` 列；`review.jsonl` 保留完整结构化证据。
- `paratranz-import.csv` 只导出 `decision=term` 且已有 `suggested_target` 的候选，避免 `needs_review` 或空译名污染正式术语库。
- `make test` 和 `make smoke` 已接入 review pack schema 检查。

### 验证状态

- `make test`：通过，直接单元测试覆盖 review pack CSV、JSONL 和 Paratranz 候选 CSV。
- `python3 -m compileall -q limbus_translate`：通过。
- `git diff --check`：通过。
- `make validate-docs`：通过，36 个 Markdown 文件。
- `make smoke`：通过，fixture review pack 生成 1 条审校候选。
- 真实 Localize checkout 小样本：扫描 19 条，术语候选 19 条，rules refine 输出 `needs_review=10`、`not_term=9`，review pack 生成 10 条审校候选，Paratranz 候选导入 CSV 为 0 条。

### 风险

- 当前仍不直接调用 Paratranz 写 API；`paratranz-import.csv` 是候选导入材料，需要人工确认后再进入正式 termbase。rules provider 不生成建议译名，因此真实 rules 小样本的 Paratranz 候选为 0 条是预期结果。

## 2026-06-13 — QA 估算显示宽度策略

### 已完成

- `LengthPolicy` 新增 `max_display_width`，QA 会按 East Asian Width 估算可见文本宽度，并忽略富文本标签。
- 新增 `line_display_too_wide` MQM design 类 issue，和既有字符级 `line_too_long` 并行。
- `config/length-policy.sample.json` 增加默认、剧情正文和短名称的显示宽度阈值。
- `make test` 直接入口覆盖 display width 策略测试。

### 验证状态

- `make test`：通过，直接单元测试包含 `test_qa_uses_display_width_policy`。
- `python3 -m compileall -q limbus_translate`：通过。
- `git diff --check`：通过。
- `make validate-docs`：通过，36 个 Markdown 文件。
- `make smoke`：通过，fixture QA 可读取 `config/length-policy.sample.json`。
- 真实 Localize checkout 小样本：扫描 19 条 `target_same_as_source`，TM 构建 92337 条，dry-run translate limit 3 通过，QA 生成 19 条 accuracy issue。

### 风险

- 当前显示宽度是 East Asian Width 估算，不是按游戏字体、字号和 UI 容器做像素测量；真实样本本轮未触发 `line_display_too_wide`，但 fixture 已覆盖触发路径。

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
  - `eval build-gold` / `eval run`：从参考译文构建 gold set，并调用 provider 输出相似度、格式一致性、术语缺失和 pass rate 报告。
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
- 世界观资料缓存：`tests.test_lore` 验证 Markdown / JSON 导入、cache roundtrip、anchors 召回、无 anchor 命中时的 TF-IDF n-gram 相似召回，以及离线 lore index roundtrip/search；`make smoke` 验证 `lore import`、`lore index/search` 和 `translate --lore-index build/lore-index.json` 链路。
- Gold set 评估：`tests.test_evaluation` 验证从 reference tree 构建 gold set、匹配 provider 全通过、错误 provider 报 similarity / format / terminology 问题、report 可落盘；`make smoke` 生成 `build/gold-set.json` 和 `build/eval-report.json`；真实 Localize checkout `eval build-gold --limit 1000` 通过，生成 1000 条，dry-run eval 1000 条报告落盘。
- QA 简繁、长度风险、路径/risk 字符级 length policy 和 MQM category/summary：fixture 测试通过；真实 dry-run QA 小样本输出 19 条 accuracy 类 issue，报告字段落盘正常；`make smoke` 已验证 `qa --length-policy config/length-policy.sample.json` 可读。
- `python3 -m pytest -q` 未运行成功，因为系统 Python 没有安装 `pytest`；已用无依赖直接测试替代。

### 风险

- 当前扫描支持唯一、非 `-1` 的 `dataList[*].id` 主键对齐；重复 id 或 `id=-1` 会回退 JSON path，避免 StoryData 误对齐。
- 当前 QA 已覆盖韩文残留、占位符、标签、数字、换行、术语命中、疑似繁体、路径/risk 字符级 length policy、估算显示宽度和 MQM 风格分类，但还没有像素级 UI 容器测量。
- 当前 lore cache 已支持 anchors、术语、轻量 TF-IDF n-gram 和离线 hashed-vector index 召回；真实世界观资料仍需整理为本地笔记或外部知识源导入，外部 embedding 服务/专用向量库和 gold set 调参还未完成。
- 当前可从真实 reference tree 自动抽取 1000 条 gold set，但还没有人工精选、分层采样后的模型赛马基准。
- 当前术语候选提取和 rules refiner 只是自动粗筛；OpenAI provider 也只能给建议译名，正式术语仍需人工确认后通过 `terms promote` 进入 termbase。
- Chrome 插件连接 Paratranz 页面失败，但子任务已通过公开 API 证明术语可读；若要用 Chrome，需要用户允许打开 Chrome 窗口刷新扩展连接。

### 下一步

- 补像素级 UI 容器测量和具体容器策略。
- 把本地 promoted glossary 与 Paratranz 或审校系统的正式 termbase 同步，并把 lore index 升级到外部 embedding 服务或专用向量库，再用 curated gold set 调参。
- 用 `eval build-gold --limit 1000` 生成真实候选 gold set，人工分层抽查后用 `eval run --provider openai --fail-under ...` 做模型赛马和 prompt 回归。

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
