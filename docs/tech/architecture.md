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
    -> memory.py: exact translation memory
    -> state.py: reviewed / locked unit state
    -> providers.py: dry-run / OpenAI provider
    -> translator.py: overlay existing target tree and set translated JSON paths
    -> qa.py: placeholders, tags, numbers, line breaks, glossary checks
    -> terms.py: candidate term cache for LLM/human review
    -> build/LLC_zh-CN/**/*.json
```

## 目录职责

| 路径 | 职责 |
|---|---|
| `limbus_translate/json_paths.py` | JSON 文本节点遍历、可翻译路径判断、路径读写 |
| `limbus_translate/scanner.py` | 生成待翻译单元；支持唯一、非 `-1` 的 `dataList[*].id` 稳定对齐，重复/无效 id 回退 JSON path |
| `limbus_translate/glossary.py` | Paratranz 术语同步、离线导入、本地缓存、术语匹配 |
| `limbus_translate/memory.py` | 从已翻译文件构建 exact-match 翻译记忆 |
| `limbus_translate/state.py` | 维护 `new` / `reviewed` / `locked` 单元状态，翻译时跳过锁定单元 |
| `limbus_translate/providers.py` | 翻译 provider 抽象，默认 dry-run，OpenAI 为 GPT 兜底 |
| `limbus_translate/translator.py` | 把候选译文写回同结构 JSON 输出树；对 `missing_target_record` 会复制源 record 到目标 `dataList` 后替换待译字段 |
| `limbus_translate/qa.py` | 检查韩文残留、占位符、标签、数字、换行和术语命中 |
| `limbus_translate/terms.py` | 从新增文本提取待确认术语/短语候选，排除已知 Paratranz 术语 |
| `limbus_translate/cli.py` | 命令行入口 |
| `tests/fixtures/` | 最小 Localize JSON 测试夹具 |
| `docs/research/` | 模型、流程、外部来源调研 |

## 数据流

1. `scan` 读取 `KR` 与 `LLC_zh-CN`，输出 `TranslationUnit[]`，包含 `source_json_path`、目标 `json_path`、`stable_key`、source hash 和格式 profile。
2. `glossary sync-paratranz` 缓存 Paratranz 项目 `6860` 的术语。
3. `tm build` 从已翻译 JSON 构建 exact-match 翻译记忆。
4. `translate` 读取待译单元、术语缓存和 TM，按目标 JSON path 写入输出目录；目标缺 `dataList` record 时会 append 源 record 并替换本字段译文。
5. `state init` 或外部审校系统维护 `reviewed` / `locked` 状态，`translate --state` 避免覆盖人工定稿。
6. `qa` 检查占位符、标签、术语、数字、换行、韩文残留、疑似繁体和长度风险。
7. `terms extract` 从新增文本提取候选词/短语，进入 LLM 或人工二次筛选。
8. 审校通过后，译文进入目标语言包、TM 和回归评估集。

## 设计原则

| 原则 | 含义 |
|---|---|
| 语义 diff 优先 | 不做文本行 diff；以 JSON path、唯一记录 id、字段类型和 source hash 为核心 |
| 格式不破坏 | 保留 JSON 结构、占位符、标签、换行和目标文件路径 |
| 术语先行 | 翻译前注入 Paratranz / 本地术语，翻译后做术语命中 QA |
| Provider 可替换 | 不把扫描、术语、写回逻辑绑定到某个模型供应商 |
| 可离线验证 | 没有 API key 时也能用 dry-run 测通扫描和输出 |
