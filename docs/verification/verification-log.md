# Verification Log

本文档维护最近验证状态、证据和风险。

## 最近验证

| 日期 | 场景 | 变更 | 验证 | 结果 |
|---|---|---|---|---|
| 2026-06-13 | Gold set 分层采样 | 新增 `eval sample-gold`，支持按 tag/risk/file 从 gold set 可重复抽样 | `make test`；`python3 -m compileall -q limbus_translate`；`git diff --check`；`make validate-docs`；`make smoke`；真实 Localize checkout `eval build-gold --limit 100` + `eval sample-gold` | 通过；直接测试覆盖按 tag/risk 分层采样和固定 seed 可重复性；fixture smoke 生成 `build/gold-sample.json` 并用于 `eval compare`；真实 gold set 100 条，按 tag 每组 5 条采样生成 15 条 |
| 2026-06-13 | Gold set 多 provider 对比 | 新增 `eval compare`，支持多个 provider/model 在同一 gold set 上输出 ranking 和完整结果 | `make test`；`python3 -m compileall -q limbus_translate`；`git diff --check`；`make smoke`；真实 Localize checkout `eval build-gold --limit 20` + `eval compare` | 通过；直接测试覆盖好/坏 provider ranking 和 compare report 写盘；fixture smoke 生成 `build/eval-compare-report.json`；真实 gold set 20 条，两个 dry-run label compare 生成完整 ranking |
| 2026-06-13 | 审校术语回写 | 新增 `terms apply-review`，把人工审校通过的 `review.csv` 行写成本地 reviewed glossary cache | `make test`；`python3 -m compileall -q limbus_translate`；`git diff --check`；`make validate-docs`；`make smoke`；真实 Localize checkout scan/terms extract/refine/review-pack/apply-review | 通过；直接测试覆盖 approved 判定、空译名跳过和未确认行跳过；fixture smoke 模拟 1 条审校确认并生成 `build/local-reviewed-glossary.json`；真实扫描 19 条，review pack 10 条，模拟确认 `찰-칵 -> 喀嚓` 后生成 1 条 reviewed glossary |
| 2026-06-13 | 术语审校导出 | 新增 `terms review-pack`，导出人工审校 CSV、结构化 JSONL 和 Paratranz 候选导入 CSV | `make test`；`python3 -m compileall -q limbus_translate`；`git diff --check`；`make validate-docs`；`make smoke`；真实 Localize checkout scan/terms extract/refine/review-pack | 通过；直接测试覆盖 review CSV、JSONL 和 Paratranz 候选 CSV；fixture smoke 生成 1 条审校候选；真实扫描 19 条，术语候选 19 条，rules refine 输出 `needs_review=10`、`not_term=9`，真实 review pack 生成 10 条审校候选，Paratranz 候选导入 CSV 为 0 条 |
| 2026-06-13 | QA 长度策略 | 新增 East Asian Width 估算显示宽度检查、`max_display_width` 策略字段和 `line_display_too_wide` MQM design issue | `make test`；`python3 -m compileall -q limbus_translate`；`git diff --check`；`make validate-docs`；`make smoke`；真实 Localize checkout scan/TM/translate limit 3/QA | 通过；直接测试覆盖 display width 触发路径；文档验证通过 36 个 Markdown；fixture smoke QA 读取 sample length policy；真实扫描 19 条 `target_same_as_source`，TM 92337 条，dry-run translate 3 条通过，真实 QA 生成 19 条 accuracy issue |
| 2026-06-13 | Limbus Translate 初版工具 | 新增 Python CLI、JSON 扫描、唯一 `dataList.id` 对齐、缺失 record append 写回、Paratranz 术语同步、TM、state、dry-run 翻译输出、QA MQM category/summary、路径/risk 字符级 length policy、lore cache、gold set build/eval report、术语候选缓存、rules 二次提炼缓存、refined term promote、ContextBundle/provider structured context 和基础 fuzzy TM 示例召回 | `make test`；`make smoke`；`make validate-docs`；`compileall`；`state init`；`lore import`；`eval build-gold`；`eval run`；`glossary sync-paratranz`；真实 Localize checkout 扫描；真实 TM 构建；真实 dry-run translate limit 3 with TM；真实 dry-run QA；`qa --length-policy config/length-policy.sample.json`；`terms extract`；`terms refine --provider rules`；`terms promote` | 通过；fixture 扫描 2 条；数组顺序变化测试通过；缺失 record append 测试通过；locked state 跳过测试通过；QA 简繁/长度/MQM 分类汇总和 length policy 测试通过；lore Markdown / JSON 导入、cache roundtrip、anchors 召回、TF-IDF n-gram 相似召回和 provider context 注入测试通过；gold set 从 reference tree 构建、eval matching/error provider/report 测试通过；真实 dry-run QA 输出 19 条 `accuracy` 类 issue；真实 Localize `eval build-gold --limit 1000` 通过，输出 1000 条，dry-run eval 1000 条报告落盘；fixture smoke 已读取 sample length policy、lore cache，生成 gold set 和 eval report；rules refiner 分类/缓存读写测试通过；refined term promote 测试和手工 CLI 正向验证通过；ContextBundle provider context 与跨文件相似 TM 测试通过；fixture refined terms 输出 3 条，`needs_review=1`、`not_term=2`；fixture promoted glossary 输出 0 条；Paratranz 同步 1963 条；dry-run 输出同结构 JSON；真实默认扫描 19 条，高风险 `StoryData/*.content`；真实带 TM dry-run translate 3 条通过；真实 TM 构建 92337 条；真实术语候选 19 条；真实 rules refine 输出 19 条，`needs_review=10`、`not_term=9`；真实 rules promote 输出 0 条，符合无建议译名不入库的保护规则 |
| 2026-06-10 | 技能化初始化 | 将 `ai-workspace-init` 默认模板来源从本机路径改为 GitHub 仓库 SSH URL | `quick_validate.py` 验证 repo/user 两份 skill；`make validate-docs`；`rg` 确认无本机路径残留；GitHub SSH clone + init smoke test；本地覆盖模式 metadata 检查 | 通过；skill 均有效；文档验证通过；默认来源为 `git@github.com:LobotomyTech/ai_workspace.git` |
| 2026-06-09 | 技能化初始化 | 新增 `ai-workspace-init` skill 和 `scripts/init-ai-workspace.sh` | `make validate-docs`；`python quick_validate.py /Users/kidjourney/.claude/skills/ai-workspace-init`；对 `/tmp/ai-workspace-smoke.GFxRMI` 执行初始化和重复初始化 | 通过；skill 结构有效；首次初始化 `created=35 skipped=0` 并通过 `docs validation passed (31 markdown files)`；重复初始化 `created=0 skipped=35`，未覆盖已有文件 |
| 2026-06-09 | 文档结构变更 | 新增 `docs/design/` 和 `docs/verification/`，将验证记录从 `docs/test/` 拆出 | `make validate-docs` | 通过，输出 `docs validation passed (31 markdown files)` |
| 2026-06-09 | 文档结构变更 | AI Workspace 文档骨架初版 | `make validate-docs` | 通过，输出 `docs validation passed (24 markdown files)` |

## 当前风险

1. 缺失 `dataList` record 可以 append 源 record 并替换已处理字段，但同一 record 中未进入当前 units 的其他韩文字段仍可能需要后续扫描/QA 复审。
2. QA 尚未覆盖按具体 UI 容器的像素级长度限制；当前已有路径/risk 字符级 length policy、估算显示宽度和 MQM 风格分类。
3. lore cache 已支持 anchors、术语和轻量 TF-IDF n-gram 相似召回，尚未升级为 embedding 向量库。
4. Gold set 可从真实 reference tree 自动抽取、分层采样并支持多 provider compare，尚未人工确认为正式模型赛马基准，也未执行真实 OpenAI 多模型评估。
5. 术语候选提取和 rules 二次提炼仍是粗筛；review pack / apply-review 只处理本地审校材料和本地 cache，正式术语仍需要人工确认，OpenAI term refiner 还没有真实 API 验证记录。

## 未覆盖项

- CI 文档检查。
- 本地 promoted glossary 尚未自动同步回 Paratranz 或审校系统正式 termbase；当前只生成候选导入 CSV。
- fuzzy TM 尚未经过真实 gold set 调参。
- 外部世界观 embedding 向量库。
