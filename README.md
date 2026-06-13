# Limbus Translate

Limbus Translate 是一个面向《Limbus Company》韩文到简体中文本地化的自动化翻译工具。目标是从 `KR/**.json` 原始资源中发现新增或变化文本，结合 Paratranz 术语库、翻译记忆和世界观上下文生成候选译文，再通过自动 QA 与人工审校回写为 `LLC_zh-CN/**.json` 同结构产物。

当前版本先落地可验证的核心骨架：

- JSON 语义扫描：按相对路径和 JSON path 找出目标为空、目标缺失、目标等于韩文源文的候选缺译单元。
- Paratranz 术语同步：匿名分页读取项目 `6860` 的术语 API，缓存为本地统一模型。
- 离线术语导入：支持 CSV / JSON 兜底。
- 可插拔翻译 provider：默认 `dry-run` 可测试，`openai` provider 作为 GPT 兜底入口。
- 同结构输出：从现有中文文件叠加候选译文，缺目标文件时沿用韩文结构生成输出。

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
  --output build/LLC_zh-CN \
  --provider dry-run
```

构建翻译记忆和 QA 报告：

```bash
python3 -m limbus_translate.cli tm build \
  --source /path/to/LocalizeLimbusCompany/KR \
  --target /path/to/LocalizeLimbusCompany/LLC_zh-CN \
  --output cache/tm/exact.json

python3 -m limbus_translate.cli qa \
  --units build/missing-units.json \
  --output-root build/LLC_zh-CN \
  --glossary cache/glossary/paratranz-6860.json \
  --report build/qa-report.json
```

使用 OpenAI provider 前需要安装可选依赖并设置 API key：

```bash
python3 -m pip install '.[openai]'
OPENAI_TRANSLATION_MODEL=gpt-4.1 python3 -m limbus_translate.cli translate ...
```

## 目录

```text
.
├── AGENTS.md
├── README.md
├── Makefile
├── limbus_translate
│   ├── cli.py
│   ├── glossary.py
│   ├── json_paths.py
│   ├── providers.py
│   ├── scanner.py
│   └── translator.py
├── tests
│   └── fixtures
├── docs
│   ├── product
│   ├── tech
│   ├── test
│   ├── verification
│   ├── research
│   └── agent
└── scripts
    └── validate-docs.sh
```
