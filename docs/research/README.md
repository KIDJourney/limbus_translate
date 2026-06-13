# Research

本目录记录需要外部资料支撑、且会随模型和平台变化而过期的研究结论。稳定架构决策写入 [agent/decisions.md](../agent/decisions.md)，操作命令写入 [tech/operations.md](../tech/operations.md)。

## 索引

| 文档 | 内容 | 复核节奏 |
|---|---|---|
| [translation-framework.md](translation-framework.md) | 韩文到中文游戏翻译框架、模型候选池、模型赛马流程和上线门槛 | 默认模型、供应商能力或评估口径变化时复核 |

## 维护原则

1. 研究结论必须写明 `AS_OF` 日期和 source registry。
2. 模型优劣只作为假设，必须回到项目 curated gold set 和 `eval compare` 验证。
3. Paratranz 项目 `6860` 是术语主源；研究文档只引用，不替代本地 glossary cache 和审校流程。
