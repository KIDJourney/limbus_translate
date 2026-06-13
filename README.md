# Limbus Translate

Limbus Translate 是一个面向《Limbus Company》韩文到简体中文本地化的自动化翻译工具。目标是从 `KR/**.json` 原始资源中发现新增或变化文本，结合 Paratranz 术语库、翻译记忆和世界观上下文生成候选译文，再通过自动 QA 与人工审校回写为 `LLC_zh-CN/**.json` 同结构产物。

当前版本先落地可验证的核心骨架：

- JSON 语义扫描：按相对路径和 JSON path 找出目标为空、目标缺失、目标等于韩文源文的候选缺译单元，并可用 scan policy 配置文件按文件类型纳入或排除路径。
- Paratranz 术语同步：匿名分页读取项目 `6860` 的术语 API，缓存为本地统一模型。
- 离线术语导入：支持 CSV / JSON 兜底。
- 世界观资料缓存：支持从 Markdown / JSON / JSONL / CSV / TXT 导入 lore cache，并通过 anchors、术语、轻量 TF-IDF n-gram 和离线 hashed-vector 索引召回相关设定片段。
- 可插拔翻译 provider：默认 `dry-run` 可测试，`openai` provider 作为 GPT 兜底入口。
- 结构化翻译上下文：翻译请求会注入位置、风险、命中术语、同文件邻近文本、同文件 TM、相似 TM 示例和世界观片段。
- 同结构输出：从现有中文文件叠加候选译文，缺目标文件时沿用韩文结构生成输出。
- 审校状态：支持 `reviewed` / `locked` 状态，避免自动覆盖人工定稿。
- 自动 QA：检查韩文残留、占位符、标签、数字、换行、术语命中、疑似繁体、字符长度和估算显示宽度风险，并按 MQM 风格类别汇总。
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

python3 -m limbus_translate.cli scan \
  --source /path/to/LocalizeLimbusCompany/KR \
  --target /path/to/LocalizeLimbusCompany/LLC_zh-CN \
  --output build/missing-units.json \
  --scan-policy config/scan-policy.sample.json \
  --changed-files build/changed-files.txt
```

`--scan-policy` 接受 JSON 规则文件，支持按 `relative_file`、`relative_file_prefix`、`json_path`、`json_path_suffix`、`key` 和 `source_contains` 做 `include` / `exclude`。这用于把特定文件里的可见文本路径纳入扫描，也用于过滤内部事件名、显示占位和无用文本等噪声；不传该参数时仍使用内置默认规则。

`--changed-files` 接受 `git diff --name-only` 这类换行分隔清单，只扫描清单中涉及的 JSON 相对文件；`KR/Foo.json`、`LLC_zh-CN/Foo.json` 和 `Foo.json` 都会归一化为同一个相对路径，非 JSON 行会被忽略。不传该参数时执行全量扫描。

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
  --output build/LLC_zh-CN \
  --provider dry-run
```

`--glossary`、`--memory`、`--lore` 和 `--lore-index` 会参与 provider 的结构化上下文包：exact TM 命中会直接复用译文；未命中时，命中术语、同文件邻近文本、同文件 TM、跨文件相似 TM 示例和 lore 片段会进入 `TranslationRequest.context`。同时提供 `--lore` 与 `--lore-index` 时，翻译上下文优先使用索引召回。

构建翻译记忆和 QA 报告：

```bash
python3 -m limbus_translate.cli tm build \
  --source /path/to/LocalizeLimbusCompany/KR \
  --target /path/to/LocalizeLimbusCompany/LLC_zh-CN \
  --output cache/tm/exact.json

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
│   ├── scanner.py
│   ├── state.py
│   ├── terms.py
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
