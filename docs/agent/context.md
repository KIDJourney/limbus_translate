# Agent Context

本文档维护未来 agent 启动时需要快速恢复的当前上下文。

## 当前状态

Limbus Translate 当前处于 v0.1 工具骨架阶段。仓库已通过 `ai-workspace-init` 初始化为 AI Workspace，并新增 Python CLI，用于扫描 LocalizeLimbusCompany 韩文资源与简中资源的缺译差异、同步 Paratranz 术语、生成 dry-run 翻译输出。`translate` provider 已接收结构化上下文包，包含位置、风险、术语、同文件邻近文本、同文件 TM 和跨文件相似 TM 示例。

## 默认假设

1. 目标语言方向是韩文 `ko` 到简体中文 `zh-cn`。
2. LocalizeLimbusCompany 的 `KR/**.json` 是源语言主输入，`LLC_zh-CN/**.json` 是目标输出参考。
3. Paratranz 项目 `6860` 是术语主来源，API 当前匿名可读，术语数约 1963。
4. 翻译流程必须保留 JSON 结构、占位符、标签、换行和文件路径。
5. 没有模型 API key 时，`dry-run` provider 仍应能验证扫描和写回链路。
6. 上下文包只服务候选译文生成，不改变 JSON 写回、state lock、QA 和人审门槛。

## 参考来源

- LocalizeLimbusCompany: https://github.com/LocalizeLimbusCompany/LocalizeLimbusCompany
- Paratranz 术语项目: https://paratranz.cn/projects/6860/terms
- 技术架构见 [architecture.md](../tech/architecture.md)。
- 数据研究见 [localize-data-study.md](../tech/localize-data-study.md)。
- 翻译框架调研见 [translation-framework.md](../research/translation-framework.md)。

## 下一步

1. 根据实际要开发的应用或工具，补充技术栈和代码目录。
2. 把 `docs/product/prd.md` 从骨架 PRD 扩展成真实产品需求。
3. 如果有界面或交互，先补 `docs/design/` 再实现。
4. 如果业务场景复杂，先补 `docs/verification/scenarios.md` 再验收。
5. 如果要复用到多个项目，新增初始化脚本。
6. 如果需要多工具协同，设计 `.agents/` 或规则生成层。
