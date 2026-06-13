# 韩文到中文游戏翻译框架调研

AS_OF: 2026-06-13

## 一句话结论

不要押注单一模型。Limbus Translate 应采用“增量 diff + 术语库 + 翻译记忆 + 世界观 RAG + 多引擎候选 + 自动 QA + 人审回写”的生产流水线。模型只是候选译文来源，最终质量主要由上下文、术语一致性、回归评估和审校门槛决定。

## 竞争假设

| 假设 | 评估 |
|---|---|
| 商用 MT 最稳 | 部分成立。DeepL、Google Cloud Translation、Azure Translator、AWS Translate、Papago 都有语言支持或术语/自定义能力，但官方文档不能证明其在韩文到中文游戏科幻域最优。 |
| LLM/GPT 直接翻译最好 | 部分成立。OpenAI 最新模型具备多语言与长上下文能力，适合风格、设定解释和疑难句处理；但全量初译成本、稳定性、术语服从和批量吞吐需要项目内评测。 |
| 开源模型足够替代商用 | 目前不建议作为首选。NLLB、MADLAD、TranslateGemma、LMT-60 等可以做基线或隐私兜底，但必须通过本项目 gold set 验证。 |
| 瓶颈不是模型，而是流程 | 当前最可能。游戏文本短、上下文缺失、专名密集、版本频繁，单句翻译能力不足以保证可上线质量。 |

## 推荐架构

```text
LocalizeLimbusCompany checkout
  -> JSON extractor: file, record id, json path, source hash, placeholders
  -> incremental diff: new / changed / unchanged / locked
  -> retrieval:
       termbase: Paratranz terms + approved local terms
       TM: exact / fuzzy translation memory
       lore RAG: world lore, speaker, nearby story, similar strings
  -> candidate generation:
       Papago / Google Adaptive / Azure / DeepL / Qwen-MT / local baseline
       GPT fallback: difficult lines, style rewrite, arbitration, review notes
  -> QA:
       placeholders, tags, numbers, line breaks, glossary hit rate, length, Simplified Chinese
  -> human review:
       high-risk full review, low-risk sampling, simplified MQM labels
  -> write back:
       approved translation -> target JSON + TM
       approved term -> termbase
       review error -> eval set
```

## 模型策略

| 用途 | 推荐 |
|---|---|
| 初译候选 | Papago、Google Adaptive Translation、Azure Translator、DeepL、Qwen-MT 做项目样本赛马 |
| 科幻 / 游戏风格润色 | GPT-5.5 或同级强 LLM，带术语、RAG 和示例约束 |
| 中文中心批量候选 | Qwen-MT 可加入候选池，但需要韩中实测 |
| 离线 / 隐私 / 成本兜底 | TranslateGemma、LMT-60、MADLAD、NLLB 作为本地基线 |
| 评估 / 仲裁 | COMET / chrF / xCOMET + 简化 MQM 人审；LLM judge 只做辅助解释 |

## 工程要求

1. 每条源文本必须有稳定 `unit_id`、相对文件、JSON path、source hash、上下文信息和占位符列表。
2. 只自动翻译新增和 changed hash；人工 reviewed / locked 译文不能被自动覆盖。
3. 术语库使用 Paratranz 项目 `6860` API 作为主源，离线 CSV / JSON 导入作为兜底。
4. 术语、变量、标签、换行、数字、颜色标签和 UI 长度必须进入自动 QA。
5. 需要建立 500-1000 条 gold set，覆盖 UI、剧情对白、战斗文本、技能、人格、物品、世界观设定和变量句。

## 主要来源

- OpenAI Models: https://developers.openai.com/api/docs/models
- OpenAI GPT-4.1 API release: https://openai.com/index/gpt-4-1/
- DeepL supported languages: https://developers.deepl.com/docs/getting-started/supported-languages
- DeepL glossaries: https://developers.deepl.com/api-reference/multilingual-glossaries
- Google Cloud Translation languages: https://docs.cloud.google.com/translate/docs/languages
- Google Adaptive Translation: https://docs.cloud.google.com/translate/docs/advanced/adaptive-translation
- Google Cloud Translation glossaries: https://docs.cloud.google.com/translate/docs/advanced/glossary
- Meta NLLB: https://ai.meta.com/research/no-language-left-behind/
- XLIFF 2.1: https://docs.oasis-open.org/xliff/xliff-core/v2.1/xliff-core-v2.1.html
- MQM: https://themqm.org/
- Crowdin Translation Memory: https://support.crowdin.com/translation-memory/
- Lokalise Translation Memory: https://docs.lokalise.com/en/articles/1409589-translation-memory
