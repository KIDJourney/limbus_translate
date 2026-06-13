# Architecture

本文档维护 Limbus Translate 当前技术架构和边界。

## 当前架构

Limbus Translate 当前是一个 Python CLI 工具，围绕 LocalizeLimbusCompany 的 JSON 语言包做增量扫描、术语同步和候选译文生成。

```text
LocalizeLimbusCompany checkout
  KR/**/*.json
  LLC_zh-CN/**/*.json
    -> scanner.py: semantic JSON path diff
    -> glossary.py: Paratranz / offline term cache and glossary audit
    -> lore.py: worldbuilding note cache and offline vector index
    -> memory.py: exact translation memory
    -> context.py: structured context bundle for provider prompts
    -> translation_cache.py: provider candidate cache, request log and translation trace
    -> localize.py: update input preparation from git commits
    -> state.py: reviewed / locked unit state
    -> providers.py: dry-run / OpenAI provider
    -> evaluation.py: gold set provider regression
    -> translator.py: overlay existing target tree and set translated JSON paths
    -> qa.py: placeholders, tags, numbers, line breaks, glossary checks
    -> terms.py: candidate extraction, refiner providers, persistent refined term cache
    -> review.py: translation review pack and reviewed state apply
    -> cli.py workflow run: optional Localize update preparation -> scan -> TM -> glossary audit -> term cache/review pack -> lore index -> translate/cache/request log/trace -> QA -> translation review summary
    -> build/LLC_zh-CN/**/*.json
```

## 目录职责

| 路径 | 职责 |
|---|---|
| `limbus_translate/json_paths.py` | JSON 文本节点遍历、可翻译路径判断、路径读写 |
| `limbus_translate/scanner.py` | 生成待翻译单元；支持唯一、非 `-1` 的 `dataList[*].id` 稳定对齐，重复/无效 id 回退 JSON path；支持 scan policy、changed-files 文件级增量扫描和 source-baseline JSON path 级源文变化扫描 |
| `limbus_translate/glossary.py` | Paratranz 术语同步、离线导入、本地缓存、术语匹配和术语库质量审计 |
| `limbus_translate/lore.py` | 从 Markdown / JSON / JSONL / CSV / TXT 导入世界观资料缓存，构建离线 hashed-vector 索引，并按 anchors、术语、TF-IDF 字符 n-gram 或索引相似度召回 lore 片段 |
| `limbus_translate/localize.py` | 从 LocalizeLimbusCompany checkout 的两个 commit 生成 changed-files 清单和上一版 `KR` source baseline |
| `limbus_translate/memory.py` | 从已翻译文件构建 exact-match 翻译记忆，并用 curated gold set 评估 fuzzy TM 召回覆盖率和目标译文相似度 |
| `limbus_translate/context.py` | 为翻译 provider 组装结构化上下文包：位置、缺译原因、旧目标译文、风险、术语、同文件邻近文本、同文件 TM、跨文件相似 TM 示例和 lore 片段 |
| `limbus_translate/evaluation.py` | 从参考译文构建 gold set；导出/导入人工审校 gold；调用 provider，输出相似度、格式一致性、术语命中和 pass rate 报告 |
| `limbus_translate/state.py` | 维护 `new` / `reviewed` / `locked` 单元状态，翻译时跳过锁定单元 |
| `limbus_translate/providers.py` | 翻译 provider 抽象，默认 dry-run，OpenAI 为 GPT 兜底；接收 `TranslationRequest.context` 结构化 JSON 上下文 |
| `limbus_translate/translator.py` | 把候选译文写回同结构 JSON 输出树；非 exact TM 命中时构建上下文包并传给 provider；对 `missing_target_record` 会复制源 record 到目标 `dataList` 后替换待译字段 |
| `limbus_translate/translation_cache.py` | 缓存 provider 候选译文，按 provider、source hash、context hash 和 glossary hash 生成 key；输出 provider request log、usage summary 和逐条 translation trace |
| `limbus_translate/qa.py` | 检查韩文残留、占位符、标签、数字、换行、术语命中和 UI 长度风险；支持 JSON length policy；输出 MQM 风格 category 汇总 |
| `limbus_translate/terms.py` | 从新增文本提取待确认术语/短语候选，排除已知 Paratranz 术语；通过 `rules` / `openai` provider 输出本轮 refined 结果，并可复用/更新持久 refined term cache；将已确认 refined term promote 为本地 glossary cache |
| `limbus_translate/review.py` | 从候选输出和 QA 报告导出翻译审校包，并把审校通过的译文回写为 reviewed / locked state |
| `limbus_translate/cli.py` | 命令行入口；`workflow run` 串联扫描、TM、术语候选/审校包、lore index、翻译输出、QA、翻译审校包和 summary |
| `tests/fixtures/` | 最小 Localize JSON 测试夹具 |
| `docs/research/` | 模型、流程、外部来源调研 |

## 数据流

1. `localize prepare-update` 可先从 LocalizeLimbusCompany checkout 的 `base..head` 生成 `changed-files.txt` 和上一版 `source-baseline/KR`；`workflow run --localize-repo` 也可以在工作目录内自动执行这一步。
2. `scan` 读取 `KR` 与 `LLC_zh-CN`，可选读取 `--scan-policy` 作为文件类型 adapter 配置，也可读取 `--changed-files` 把范围收敛到本次 git diff 涉及的 JSON 文件；如果传入 `--source-baseline`，会按 JSON path 和 `dataList[id=...]` 稳定键只保留源文新增/变化的路径，并把目标已有旧中文的单元标记为 `source_changed`。输出 `TranslationUnit[]`，包含 `source_json_path`、目标 `json_path`、`stable_key`、source hash 和格式 profile。
3. `glossary sync-paratranz` 缓存 Paratranz 项目 `6860` 的术语；`glossary audit` 检查空源文、空译名、同源多译名冲突、译文韩文残留和重复项。
4. `lore import` 把世界观笔记导成 `cache/lore/world.json`；`lore index` 进一步构建 `cache/lore/world-index.json`，供翻译时按源文、术语、anchors 和离线向量相似度召回。
5. `tm build` 从已翻译 JSON 构建 exact-match 翻译记忆；`tm evaluate` 用 curated gold set 评估 fuzzy TM top-k 召回、覆盖率、源文相似度、目标译文相似度和阈值 sweep。
6. `translate` 读取待译单元、术语缓存、lore cache、TM 和可选 candidate cache，先查 state / exact TM；未命中时匹配术语并构建结构化 context bundle，按 provider、source hash、context hash 和 glossary hash 查候选缓存；仍未命中才调用 provider，并可把本次发送给 provider 的 source、glossary、context、返回译文、响应模型/id 和 token usage 写入 request log，再按目标 JSON path 写入输出目录；目标缺 `dataList` record 时会 append 源 record 并替换本字段译文。开启 trace 时，每条处理结果都会记录译文来源。
7. `state init` 或外部审校系统维护 `reviewed` / `locked` 状态，`translate --state` 避免覆盖人工定稿。
8. `qa` 检查占位符、标签、术语、数字、换行、韩文残留、疑似繁体和长度风险，可通过 `--length-policy` 按路径或 risk 覆盖字符级阈值，并按 `accuracy` / `terminology` / `format` / `locale_convention` / `design` 等 MQM 风格类别汇总。
9. `eval build-gold` 从已有中译参考抽取回归样本，`eval sample-gold` 做分层抽样，`eval review-pack` / `eval apply-review` 把人工确认结果写成 curated gold；`eval run` 用 gold set 比较 provider 输出，生成 `build/eval-report.json`，并在启用 request log 时把 usage 聚合进 summary，用于模型赛马、成本复盘和 prompt 回归。
10. `terms extract` 从新增文本提取候选词/短语，`terms refine` 生成 `cache/terms/refined.json`，把候选分为 `term` / `not_term` / `needs_review`；传入 `--cache` 时会按规范化 source 复用历史 refined 结果，只把未命中候选交给 refiner，并把合并结果写回持久 cache；`terms promote` 只把有确认译名的 `term` 写入本地 glossary cache。
11. `review pack` 把候选译文、源文、原目标文本、QA severity/code/message 导出为人工审校 CSV/JSONL；`review apply` 把明确 approved 的行回写为 `reviewed` 或 `locked` state。
12. `workflow run` 把可选 Localize commit 输入准备、scan、TM 构建、可选 source-baseline 源文 path diff、可选 glossary audit、术语候选提取/refine/cache/review pack、可选 lore 导入/索引、translate、candidate cache、provider request log、usage summary、translation trace、QA 和 translation review pack 串成一次可复现更新，输出工作目录内的 `localize-update/`、`missing-units.json`、`tm.json`、可选 `glossary-audit.json`、`translation-candidates.json`、`translation-requests.jsonl`、`translation-trace.jsonl`、`term-candidates.json`、`refined-terms.json`、`term-review/`、可选 refined term cache、可选 lore cache/index、`qa-report.json`、`translation-review/` 和 `summary.json`。
13. 审校通过后，译文进入目标语言包、TM 和回归评估集。

`TranslationContextBundle` 当前字段为 `relative_file`、`json_path`、`source_json_path`、`stable_key`、`reason`、`risk`、`previous_target_text`、`terms`、`neighbors`、`memory_examples`、`lore`。其中 `previous_target_text` 只在 `source_changed` 且旧目标译文是中文时填充，用于让 provider 修订旧译文；`neighbors` 来自同文件邻近可翻译 JSON 文本，`memory_examples` 包含同文件 TM 示例和基于 `SequenceMatcher` 的跨文件相似 TM 示例，`lore` 来自可维护的世界观资料缓存。未提供 index 时使用 anchors、术语和轻量 TF-IDF 字符 n-gram 相似度召回；提供 `--lore-index` 时使用离线 hashed-vector index 召回。当前还不是外部 embedding 服务或经过 gold set 调参的完整 RAG。

## 设计原则

| 原则 | 含义 |
|---|---|
| 语义 diff 优先 | 不做文本行 diff；以 JSON path、唯一记录 id、字段类型和 source hash 为核心 |
| Adapter 可配置 | 文件类型、路径和内部字段噪声先用 scan policy 沉淀，减少每次改代码才能调扫描范围 |
| 格式不破坏 | 保留 JSON 结构、占位符、标签、换行和目标文件路径 |
| 术语先行 | 翻译前注入 Paratranz / 本地术语，术语提炼跨更新缓存，翻译后做术语命中 QA |
| 上下文显式化 | Provider 接收 JSON context，而不是隐式依赖单句 prompt |
| 候选可追溯 | 模型译文要记录 cache key、context hash、provider 入参、响应 metadata、usage 和来源，避免重复调用和无法复盘 |
| Provider 可替换 | 不把扫描、术语、写回逻辑绑定到某个模型供应商；术语提炼默认 `rules` 离线可跑，`openai` 可选 |
| 可离线验证 | 没有 API key 时也能用 dry-run 测通扫描和输出 |
