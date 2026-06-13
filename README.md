# Limbus Translate

Limbus Translate 是一个面向《Limbus Company》韩文到简体中文本地化的自动化翻译工具。目标是从 `KR/**.json` 原始资源中发现新增或变化文本，结合 Paratranz 术语库、翻译记忆和世界观上下文生成候选译文，再通过自动 QA 与人工审校回写为 `LLC_zh-CN/**.json` 同结构产物。

当前版本先落地可验证的核心骨架：

- JSON 语义扫描：按相对路径和 JSON path 找出目标为空、目标缺失、目标等于韩文源文的候选缺译单元，并可用 scan policy 配置文件按文件类型纳入或排除路径。
- Paratranz 术语同步：匿名分页读取项目 `6860` 的术语 API，缓存为本地统一模型。
- 离线术语导入：支持 CSV / JSON 兜底。
- 术语库审计：检查空源文、空译名、同源多译名冲突、译文韩文残留和重复项，并在 workflow summary 中暴露结果。
- 世界观资料缓存：支持从 Markdown / JSON / JSONL / CSV / TXT 导入 lore cache，并通过 anchors、术语、轻量 TF-IDF n-gram 和离线 hashed-vector 索引召回相关设定片段。
- 可插拔翻译 provider：默认 `dry-run` 可测试，`openai` provider 作为 GPT 兜底入口。
- 结构化翻译上下文：翻译请求会注入位置、风险、命中术语、同文件邻近文本、同文件 TM、相似 TM 示例和世界观片段。
- 候选译文缓存与 trace：provider 产物按 provider、source hash、context hash 和 glossary hash 缓存；每条译文记录 provenance，区分 state、TM、cache 和 provider。
- 同结构输出：从现有中文文件叠加候选译文，缺目标文件时沿用韩文结构生成输出。
- 审校状态：支持 `reviewed` / `locked` 状态，避免自动覆盖人工定稿。
- 自动 QA：检查韩文残留、占位符、标签、数字、换行、术语命中、疑似繁体、字符长度和估算显示宽度风险，并按 MQM 风格类别汇总。
- 翻译审校包：可从候选输出和 QA 报告导出 `review.csv` / `review.jsonl`，人工确认后回写为 reviewed state。
- 术语候选二次提炼：`terms extract` 召回候选后，`terms refine` 用 `rules` 或 `openai` provider 输出 refined cache，并可导出 review pack 供人工审校，审校通过后写入本地 glossary cache。
- Gold set 评估：`eval build-gold` 可从已有中译参考构建样本，支持分层抽样、人工审校回写，`eval run` / `eval compare` 可比较 provider 输出并报告相似度、格式问题、术语缺失和模型排名。

## 快速开始

```bash
make validate-docs
make test
make smoke
make sync-glossary
```

对真实 LocalizeLimbusCompany checkout 运行扫描：

```bash
git -C /path/to/LocalizeLimbusCompany diff --name-only HEAD~1 HEAD > build/changed-files.txt
mkdir -p build/source-baseline
git -C /path/to/LocalizeLimbusCompany archive HEAD~1 KR | tar -x -C build/source-baseline

python3 -m limbus_translate.cli scan \
  --source /path/to/LocalizeLimbusCompany/KR \
  --target /path/to/LocalizeLimbusCompany/LLC_zh-CN \
  --output build/missing-units.json \
  --scan-policy config/scan-policy.sample.json \
  --changed-files build/changed-files.txt \
  --source-baseline build/source-baseline/KR
```

`--scan-policy` 接受 JSON 规则文件，支持按 `relative_file`、`relative_file_prefix`、`json_path`、`json_path_suffix`、`key` 和 `source_contains` 做 `include` / `exclude`。这用于把特定文件里的可见文本路径纳入扫描，也用于过滤内部事件名、显示占位和无用文本等噪声；不传该参数时仍使用内置默认规则。

`--changed-files` 接受 `git diff --name-only` 这类换行分隔清单，只扫描清单中涉及的 JSON 相对文件；`KR/Foo.json`、`LLC_zh-CN/Foo.json` 和 `Foo.json` 都会归一化为同一个相对路径，非 JSON 行会被忽略。不传该参数时执行全量扫描。

`--source-baseline` 接受上一个版本的 `KR` 目录，用于 JSON path 级源文 diff。传入后，扫描只处理当前源文中相对 baseline 新增或变化的文本；如果目标里已有旧中文，也会以 `source_changed` 原因重新进入待译列表。

一键执行本次更新链路：

```bash
python3 -m limbus_translate.cli workflow run \
  --source /path/to/LocalizeLimbusCompany/KR \
  --target /path/to/LocalizeLimbusCompany/LLC_zh-CN \
  --output build/LLC_zh-CN \
  --work-dir build/workflow \
  --scan-policy config/scan-policy.sample.json \
  --changed-files build/changed-files.txt \
  --source-baseline build/source-baseline/KR \
  --glossary cache/glossary/paratranz-6860.json \
  --lore-input docs/lore \
  --length-policy config/length-policy.sample.json \
  --provider dry-run
```

`workflow run` 会串联 scan、TM 构建、可选 glossary audit、可选 lore 导入/索引、同结构翻译输出、QA 和翻译审校包，工作目录中会写出 `missing-units.json`、`tm.json`、可选 `glossary-audit.json`、`translation-candidates.json`、`translation-trace.jsonl`、可选 `lore.json` / `lore-index.json`、`qa-report.json`、`translation-review/` 和 `summary.json`。`summary.json` 记录待译单元数、实际写入数、缺译原因分布、术语库审计、候选缓存统计、trace 行数、QA 汇总和所有产物路径，适合作为一次上游更新的交接入口。

默认情况下，`workflow run` 还会对本次新增文本执行术语候选提取和 rules 二次提炼，输出 `term-candidates.json`、`refined-terms.json` 和 `term-review/` 审校包；需要 LLM 给建议译名时可传 `--terms-provider openai`，需要只跑翻译链路时可传 `--skip-terms`。

生成候选译文：

```bash
python3 -m limbus_translate.cli translate \
  --source /path/to/LocalizeLimbusCompany/KR \
  --target /path/to/LocalizeLimbusCompany/LLC_zh-CN \
  --units build/missing-units.json \
  --glossary cache/glossary/paratranz-6860.json \
  --memory cache/tm/exact.json \
  --lore cache/lore/world.json \
  --lore-index cache/lore/world-index.json \
  --state cache/state/units.json \
  --candidate-cache cache/translation/candidates.json \
  --trace build/translation-trace.jsonl \
  --output build/LLC_zh-CN \
  --provider dry-run
```

`--glossary`、`--memory`、`--lore` 和 `--lore-index` 会参与 provider 的结构化上下文包：state 和 exact TM 命中会直接复用译文；未命中时，命中术语、同文件邻近文本、同文件 TM、跨文件相似 TM 示例和 lore 片段会进入 `TranslationRequest.context`。`source_changed` 单元会把旧中文写入 `previous_target_text`，让模型基于旧译文修订而不是从零翻译。`--candidate-cache` 会读取并更新 provider 候选缓存，缓存 key 绑定 provider、source hash、context hash 和 glossary hash；`--trace` 会输出 JSONL，记录每条译文来自 state、TM、candidate cache 还是 provider。同时提供 `--lore` 与 `--lore-index` 时，翻译上下文优先使用索引召回。

构建翻译记忆和 QA 报告：

```bash
python3 -m limbus_translate.cli tm build \
  --source /path/to/LocalizeLimbusCompany/KR \
  --target /path/to/LocalizeLimbusCompany/LLC_zh-CN \
  --output cache/tm/exact.json

python3 -m limbus_translate.cli glossary audit \
  --input cache/glossary/paratranz-6860.json \
  --report build/glossary-audit.json \
  --fail-on error

python3 -m limbus_translate.cli state init \
  --units build/missing-units.json \
  --output cache/state/units.json

python3 -m limbus_translate.cli lore import \
  --input docs/lore \
  --output cache/lore/world.json

python3 -m limbus_translate.cli lore index \
  --lore cache/lore/world.json \
  --output cache/lore/world-index.json

python3 -m limbus_translate.cli lore search \
  --index cache/lore/world-index.json \
  --query "단테가 전투를 지휘한다" \
  --output build/lore-search.json

python3 -m limbus_translate.cli qa \
  --units build/missing-units.json \
  --output-root build/LLC_zh-CN \
  --glossary cache/glossary/paratranz-6860.json \
  --report build/qa-report.json \
  --length-policy config/length-policy.sample.json

python3 -m limbus_translate.cli review pack \
  --units build/missing-units.json \
  --output-root build/LLC_zh-CN \
  --qa-report build/qa-report.json \
  --output-dir build/translation-review

python3 -m limbus_translate.cli review apply \
  --review build/translation-review/review.csv \
  --output cache/state/reviewed.json \
  --merge cache/state/units.json

python3 -m limbus_translate.cli eval build-gold \
  --source /path/to/LocalizeLimbusCompany/KR \
  --target /path/to/LocalizeLimbusCompany/LLC_zh-CN \
  --glossary cache/glossary/paratranz-6860.json \
  --output cache/eval/gold-set.json \
  --limit 1000

python3 -m limbus_translate.cli eval sample-gold \
  --gold cache/eval/gold-set.json \
  --output cache/eval/gold-sample.json \
  --per-group 20 \
  --group-by tag \
  --seed 7

python3 -m limbus_translate.cli eval review-pack \
  --gold cache/eval/gold-sample.json \
  --output-dir build/gold-review

python3 -m limbus_translate.cli eval apply-review \
  --gold cache/eval/gold-sample.json \
  --review build/gold-review/review.csv \
  --output cache/eval/gold-curated.json

python3 -m limbus_translate.cli eval run \
  --gold cache/eval/gold-curated.json \
  --provider dry-run \
  --report build/eval-report.json

python3 -m limbus_translate.cli eval compare \
  --gold cache/eval/gold-curated.json \
  --provider baseline=dry-run \
  --provider gpt41=openai:gpt-4.1 \
  --report build/eval-compare-report.json

python3 -m limbus_translate.cli terms extract \
  --units build/missing-units.json \
  --glossary cache/glossary/paratranz-6860.json \
  --output cache/terms/candidates.json

python3 -m limbus_translate.cli terms refine \
  --candidates cache/terms/candidates.json \
  --output cache/terms/refined.json \
  --provider rules

python3 -m limbus_translate.cli terms review-pack \
  --refined cache/terms/refined.json \
  --output-dir build/term-review

python3 -m limbus_translate.cli terms apply-review \
  --review build/term-review/review.csv \
  --output cache/glossary/local-reviewed.json \
  --merge cache/glossary/paratranz-6860.json

python3 -m limbus_translate.cli terms promote \
  --refined cache/terms/refined.json \
  --output cache/glossary/local-refined.json \
  --merge cache/glossary/paratranz-6860.json
```

`refined.json` 中的 `decision` 为 `term` / `not_term` / `needs_review`，并保留 `suggested_target`、`confidence`、`note`、`contexts`、`provider` 等字段。`terms review-pack` 会输出 `review.csv`、`review.jsonl` 和 `paratranz-import.csv`，默认排除 `not_term`；`terms apply-review` 只会导入 `approved` 明确为真且 `target` 非空的审校行；`terms promote` 只会导出 `decision=term` 且有 `suggested_target` 的记录。

`eval sample-gold` 可按 `tag` / `risk` / `file` 分层抽样，避免评估集过度偏向单一文本类型；`eval review-pack` 会导出 `review.csv` 和 `review.jsonl` 供人工确认，`eval apply-review` 只把 `approved` 明确为真且能匹配原始 gold case 的行写回 curated gold set，并保留原始 glossary / context / tags。`--provider` 支持 `dry-run`、`openai` 和 `openai:<model>`；`eval compare` 的 provider 可写成 `label=spec`，用于在同一 gold set 上比较多个模型。

使用 OpenAI provider 前需要安装可选依赖并设置 API key：

```bash
python3 -m pip install '.[openai]'
OPENAI_TRANSLATION_MODEL=gpt-4.1 python3 -m limbus_translate.cli translate ...
OPENAI_TERM_MODEL=gpt-4.1 python3 -m limbus_translate.cli terms refine --provider openai ...
```

## 目录

```text
.
├── AGENTS.md
├── README.md
├── Makefile
├── config
│   ├── length-policy.sample.json
│   └── scan-policy.sample.json
├── limbus_translate
│   ├── cli.py
│   ├── context.py
│   ├── evaluation.py
│   ├── glossary.py
│   ├── lore.py
│   ├── json_paths.py
│   ├── memory.py
│   ├── providers.py
│   ├── qa.py
│   ├── review.py
│   ├── scanner.py
│   ├── state.py
│   ├── terms.py
│   ├── translation_cache.py
│   └── translator.py
├── tests
│   └── fixtures
├── docs
│   ├── product
│   ├── tech
│   ├── lore
│   ├── test
│   ├── verification
│   ├── research
│   └── agent
└── scripts
    └── validate-docs.sh
```
