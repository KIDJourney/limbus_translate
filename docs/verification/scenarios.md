# Verification Scenarios

本文档按业务场景维护验证方式。不同业务场景可以复用同一测试命令，但不能共用同一个通过结论。

## 场景矩阵

| 业务场景 | 验证目标 | 推荐方法 | 通过标准 | 记录位置 |
|---|---|---|---|---|
| 文档结构变更 | 确认入口、目录和链接可用 | 结构检查 + 链接检查 | `make validate-docs` 通过，目录索引与实际文件一致 | [verification-log.md](verification-log.md) |
| 产品需求变更 | 确认需求边界清楚，未混入实现细节 | PRD 审查 + 关联测试方案 | PRD 有目标、非目标、范围、验收标准 | [verification-log.md](verification-log.md) |
| 设计 / UI 变更 | 确认体验、交互、状态、视觉边界清楚 | 设计走查 + 截图 / 原型检查 | 关键状态齐全，文本不溢出，路径可达 | [verification-log.md](verification-log.md) |
| 技术实现变更 | 确认代码满足方案且不破坏边界 | 构建、单测、集成测试、代码审查 | 相关命令通过，风险有记录 | [verification-log.md](verification-log.md) |
| 发布 / 交付变更 | 确认用户拿到的产物可用 | 最终产物验证 + 回滚检查 | 使用最终产物完成主路径，失败可回滚 | [verification-log.md](verification-log.md) |
| Agent 上下文变更 | 确认新会话能恢复项目事实 | 入口读取演练 + 链接检查 | 从 `AGENTS.md` 能找到正确权威文档 | [verification-log.md](verification-log.md) |

## 场景维护规则

1. 新增业务场景时，必须说明验证目标和通过标准。
2. 如果场景依赖特定环境，必须写清楚环境前提。
3. 如果自动化无法覆盖用户主路径，必须补手动或 E2E 验证方式。
