# Limbus Translate PRD

本文档维护 Limbus Translate 当前产品定义、功能范围和实现进展。

## 产品定位

Limbus Translate 是一个韩文到简体中文的游戏本地化自动化工具。它面向《Limbus Company》这类版本频繁、术语密集、世界观复杂的 JSON 语言包，以 GitHub `LLC_zh-CN` 现有中文为目标基线，自动发现未翻译、仍是韩文或源文已变化的缺口，结合术语库、翻译记忆和上下文生成候选译文，并输出与目标语言包同结构的增量补丁或翻译产物。

## 目标用户

| 用户 | 需求 |
|---|---|
| 游戏本地化维护者 | 希望每次上游更新后快速知道 `LLC_zh-CN` 里哪些缺口需要补译，而不是重翻已有中文 |
| 翻译 / 审校人员 | 希望候选译文遵守既有术语、角色口吻和世界观设定 |
| 工具开发者 | 希望翻译流程可测试、可缓存、可回归，而不是不可控的一次性 prompt |

## 核心问题

1. LocalizeLimbusCompany 的原始语言目录和中文目录同结构但文件多、字段多，人工发现新增文本成本高。
2. 游戏存在大量专名、组织、技能、人格、E.G.O、世界观概念，单句机器翻译容易造成译名漂移。
3. 上游更新分为 `Auto RAW Update` 和 `Auto GTP Update` 等模式，需要区分原文同步、译文修正和维护提交。
4. 韩文游戏文本存在省略主语、敬语、角色口吻、变量标签和 UI 长度限制，必须通过自动 QA 与人工审校兜底。

## 当前版本范围

| 功能 | 定义 | 当前进展 |
|---|---|---|
| 缺译扫描 | 比较 `KR` 与 `LLC_zh-CN`，输出待译单元 JSON；可用上一版 `KR` 做源文 path 级 diff | 已完成 Localize commit 输入准备、全量扫描、scan policy、changed-files 文件级过滤和 source-baseline JSON path 级源文变化扫描；`workflow run` 可直接从 Localize checkout 的 base/head 准备输入；源文变化但目标已有旧中文会标记为 `source_changed` |
| 术语同步 | 从 Paratranz 项目 `6860` 分页同步术语缓存，并对缓存质量做本地审计 | 已完成同步、audit 和多来源 glossary cache 合并；可把 Paratranz 基础库与本地人工审校术语合成 active glossary，workflow summary 可暴露术语库问题分布 |
| 术语候选二次提炼 | 将 heuristic 候选分为正式术语、非术语、需人工确认，并可给出建议译名 | 已完成 rules provider 初版，OpenAI provider 可选；支持持久 refined cache，跨更新复用已提炼 source，只对新增候选调用 refiner；可导出 review pack，审校确认后可写入本地 glossary cache；`workflow run` 默认产出本次新增术语候选和审校包 |
| 离线术语导入 | 支持 CSV / JSON 术语导入 | 已完成初版 |
| 翻译 provider | `dry-run` 可测试，`openai` 可作为 GPT 兜底，OpenAI-compatible Chat / Qwen-MT 可进入模型赛马 | 已完成 `dry-run`、Responses API `openai`、通用 `openai-chat` 和专用 `qwen-mt` provider；Qwen-MT 真实质量尚待 curated gold 评估 |
| 翻译上下文包 | 将缺译原因、旧译文、同文件邻近文本、exact TM 示例、相似 TM 示例、术语命中和世界观资料片段注入 provider context | 已完成轻量 ContextBundle 初版；`source_changed` 会携带旧中文供 provider 修订 |
| 候选译文缓存 / Request log / Trace | 缓存 provider 候选译文、记录 provider 入参、响应 metadata、usage 汇总与每条译文来源，避免重复模型调用并支持复盘 | 已完成初版；cache key 绑定 provider、source hash、context hash 和 glossary hash，request log 记录 `target_text`、响应模型、响应 id 和 token usage，workflow 默认产出候选缓存、request log、usage summary 与 JSONL trace |
| 世界观资料缓存 | 从本地笔记导入可召回 lore cache，辅助角色、组织、设定一致性 | 已完成 Markdown / JSON / JSONL / CSV / TXT 导入、关键词召回、轻量 TF-IDF n-gram 和离线 hashed-vector index 初版 |
| 端到端更新工作流 | 一条命令串联扫描、TM、术语候选审校包、lore index、候选翻译、QA 和 summary 产物 | 已完成 `workflow run` CLI，可从 Localize checkout/base/head 自动准备 changed-files 和 source-baseline；已完成 `workflow finalize`，可在人审后生成发布候选目录、状态报告、QA 报告和 summary；正式上线仍需要人工审校与真实 provider 门禁 |
| 同结构输出 | 生成目标 JSON 树，保持原始路径和 JSON path | 已完成候选翻译输出、reviewed state 应用输出和 finalize 发布候选输出；可在人工审校后生成只包含确认译文的同结构发布候选目录 |
| 数据 adapter | 按文件类型区分可见文本、内部 ID、特殊主键 | 已完成 scan policy 配置层和 `dataList.id` 主键对齐初版；仍需按更多真实文件类型扩充规则库 |
| 审校状态 | 维护 `new` / `reviewed` / `locked`，避免覆盖人工定稿 | 已完成初版；翻译 review pack 可回写 reviewed / locked state，`state apply` 可把审校译文写回最终 JSON 树，`state status --fail-if-pending` 和 `workflow finalize --fail-if-pending` 可做发布前审校门禁 |
| 自动 QA | 占位符、标签、数字、术语命中、简繁、长度检查和 MQM 风格分类 | 已完成初版；路径/risk 字符级 length policy 和估算显示宽度已完成，像素级 UI 容器测量未完成 |
| Gold set / 模型评估 | 用固定样本评估 provider 翻译质量、成本和 prompt 变更风险 | 已完成从参考译文构建 gold set、分层采样、人工审校回写、单 provider eval report、多 provider compare report、eval candidate cache 和带响应 metadata / usage summary 的 eval request log 初版；真实模型赛马未完成 |
| 翻译记忆 / RAG | 句段复用、相似上下文、世界观资料检索 | exact-match TM、基础 fuzzy TM、基于 curated gold 的 TM 召回评估和离线 lore index 已完成；外部 embedding 向量库未完成，fuzzy 阈值仍需真实 curated gold 调参 |

## 当前不做

| 范围 | 说明 |
|---|---|
| 无审校直接上线 | 自动译文必须经过 QA 和人审门槛 |
| 单一模型押注 | 不把任何模型视为永久最优，模型需要通过项目 gold set 赛马 |
| 破坏上游格式 | 不改变 JSON 结构、占位符、标签、换行语义 |
| 从头全量重翻 | 不用模型重写 GitHub `LLC_zh-CN` 已有中文；已有译文只作为 TM、gold set、旧译文修订参考或邻近上下文 |
| 直接覆盖已锁定译文 | 自动翻译必须尊重 reviewed / locked 状态，避免覆盖人工定稿 |

## 用户故事

1. 作为维护者，我希望给定 LocalizeLimbusCompany checkout 后，一条命令以 `LLC_zh-CN` 为目标基线输出新增待译文本列表。
2. 作为翻译者，我希望每条候选译文都带相关术语、上下文路径和源文位置。
3. 作为审校者，我希望工具能标出术语不一致、占位符破坏、标签丢失和疑似漏译。
4. 作为开发者，我希望在没有模型 API key 时也能通过 dry-run 验证扫描和输出链路。
5. 作为项目维护者，我希望 Paratranz 术语库能被缓存，并在 API 不可用时用导出文件兜底。
6. 作为术语维护者，我希望新增候选先被自动分流，减少人工从整句和普通短语里筛术语的成本。
7. 作为术语维护者，我希望自动提炼结果能导出为可审校表格和 Paratranz 候选导入文件，而不是直接污染正式术语库。
8. 作为术语维护者，我希望已审校通过的表格能被工具重新导入为本地术语缓存，后续翻译自动使用。
9. 作为模型评估维护者，我希望自动抽样的 gold set 能导出给人工确认，并把确认后的样本回写为 curated gold，避免未审样本污染模型赛马结果。
10. 作为维护者，我希望扫描规则能通过配置按文件、路径和内容过滤噪声，而不是每次发现内部字段都修改代码。
11. 作为维护者，我希望每次上游更新后可以直接用 git diff 文件清单收敛扫描范围，而不是反复全量扫描和人工筛选无关文件。
12. 作为维护者，我希望一次上游更新能用一条命令产出待译单元、候选输出、QA 报告和 summary，便于交给审校继续处理。
13. 作为审校者，我希望候选译文、源文、QA 问题和可修订译文在同一张表里，并能把确认结果回写为后续自动翻译不会覆盖的状态。
14. 作为维护者，我希望每次使用 Paratranz 术语库前能自动发现空译名、多译名冲突和韩文残留，避免低质量术语污染模型上下文。
15. 作为开发者，我希望真实模型调用结果能缓存，并能追踪每条译文来自人工 state、TM、候选缓存还是 provider，便于复盘和控制成本。
16. 作为维护者，我希望上游 RAW 更新后只扫描真正新增或变化的源文路径，并把已有旧译文的源文变化标记出来，避免同文件内无关字段造成审校噪声。
17. 作为开发者，我希望真实模型调用的 source、glossary 和 context 能落盘，便于复现 prompt、审计成本和排查异常译文。
18. 作为模型评估维护者，我希望 Qwen-MT / DashScope 这类 OpenAI-compatible Chat 端点能用同一套 provider、cache、request log、trace 和 `eval compare` 接入，而不是另起一条不可回归链路。
19. 作为维护者，我希望人工审校完成后能用一条命令生成最终发布候选、状态报告、QA 报告和门禁 summary，而不是手工串多个命令。
20. 作为维护者，我希望工具保留 GitHub 已有中文，只对缺失、空值、仍韩文或 `source_changed` 的 JSON path 生成候选和 patch，避免把成熟译文重新洗一遍。
