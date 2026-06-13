# Architecture

本文档维护 Limbus Translate 当前技术架构和边界。

## 当前架构

Limbus Translate 当前是一个 Python CLI 工具，围绕 LocalizeLimbusCompany 的 JSON 语言包做增量扫描、术语同步和候选译文生成。

```text
LocalizeLimbusCompany checkout
  KR/**/*.json
  LLC_zh-CN/**/*.json
    -> scanner.py: semantic JSON path diff
    -> glossary.py: Paratranz / offline term cache
    -> lore.py: worldbuilding note cache
    -> memory.py: exact translation memory
    -> context.py: structured context bundle for provider prompts
    -> state.py: reviewed / locked unit state
    -> providers.py: dry-run / OpenAI provider
    -> evaluation.py: gold set provider regression
    -> translator.py: overlay existing target tree and set translated JSON paths
    -> qa.py: placeholders, tags, numbers, line breaks, glossary checks
    -> terms.py: candidate extraction, refiner providers, refined term cache
    -> build/LLC_zh-CN/**/*.json
```

## 目录职责

| 路径 | 职责 |
|---|---|
| `limbus_translate/json_paths.py` | JSON 文本节点遍历、可翻译路径判断、路径读写 |
| `limbus_translate/scanner.py` | 生成待翻译单元；支持唯一、非 `-1` 的 `dataList[*].id` 稳定对齐，重复/无效 id 回退 JSON path；支持 scan policy 按文件/path/key include 或 exclude |
| `limbus_translate/glossary.py` | Paratranz 术语同步、离线导入、本地缓存、术语匹配 |
| `limbus_translate/lore.py` | 从 Markdown / JSON / JSONL / CSV / TXT 导入世界观资料缓存，并按 anchors、术语和 TF-IDF 字符 n-gram 相似度召回 lore 片段 |
| `limbus_translate/memory.py` | 从已翻译文件构建 exact-match 翻译记忆 |
| `limbus_translate/context.py` | 为翻译 provider 组装结构化上下文包：位置、风险、术语、同文件邻近文本、同文件 TM、跨文件相似 TM 示例和 lore 片段 |
| `limbus_translate/evaluation.py` | 从参考译文构建 gold set；导出/导入人工审校 gold；调用 provider，输出相似度、格式一致性、术语命中和 pass rate 报告 |
| `limbus_translate/state.py` | 维护 `new` / `reviewed` / `locked` 单元状态，翻译时跳过锁定单元 |
| `limbus_translate/providers.py` | 翻译 provider 抽象，默认 dry-run，OpenAI 为 GPT 兜底；接收 `TranslationRequest.context` 结构化 JSON 上下文 |
| `limbus_translate/translator.py` | 把候选译文写回同结构 JSON 输出树；非 exact TM 命中时构建上下文包并传给 provider；对 `missing_target_record` 会复制源 record 到目标 `dataList` 后替换待译字段 |
| `limbus_translate/qa.py` | 检查韩文残留、占位符、标签、数字、换行、术语命中和 UI 长度风险；支持 JSON length policy；输出 MQM 风格 category 汇总 |
| `limbus_translate/terms.py` | 从新增文本提取待确认术语/短语候选，排除已知 Paratranz 术语；通过 `rules` / `openai` provider 输出 refined term cache；将已确认 refined term promote 为本地 glossary cache |
| `limbus_translate/cli.py` | 命令行入口 |
| `tests/fixtures/` | 最小 Localize JSON 测试夹具 |
| `docs/research/` | 模型、流程、外部来源调研 |

## 数据流

1. `scan` 读取 `KR` 与 `LLC_zh-CN`，可选读取 `--scan-policy` 作为文件类型 adapter 配置，输出 `TranslationUnit[]`，包含 `source_json_path`、目标 `json_path`、`stable_key`、source hash 和格式 profile。
2. `glossary sync-paratranz` 缓存 Paratranz 项目 `6860` 的术语。
3. `lore import` 把世界观笔记导成 `cache/lore/world.json`，供翻译时按源文、术语和 anchors 召回。
4. `tm build` 从已翻译 JSON 构建 exact-match 翻译记忆。
5. `translate` 读取待译单元、术语缓存、lore cache 和 TM，先查 state / exact TM；未命中时匹配术语并构建结构化 context bundle，再按目标 JSON path 写入输出目录；目标缺 `dataList` record 时会 append 源 record 并替换本字段译文。
6. `state init` 或外部审校系统维护 `reviewed` / `locked` 状态，`translate --state` 避免覆盖人工定稿。
7. `qa` 检查占位符、标签、术语、数字、换行、韩文残留、疑似繁体和长度风险，可通过 `--length-policy` 按路径或 risk 覆盖字符级阈值，并按 `accuracy` / `terminology` / `format` / `locale_convention` / `design` 等 MQM 风格类别汇总。
8. `eval build-gold` 从已有中译参考抽取回归样本，`eval sample-gold` 做分层抽样，`eval review-pack` / `eval apply-review` 把人工确认结果写成 curated gold；`eval run` 用 gold set 比较 provider 输出，生成 `build/eval-report.json`，用于模型赛马和 prompt 回归。
9. `terms extract` 从新增文本提取候选词/短语，`terms refine` 生成 `cache/terms/refined.json`，把候选分为 `term` / `not_term` / `needs_review`；`terms promote` 只把有确认译名的 `term` 写入本地 glossary cache。
10. 审校通过后，译文进入目标语言包、TM 和回归评估集。

`TranslationContextBundle` 当前字段为 `relative_file`、`json_path`、`source_json_path`、`stable_key`、`risk`、`terms`、`neighbors`、`memory_examples`、`lore`。其中 `neighbors` 来自同文件邻近可翻译 JSON 文本，`memory_examples` 包含同文件 TM 示例和基于 `SequenceMatcher` 的跨文件相似 TM 示例，`lore` 来自可维护的世界观资料缓存，并使用 anchors、术语和轻量 TF-IDF 字符 n-gram 相似度召回；这还不是 embedding 向量库或经过 gold set 调参的完整 RAG。

## 设计原则

| 原则 | 含义 |
|---|---|
| 语义 diff 优先 | 不做文本行 diff；以 JSON path、唯一记录 id、字段类型和 source hash 为核心 |
| Adapter 可配置 | 文件类型、路径和内部字段噪声先用 scan policy 沉淀，减少每次改代码才能调扫描范围 |
| 格式不破坏 | 保留 JSON 结构、占位符、标签、换行和目标文件路径 |
| 术语先行 | 翻译前注入 Paratranz / 本地术语，翻译后做术语命中 QA |
| 上下文显式化 | Provider 接收 JSON context，而不是隐式依赖单句 prompt |
| Provider 可替换 | 不把扫描、术语、写回逻辑绑定到某个模型供应商；术语提炼默认 `rules` 离线可跑，`openai` 可选 |
| 可离线验证 | 没有 API key 时也能用 dry-run 测通扫描和输出 |
