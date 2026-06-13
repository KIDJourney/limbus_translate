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
| TranslationUnit | 本项目内部待译单元，包含文件、JSON path、源文、目标文和缺译原因 |
| `dry-run` provider | 不调用外部模型，只输出 `[待译] 源文`，用于验证扫描和写回链路 |
| MQM | Multidimensional Quality Metrics，本地化质量评估框架 |
