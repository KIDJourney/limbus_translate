# AGENTS.md — Limbus Translate 项目指南

给未来的 Codex / Claude / Cursor / Copilot 会话：先读这份，再动手。根目录入口只保留稳定规则和索引；长期上下文、产品事实、技术方案、测试方案和验证证据都维护在 `docs/`。

## 项目定位

Limbus Translate 是一个自动化游戏翻译工具，目标是把《Limbus Company》LocalizeLimbusCompany 仓库中的韩文 `KR/**.json` 资源增量翻译为简体中文 `LLC_zh-CN/**.json`。项目核心不是单次调用模型，而是建立可复用的工程流水线：语义 diff、术语库、翻译记忆、世界观上下文、候选译文生成、自动 QA、人工审校和记忆回写。

## 权威文档

| 场景 | 先读文档 |
|---|---|
| 理解项目全貌 | `README.md`、`docs/README.md` |
| 写产品需求、改功能范围 | `docs/product/README.md`、`docs/product/prd.md` |
| 做架构或技术实现 | `docs/tech/README.md`、`docs/tech/architecture.md` |
| 理解 Localize 数据 | `docs/tech/localize-data-study.md` |
| 理解翻译模型和流程 | `docs/research/translation-framework.md` |
| 写测试方案或验收标准 | `docs/test/README.md`、`docs/test/test-plan.md` |
| 按业务场景验证结果 | `docs/verification/README.md`、`docs/verification/scenarios.md` |
| 恢复 agent 工作上下文 | `docs/agent/context.md`、`docs/agent/decisions.md` |
| 新建文档 | `docs/templates/` 下对应模板 |

## 当前信息架构

```text
limbus_translate/           # Python CLI 和核心库
tests/                      # 最小 fixture 和测试
docs/
  product/                  # 产品文档：愿景、PRD、范围、用户故事
  research/                 # 外部调研：模型、流程、信源
  tech/                     # 技术文档：架构、数据、接口、运维
  test/                     # 测试文档：测试策略、测试用例、回归要求
  verification/             # 验证文档：业务场景、验证方法、证据、结论
  agent/                    # agent 知识：上下文、决策、术语、交接
scripts/
  validate-docs.sh          # 最小文档结构和链接验证
```

## 工作流

1. 先根据任务类型读取对应文档，不要全量扫描无关上下文。
2. 修改任何文件前，先读取该文件现有内容和同目录 README。
3. 产品范围变化先更新 `docs/product/`，再实现。
4. 架构、接口、数据、依赖或部署变化同步更新 `docs/tech/`。
5. 测试策略、测试用例和回归要求同步更新 `docs/test/`。
6. 业务场景验证方法、证据、结果和阻塞点同步更新 `docs/verification/`。
7. 会影响后续 agent 判断的经验、约束、决策，记录到 `docs/agent/`。
8. 完成前运行相关验证，并在回复中说明结果。

## 文档维护边界

- `AGENTS.md` 只放高频入口、权威索引和稳定规则，不堆长篇背景。
- `CLAUDE.md` 是指向 `AGENTS.md` 的软链接，避免双写漂移。
- `docs/product/` 只写用户价值、范围、需求和产品边界，不写实现细节。
- `docs/tech/` 只写技术事实、设计选择、接口、数据、运行方式和技术风险。
- `docs/research/` 只写外部调研、信源、竞争假设和结论。
- `docs/test/` 只写测试策略、测试用例、自动化覆盖和回归要求。
- `docs/verification/` 只写面向业务场景的验证方法、证据、结论、阻塞点和未覆盖项。
- `docs/agent/` 只写会跨会话复用的上下文，不记录临时聊天流水。

## 常用命令

```bash
make validate-docs
make test
make smoke
make sync-glossary
rg "TODO|待确认|阻塞" docs
```

## Git 规则

- 提交前先看 `git status --short --untracked-files=all`。
- 不把无关文档重排、格式化和需求变更混进同一个 commit。
- 约定式 commit：`<type>(<scope>): <subject>`。
- 不使用 `git reset --hard`、`git checkout --`、`push --force` 等破坏性命令，除非用户明确要求。
