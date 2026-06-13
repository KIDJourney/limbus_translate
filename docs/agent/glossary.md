# Glossary

| 术语 | 定义 |
|---|---|
| LocalizeLimbusCompany | 参考语言包仓库，包含 `KR`、`EN`、`JP`、`LLC_zh-CN` 等目录 |
| `KR` | 韩文原始资源目录 |
| `LLC_zh-CN` | 简体中文语言包目录 |
| Paratranz | 在线协作翻译平台；项目 `6860` 当前作为术语主来源 |
| Termbase | 词语级术语库，用于专名和固定译名一致性 |
| TM | Translation Memory，句段级翻译记忆，用于复用已审校译文 |
| RAG | 检索增强生成，用世界观、角色和相似句上下文辅助翻译 |
| Gold set | 固定人工参考译文样本，用于比较 provider、prompt 和上下文策略的回归表现 |
| Gold sample | 从 Gold set 按 tag、risk 或 file 分层抽样得到的较小评估集，用于减少样本偏置 |
| Eval comparison | 在同一 Gold set 上并排评估多个 provider/model，并按 pass rate 和 similarity 排名 |
| TranslationUnit | 本项目内部待译单元，包含文件、JSON path、源文、目标文和缺译原因 |
| TranslationContextBundle | 本项目传给 provider 的结构化翻译上下文，当前包含位置、风险、术语、同文件邻近文本、同文件 TM、基础 fuzzy TM 示例和 lore 片段；可由离线 lore index 召回，但还不是外部 embedding RAG |
| LoreEntry | 本地世界观资料缓存条目，包含标题、正文、标签、来源和 anchors，用于翻译上下文召回 |
| LoreIndex | 由 `LoreEntry` 构建的离线 hashed-vector sparse index，用于缓存和验证世界观资料相似召回 |
| RefinedTerm | 术语候选二次提炼结果，包含 `term` / `not_term` / `needs_review` 决策和可选建议译名 |
| Term review pack | 从 `RefinedTerm` 导出的人工审校包，包含 `review.csv`、`review.jsonl` 和 Paratranz 候选导入 CSV |
| Reviewed glossary | 从人工审校后的 `review.csv` 导出的本地 glossary cache；只包含 `approved` 明确为真且译名非空的术语 |
| Promoted glossary | 从 `RefinedTerm` 导出的本地 glossary cache；只包含已确认且有译名的 `term` |
| MQM | Multidimensional Quality Metrics，本地化质量评估框架；本项目 QA 使用 MQM 风格 category 做粗粒度归类 |
| LengthPolicy | QA 使用的长度策略，可按路径、文件前缀、JSON path 后缀或 risk 覆盖字符阈值和 East Asian Width 估算显示宽度；不是像素级 UI 测量 |
| `dry-run` provider | 不调用外部模型，只输出 `[待译] 源文`，用于验证扫描和写回链路 |
