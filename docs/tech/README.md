# Tech Docs

本目录维护技术层事实：系统结构、模块职责、接口、数据、依赖、运行方式、技术风险和设计取舍。产品范围放到 `docs/product/`，设计/UI 放到 `docs/design/`，测试方案放到 `docs/test/`，验证证据放到 `docs/verification/`。

## 文档索引

| 文档 | 维护内容 |
|---|---|
| [architecture.md](architecture.md) | 当前架构、目录职责、文档流、agent 读取路径 |
| [operations.md](operations.md) | 本地命令、验证脚本、维护流程、后续自动化方向 |

## 维护规则

1. 架构、目录职责、接口、数据、依赖变化，更新 [architecture.md](architecture.md)。
2. 本地命令、验证流程、CI 或自动化变化，更新 [operations.md](operations.md)。
3. 技术决策需要能被未来复盘时，额外记录到 `docs/agent/decisions.md`。
4. 测试结果和验收证据不写在这里，写到 `docs/verification/verification-log.md`。
