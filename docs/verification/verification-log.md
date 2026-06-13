# Verification Log

本文档维护最近验证状态、证据和风险。

## 最近验证

| 日期 | 场景 | 变更 | 验证 | 结果 |
|---|---|---|---|---|
| 2026-06-13 | Limbus Translate 初版工具 | 新增 Python CLI、JSON 扫描、唯一 `dataList.id` 对齐、缺失 record append 写回、Paratranz 术语同步、TM、state、dry-run 翻译输出、QA、术语候选缓存和 rules 二次提炼缓存 | `make test`；`make smoke`；`make validate-docs`；`compileall`；`state init`；`glossary sync-paratranz`；真实 Localize checkout 扫描；真实 TM 构建；`terms extract`；`terms refine --provider rules` | 通过；fixture 扫描 2 条；数组顺序变化测试通过；缺失 record append 测试通过；locked state 跳过测试通过；QA 简繁/长度测试通过；rules refiner 分类/缓存读写测试通过；fixture refined terms 输出 3 条，`needs_review=1`、`not_term=2`；Paratranz 同步 1963 条；dry-run 输出同结构 JSON；真实默认扫描 19 条，高风险 `StoryData/*.content`；真实 TM 构建 92337 条；真实术语候选 19 条；真实 rules refine 输出 19 条，`needs_review=10`、`not_term=9` |
| 2026-06-10 | 技能化初始化 | 将 `ai-workspace-init` 默认模板来源从本机路径改为 GitHub 仓库 SSH URL | `quick_validate.py` 验证 repo/user 两份 skill；`make validate-docs`；`rg` 确认无本机路径残留；GitHub SSH clone + init smoke test；本地覆盖模式 metadata 检查 | 通过；skill 均有效；文档验证通过；默认来源为 `git@github.com:LobotomyTech/ai_workspace.git` |
| 2026-06-09 | 技能化初始化 | 新增 `ai-workspace-init` skill 和 `scripts/init-ai-workspace.sh` | `make validate-docs`；`python quick_validate.py /Users/kidjourney/.claude/skills/ai-workspace-init`；对 `/tmp/ai-workspace-smoke.GFxRMI` 执行初始化和重复初始化 | 通过；skill 结构有效；首次初始化 `created=35 skipped=0` 并通过 `docs validation passed (31 markdown files)`；重复初始化 `created=0 skipped=35`，未覆盖已有文件 |
| 2026-06-09 | 文档结构变更 | 新增 `docs/design/` 和 `docs/verification/`，将验证记录从 `docs/test/` 拆出 | `make validate-docs` | 通过，输出 `docs validation passed (31 markdown files)` |
| 2026-06-09 | 文档结构变更 | AI Workspace 文档骨架初版 | `make validate-docs` | 通过，输出 `docs validation passed (24 markdown files)` |

## 当前风险

1. 缺失 `dataList` record 可以 append 源 record 并替换已处理字段，但同一 record 中未进入当前 units 的其他韩文字段仍可能需要后续扫描/QA 复审。
2. QA 尚未覆盖 MQM 分类和按具体 UI 容器的像素级长度限制；当前只有字符级长度风险。
3. 术语候选提取和 rules 二次提炼仍是粗筛；正式术语需要人工确认，OpenAI term refiner 还没有真实 API 验证记录。

## 未覆盖项

- CI 文档检查。
- refined term 审校结果回写正式 termbase。
- fuzzy TM。
