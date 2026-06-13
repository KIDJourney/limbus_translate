# 韩文到中文游戏翻译框架调研

AS_OF: 2026-06-14

## 结论

不要把 Limbus Translate 设计成“选一个最强模型直接翻完”。截至 2026-06-14，官方资料只能证明各供应商具备韩文/中文翻译、术语、自适应或定制能力，不能证明任何一个模型在《Limbus Company》这种科幻游戏文本上稳定最优。正确路径是：用项目自己的 curated gold set 对候选模型赛马，把模型当候选译文来源，再由术语库、翻译记忆、世界观上下文、自动 QA 和人工审校控制上线质量。

当前工程默认保留 OpenAI provider 作为强 LLM 兜底；批量初译候选建议优先加入 Qwen-MT、Google Cloud Translation、Azure Translator、DeepL 和 Amazon Translate。所有候选必须通过 `eval compare`、request log、candidate cache 和 review pack 闭环验证后，才能变成默认生产路径。

## 前提审查

| 用户/项目假设 | 判断 |
|---|---|
| “有一个韩文到中文效果最好的模型” | 未验证。公开榜单和供应商资料通常不是 Limbus 游戏文本、术语和格式约束。 |
| “LLM 可以直接替代本地化流程” | 不成立。游戏文本短、上下文缺失、变量/标签多，必须工程化注入上下文和 QA。 |
| “术语可以自动提炼后直接入库” | 不成立。自动提炼只能减少筛选成本，正式 termbase 仍要人审。 |
| “GPT 兜底足够” | 部分成立。强 LLM 适合疑难句、风格重写和仲裁，但全量批译成本、稳定性和术语服从要实测。 |

## 竞争假设

| 假设 | 当前评估 | 处理方式 |
|---|---|---|
| H1: 专用 MT 服务最稳 | 有可能。Google、Azure、DeepL、AWS 都有成熟 MT / glossary / customization 能力，但不一定擅长游戏语境。 | 作为批量候选池，跑 gold set。 |
| H2: Qwen-MT 更适合中文中心的韩中翻译 | 有可能。官方文档显示 Qwen-MT 支持中日韩等 92 种语言和术语/领域/记忆能力。 | 优先接入或通过 OpenAI-compatible API 赛马。 |
| H3: GPT 系列最适合风格与上下文 | 有可能。OpenAI 当前模型线适合作为强 LLM 兜底和高风险文本处理。 | 保留 `openai:<model>`，用于疑难句和模型赛马。 |
| H4: 开源 MT 可做低成本离线基线 | 部分成立。NLLB 证明多语言 MT 路线可行，但项目域质量未知。 | 只做 privacy/cost baseline，不作为首选上线模型。 |
| H5: 模型不是主要瓶颈 | 当前最可信。术语、上下文、增量 diff、审校和 QA 对质量影响更稳定。 | 继续优先完善 workflow、RAG、gold set 和 review loop。 |

## 候选模型池

| 候选 | 作为 | 官方证据 | 项目内判断 |
|---|---|---|---|
| OpenAI GPT 系列 | 高风险文本、风格修订、仲裁、兜底 | OpenAI models 文档列出当前模型线；GPT-4.1 发布说明强调长上下文和指令能力。 | 已有 `openai` / `openai:<model>` provider；默认不假设最优，必须跑 curated gold。 |
| Qwen-MT | 中文中心批量候选 | Qwen-MT 官方文档称支持 92 种语言，提供术语干预、领域提示和记忆库；Qwen 文档说明可通过 OpenAI-compatible Chat Completions、单条 user message 和 `translation_options` 调用。 | 已接入 `qwen-mt` provider，可进入 `eval compare`；仍需真实韩文->简中 curated gold 评估。 |
| Google Cloud Translation | 企业 MT 基线、自适应 MT | Google Cloud Translation 支持语言列表包含 Korean 和 Chinese；官方提供 glossary 和 adaptive translation。 | 适合和项目 TM/reference pairs 结合赛马。 |
| Azure Translator / Custom Translator | 企业 MT 基线、自定义模型 | Azure language support 包含 Korean 和 Chinese Simplified；Custom Translator 支持用文档/词典构建定制 NMT 系统。 | 可作为有云资源时的定制 MT 候选。需验证直连韩->简中定制路径和成本。 |
| DeepL API | 通用 MT 基线 | DeepL API 提供 supported languages endpoint、glossary、style rules 和 translation memory 相关能力。 | 可加入候选，但韩->简中的具体质量必须本项目评测。 |
| Amazon Translate | 云 MT 基线 | Amazon Translate 官方说明其用于按需文本翻译和多语言应用。 | 适合作为 AWS 环境里的 baseline；术语/语言对需按实际账号验证。 |
| NLLB / 开源 MT | 离线/隐私基线 | Meta NLLB 覆盖 200 语言，并使用扩展 FLORES 做质量评估。 | 不建议直接生产；可作为离线 cost baseline。 |

## 推荐赛马流程

1. 从真实 `KR` / `LLC_zh-CN` 构建 gold set：

```bash
python3 -m limbus_translate.cli eval build-gold \
  --source /path/to/LocalizeLimbusCompany/KR \
  --target /path/to/LocalizeLimbusCompany/LLC_zh-CN \
  --glossary cache/glossary/paratranz-6860.json \
  --output cache/eval/gold-set.json \
  --limit 1000
```

2. 分层抽样并人工审校：

```bash
python3 -m limbus_translate.cli eval sample-gold \
  --gold cache/eval/gold-set.json \
  --output cache/eval/gold-sample.json \
  --per-group 20 \
  --group-by tag \
  --seed 7

python3 -m limbus_translate.cli eval review-pack \
  --gold cache/eval/gold-sample.json \
  --output-dir build/gold-review
```

3. 只对 curated gold 做模型赛马：

```bash
python3 -m limbus_translate.cli eval compare \
  --gold cache/eval/gold-curated.json \
  --provider baseline=dry-run \
  --provider gpt=openai:gpt-4.1 \
  --report build/eval-compare-report.json
```

4. 新 provider 接入后必须加入同一命令，不单独换样本：

```bash
python3 -m limbus_translate.cli eval compare \
  --gold cache/eval/gold-curated.json \
  --provider gpt=openai:gpt-4.1 \
  --provider qwen=qwen-mt:qwen-mt-plus \
  --provider google=google-adaptive \
  --report build/eval-compare-report.json
```

## 上线门槛

| 门槛 | 要求 |
|---|---|
| 覆盖 | curated gold 至少覆盖 UI、剧情对白、战斗文本、技能、人格、物品、世界观和变量句。 |
| 格式 | placeholder、tag、数字、换行不能回归。 |
| 术语 | 命中 Paratranz / local-reviewed glossary；冲突术语必须先审校。 |
| 质量 | 自动 similarity 只能做过滤；最终要以 review pack 的人工结果为准。 |
| 成本 | provider request log 和 candidate cache 必须开启，避免不可复现的模型调用。 |
| 默认模型变更 | 任何默认 provider 变更必须更新 verification log，并附 `eval compare` 报告路径。 |

## 工程路线

1. 保持 `openai` provider 作为强 LLM 兜底，避免阻塞。
2. 已新增 OpenAI-compatible Chat Completions provider 和专用 `qwen-mt` provider，用于 Qwen-MT、DashScope 或其他兼容端点进入模型赛马。
3. 新增 Google / Azure / DeepL provider 时，只接入候选生成，不直接绕过 QA 和 review。
4. 给 `eval compare` 增加 request log / provider cost metadata，方便模型赛马复盘。
5. 对 curated gold 做人工分层维护，禁止用未审自动抽样证明模型最优。

## Source Registry

| ID | Source | Type | Accessibility | AS_OF | 用途 |
|---|---|---|---|---|---|
| S1 | https://developers.openai.com/api/docs/models | official | public | 2026-06-14 | OpenAI 当前模型线。 |
| S2 | https://openai.com/index/gpt-4-1/ | official | public | 2026-06-14 | GPT-4.1 API 发布和能力背景。 |
| S3 | https://help.aliyun.com/zh/model-studio/machine-translation | official | public | 2026-06-14 | Qwen-MT 语言、术语、领域提示、记忆库和模型选择。 |
| S4 | https://qwenlm.github.io/blog/qwen-mt/ | official | public | 2026-06-14 | Qwen-MT 设计、评估和 OpenAI-compatible 调用示例。 |
| S5 | https://docs.cloud.google.com/translate/docs/languages | official | public | 2026-06-14 | Google Cloud Translation 语言支持。 |
| S6 | https://docs.cloud.google.com/translate/docs/advanced/glossary | official | public | 2026-06-14 | Google glossary 用于领域术语。 |
| S7 | https://docs.cloud.google.com/translate/docs/advanced/adaptive-translation | official | public | 2026-06-14 | Google adaptive translation reference pairs。 |
| S8 | https://learn.microsoft.com/en-us/azure/ai-services/translator/language-support | official | public | 2026-06-14 | Azure Translator 语言支持。 |
| S9 | https://learn.microsoft.com/en-us/azure/ai-services/translator/custom-translator/overview | official | public | 2026-06-14 | Azure Custom Translator 定制能力。 |
| S10 | https://developers.deepl.com/docs/getting-started/supported-languages | official | public | 2026-06-14 | DeepL API language endpoint and feature availability。 |
| S11 | https://developers.deepl.com/api-reference/multilingual-glossaries | official | public | 2026-06-14 | DeepL glossary 管理能力。 |
| S12 | https://docs.aws.amazon.com/translate/latest/dg/what-is.html | official | public | 2026-06-14 | Amazon Translate 基线能力。 |
| S13 | https://ai.meta.com/research/no-language-left-behind/ | official | public | 2026-06-14 | NLLB / FLORES 多语言 MT 背景。 |
| S14 | https://www.alibabacloud.com/help/en/model-studio/compatibility-of-openai-with-dashscope | official | public | 2026-06-14 | DashScope OpenAI-compatible Chat base URL 和 `/chat/completions` 端点。 |
| S15 | https://www.alibabacloud.com/help/en/model-studio/machine-translation | official | public | 2026-06-14 | Qwen-MT 单条 user message、`translation_options`、模型选择和语言支持。 |
