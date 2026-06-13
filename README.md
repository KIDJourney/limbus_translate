# Limbus Translate

Limbus Translate 是一个面向《Limbus Company》韩文到简体中文本地化的自动化翻译工具。目标是从 `KR/**.json` 原始资源中发现新增或变化文本，结合 Paratranz 术语库、翻译记忆和世界观上下文生成候选译文，再通过自动 QA 与人工审校回写为 `LLC_zh-CN/**.json` 同结构产物。

当前版本先落地可验证的核心骨架：

- JSON 语义扫描：按相对路径和 JSON path 找出目标为空、目标缺失、目标等于韩文源文的候选缺译单元。
- Paratranz 术语同步：匿名分页读取项目 `6860` 的术语 API，缓存为本地统一模型。
- 离线术语导入：支持 CSV / JSON 兜底。
- 世界观资料缓存：支持从 Markdown / JSON / JSONL / CSV / TXT 导入 lore cache，并在翻译上下文中召回相关设定片段。
- 可插拔翻译 provider：默认 `dry-run` 可测试，`openai` provider 作为 GPT 兜底入口。
- 结构化翻译上下文：翻译请求会注入位置、风险、命中术语、同文件邻近文本、同文件 TM、相似 TM 示例和世界观片段。
- 同结构输出：从现有中文文件叠加候选译文，缺目标文件时沿用韩文结构生成输出。
- 审校状态：支持 `reviewed` / `locked` 状态，避免自动覆盖人工定稿。
- 自动 QA：检查韩文残留、占位符、标签、数字、换行、术语命中、疑似繁体和长度风险，并按 MQM 风格类别汇总。
- 术语候选二次提炼：`terms extract` 召回候选后，`terms refine` 用 `rules` 或 `openai` provider 输出 refined cache，确认后的术语可 promote 为本地 glossary cache。
- Gold set 评估：`eval build-gold` 可从已有中译参考构建样本，`eval run` 可比较 provider 输出并报告相似度、格式问题和术语缺失。

## 快速开始

```bash
make validate-docs
make test
make smoke
make sync-glossary
```

对真实 LocalizeLimbusCompany checkout 运行扫描：

```bash
python3 -m limbus_translate.cli scan \
  --source /path/to/LocalizeLimbusCompany/KR \
  --target /path/to/LocalizeLimbusCompany/LLC_zh-CN \
  --output build/missing-units.json
```

生成候选译文：

```bash
python3 -m limbus_translate.cli translate \
  --source /path/to/LocalizeLimbusCompany/KR \
  --target /path/to/LocalizeLimbusCompany/LLC_zh-CN \
  --units build/missing-units.json \
  --glossary cache/glossary/paratranz-6860.json \
  --memory cache/tm/exact.json \
  --lore cache/lore/world.json \
  --state cache/state/units.json \
  --output build/LLC_zh-CN \
  --provider dry-run
```

`--glossary`、`--memory` 和 `--lore` 会参与 provider 的结构化上下文包：exact TM 命中会直接复用译文；未命中时，命中术语、同文件邻近文本、同文件 TM、跨文件相似 TM 示例和 lore 片段会进入 `TranslationRequest.context`。

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

python3 -m limbus_translate.cli eval run \
  --gold cache/eval/gold-set.json \
  --provider dry-run \
  --report build/eval-report.json

python3 -m limbus_translate.cli terms extract \
  --units build/missing-units.json \
  --glossary cache/glossary/paratranz-6860.json \
  --output cache/terms/candidates.json

python3 -m limbus_translate.cli terms refine \
  --candidates cache/terms/candidates.json \
  --output cache/terms/refined.json \
  --provider rules

python3 -m limbus_translate.cli terms promote \
  --refined cache/terms/refined.json \
  --output cache/glossary/local-refined.json \
  --merge cache/glossary/paratranz-6860.json
```

`refined.json` 中的 `decision` 为 `term` / `not_term` / `needs_review`，并保留 `suggested_target`、`confidence`、`note`、`contexts`、`provider` 等字段。`terms promote` 只会导出 `decision=term` 且有 `suggested_target` 的记录，供人工审校后进入正式术语库。

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
│   └── length-policy.sample.json
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
