# Docs

本目录是 AI Workspace 的长期知识库。根目录 `AGENTS.md` 负责入口和规则；`docs/` 负责承载可以被人和 agent 长期复用的项目事实。

## 文档索引

| 目录 | 维护内容 | 典型读者 |
|---|---|---|
| [product](product/README.md) | 产品定位、PRD、范围、用户故事、路线图 | 产品 agent、实现 agent、评审者 |
| [design](design/README.md) | 体验目标、信息架构、交互、UI、组件状态、视觉规范 | 设计 agent、前端 agent、评审者 |
| [tech](tech/README.md) | 架构、模块职责、接口、数据、依赖、运维 | 架构 agent、开发 agent、排障 agent |
| [research](research/README.md) | 模型、流程和外部资料调研，沉淀需要定期复核的判断 | 研究 agent、架构 agent、翻译 agent |
| [lore](lore/README.md) | 世界观、角色、组织和设定笔记，用于 lore cache 导入 | 翻译 agent、审校者 |
| [test](test/README.md) | 测试策略、测试方案、自动化覆盖、回归要求 | 测试 agent、开发 agent |
| [verification](verification/README.md) | 业务场景验证方法、证据、结论、阻塞点、未覆盖项 | 验证 agent、发布 agent、评审者 |
| [agent](agent/README.md) | 当前上下文、决策记录、术语、交接记录 | 所有未来 agent |
| [templates](templates/README.md) | PRD、设计、技术、测试、验证、决策记录模板 | 需要新增文档的 agent |

## 维护原则

1. 入口短，知识分层：`AGENTS.md` 不承载长背景，详细内容放在本目录。
2. 单一事实源：同一事实只放一个权威位置，其他文档用链接引用。
3. 任务驱动读取：agent 按任务读取相关目录，不默认全量加载。
4. 证据优先：验证结论、发布结论和风险结论必须带命令、日志、截图或复现路径。
5. 持续更新：任何需求、设计、架构、接口、测试或验证边界变化，都要同步修改对应文档。

## 新增文档流程

1. 先确认文档类型：产品、设计、技术、测试、验证、agent 知识或模板。
2. 从 [templates](templates/README.md) 选择对应模板。
3. 新文档放到对应目录，并更新该目录 README 的索引。
4. 如果文档变成权威入口，同步更新 `AGENTS.md` 的“权威文档”表。
5. 运行 `make validate-docs`。
