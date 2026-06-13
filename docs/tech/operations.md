# Operations

本文档维护本地操作、验证命令和后续自动化方向。

## 本地命令

```bash
make validate-docs
make test
make smoke
make sync-glossary
PROVIDER=qwen-mt make check-provider-env
rg "TODO|待确认|阻塞" docs
```

## CLI 命令

```bash
python3 -m limbus_translate.cli localize prepare-update \
  --repo /path/to/LocalizeLimbusCompany \
  --base HEAD~1 \
  --head HEAD \
  --work-dir build/localize-update

python3 -m limbus_translate.cli scan \
  --source /path/to/LocalizeLimbusCompany/KR \
  --target /path/to/LocalizeLimbusCompany/LLC_zh-CN \
  --output build/missing-units.json \
  --scan-policy config/scan-policy.sample.json \
  --changed-files build/localize-update/changed-files.txt \
  --source-baseline build/localize-update/source-baseline/KR

python3 -m limbus_translate.cli glossary sync-paratranz \
  --project-id 6860 \
  --output cache/glossary/paratranz-6860.json

python3 -m limbus_translate.cli glossary audit \
  --input cache/glossary/paratranz-6860.json \
  --report build/glossary-audit.json \
  --fail-on error

python3 -m limbus_translate.cli glossary merge \
  --input cache/glossary/paratranz-6860.json \
  --input cache/glossary/local-reviewed.json \
  --output cache/glossary/active.json

python3 -m limbus_translate.cli tm build \
  --source /path/to/LocalizeLimbusCompany/KR \
  --target /path/to/LocalizeLimbusCompany/LLC_zh-CN \
  --output cache/tm/exact.json

python3 -m limbus_translate.cli state init \
  --units build/missing-units.json \
  --output cache/state/units.json

python3 -m limbus_translate.cli lore import \
  --input docs/lore \
  --output cache/lore/world.json

python3 -m limbus_translate.cli lore index \
  --lore cache/lore/world.json \
  --output cache/lore/world-index.json

python3 -m limbus_translate.cli lore search \
  --index cache/lore/world-index.json \
  --query "단테가 전투를 지휘한다" \
  --output build/lore-search.json

python3 -m limbus_translate.cli workflow run \
  --source /path/to/LocalizeLimbusCompany/KR \
  --target /path/to/LocalizeLimbusCompany/LLC_zh-CN \
  --output build/LLC_zh-CN \
  --work-dir build/workflow \
  --scan-policy config/scan-policy.sample.json \
  --localize-repo /path/to/LocalizeLimbusCompany \
  --localize-base HEAD~1 \
  --localize-head HEAD \
  --glossary cache/glossary/paratranz-6860.json \
  --lore-input docs/lore \
  --terms-cache cache/terms/refined-cache.json \
  --length-policy config/length-policy.sample.json \
  --provider dry-run

python3 -m limbus_translate.cli translate \
  --source /path/to/LocalizeLimbusCompany/KR \
  --target /path/to/LocalizeLimbusCompany/LLC_zh-CN \
  --units build/missing-units.json \
  --glossary cache/glossary/paratranz-6860.json \
  --memory cache/tm/exact.json \
  --lore cache/lore/world.json \
  --lore-index cache/lore/world-index.json \
  --state cache/state/units.json \
  --candidate-cache cache/translation/candidates.json \
  --request-log build/translation-requests.jsonl \
  --trace build/translation-trace.jsonl \
  --output build/LLC_zh-CN \
  --provider dry-run

python3 -m limbus_translate.cli qa \
  --units build/missing-units.json \
  --output-root build/LLC_zh-CN \
  --glossary cache/glossary/paratranz-6860.json \
  --report build/qa-report.json \
  --length-policy config/length-policy.sample.json

python3 -m limbus_translate.cli review pack \
  --units build/missing-units.json \
  --output-root build/LLC_zh-CN \
  --qa-report build/qa-report.json \
  --output-dir build/translation-review

python3 -m limbus_translate.cli review apply \
  --review build/translation-review/review.csv \
  --output cache/state/reviewed.json \
  --merge cache/state/units.json

python3 -m limbus_translate.cli eval build-gold \
  --source /path/to/LocalizeLimbusCompany/KR \
  --target /path/to/LocalizeLimbusCompany/LLC_zh-CN \
  --glossary cache/glossary/paratranz-6860.json \
  --output cache/eval/gold-set.json \
  --limit 1000

python3 -m limbus_translate.cli eval sample-gold \
  --gold cache/eval/gold-set.json \
  --output cache/eval/gold-sample.json \
  --per-group 20 \
  --group-by tag \
  --seed 7

python3 -m limbus_translate.cli eval review-pack \
  --gold cache/eval/gold-sample.json \
  --output-dir build/gold-review

python3 -m limbus_translate.cli eval apply-review \
  --gold cache/eval/gold-sample.json \
  --review build/gold-review/review.csv \
  --output cache/eval/gold-curated.json

python3 -m limbus_translate.cli state apply \
  --source /path/to/LocalizeLimbusCompany/KR \
  --target /path/to/LocalizeLimbusCompany/LLC_zh-CN \
  --units build/missing-units.json \
  --state cache/state/reviewed.json \
  --output build/LLC_zh-CN-reviewed

python3 -m limbus_translate.cli state status \
  --units build/missing-units.json \
  --state cache/state/reviewed.json \
  --report build/state-status.json \
  --fail-if-pending

python3 -m limbus_translate.cli workflow finalize \
  --source /path/to/LocalizeLimbusCompany/KR \
  --target /path/to/LocalizeLimbusCompany/LLC_zh-CN \
  --units build/missing-units.json \
  --state cache/state/reviewed.json \
  --output build/LLC_zh-CN-reviewed \
  --work-dir build/finalize \
  --glossary cache/glossary/active.json \
  --length-policy config/length-policy.sample.json \
  --localize-repo /path/to/LocalizeLimbusCompany \
  --patch-output build/localize-translation.patch \
  --fail-if-pending \
  --fail-on-error

python3 -m limbus_translate.cli localize make-patch \
  --repo /path/to/LocalizeLimbusCompany \
  --units build/missing-units.json \
  --state cache/state/reviewed.json \
  --output build/localize-translation.patch

python3 -m limbus_translate.cli tm evaluate \
  --memory cache/tm/exact.json \
  --gold cache/eval/gold-curated.json \
  --report build/tm-eval-report.json \
  --min-similarity 0.35 \
  --thresholds 0.35,0.5,0.7

python3 -m limbus_translate.cli eval run \
  --gold cache/eval/gold-curated.json \
  --provider dry-run \
  --candidate-cache cache/eval/candidates.json \
  --request-log build/eval-requests.jsonl \
  --report build/eval-report.json

python3 -m limbus_translate.cli eval compare \
  --gold cache/eval/gold-curated.json \
  --provider baseline=dry-run \
  --provider gpt41=openai:gpt-4.1 \
  --provider qwen=qwen-mt:qwen-mt-plus \
  --candidate-cache cache/eval/candidates.json \
  --request-log build/eval-compare-requests.jsonl \
  --report build/eval-compare-report.json

python3 -m limbus_translate.cli terms extract \
  --units build/missing-units.json \
  --glossary cache/glossary/paratranz-6860.json \
  --output cache/terms/candidates.json

python3 -m limbus_translate.cli terms refine \
  --candidates cache/terms/candidates.json \
  --output cache/terms/refined.json \
  --cache cache/terms/refined-cache.json \
  --provider rules

python3 -m limbus_translate.cli terms review-pack \
  --refined cache/terms/refined.json \
  --output-dir build/term-review

python3 -m limbus_translate.cli terms apply-review \
  --review build/term-review/review.csv \
  --output cache/glossary/local-reviewed.json \
  --merge cache/glossary/paratranz-6860.json

python3 -m limbus_translate.cli terms promote \
  --refined cache/terms/refined.json \
  --output cache/glossary/local-refined.json \
  --merge cache/glossary/paratranz-6860.json
```

`terms refine --cache` 会读取并更新持久 refined cache。命中缓存的 source 不会再次调用 refiner，而是复用旧 decision、suggested target 和 note，同时刷新本轮 contexts、count 与 sample text；未命中的候选才交给 `rules` 或 `openai`。`terms refine --provider openai` 可用于正式术语初筛和建议译名，但它依赖 OpenAI 可选依赖与 API key；输出仍应进入人工审校，不直接写入正式 termbase。

`scan --scan-policy` 接受 JSON 策略文件，当前示例为 `config/scan-policy.sample.json`。规则按顺序匹配，支持 `include` / `exclude` 两种 action，并可按 `relative_file`、`relative_file_prefix`、`json_path`、`json_path_suffix`、`key`、`source_contains` 过滤。`include` 可把非默认文本 key 纳入扫描并可覆盖 `risk`；`exclude` 用于过滤内部事件名、占位文案、无用文本或特定文件类型的噪声。不传该参数时扫描行为保持内置默认。

`localize prepare-update` 从 LocalizeLimbusCompany checkout 的 `--base..--head` 自动生成 `changed-files.txt`，并用 `git archive` 把 `--base` 的 `KR` 目录导出为 `source-baseline/KR`，减少每次上游更新前的手工 git 命令。

`scan --changed-files` 接受 `git diff --name-only` 生成的换行分隔文件清单，只扫描涉及的 JSON 相对文件。路径可以是仓库根目录形式的 `KR/Foo.json` / `LLC_zh-CN/Foo.json`，也可以是语言目录内的 `Foo.json`；非 JSON 文件会被忽略。该参数用于 RAW/GTP 更新后把扫描范围收敛到本次变更，减少全量扫描和人工审查成本。

`scan --source-baseline` 接受上一个版本的 `KR` 目录，按 JSON path 和 `dataList[id=...]` 稳定键比较源文变化。传入后，scan 只处理新增或变化的源文路径；如果目标已有旧中文，会输出 `source_changed`，避免只靠“目标为空/目标仍是韩文”漏掉需要重译的旧译文。

`glossary audit` 会读取本地 glossary cache，检查空源文、空译名、同源多译名冲突、源文疑似非韩文、译文韩文残留、译文等于源文和重复 source/target pair。`--fail-on error` 可把严重术语问题作为自动化门禁；`--fail-on warning` 更适合正式发布前的人工清理阶段。

`glossary merge` 会把多个 glossary cache 合成一个 active glossary。输入按顺序处理，后面的 cache 覆盖前面同 `source_lang` / `target_lang` / Korean source 的术语；常用顺序是先放 Paratranz 官方缓存，再放本地人工审校术语或 promoted refined 术语。

`workflow run` 是一次上游更新的默认串联入口：如果传入 `--localize-repo`，会先按 `--localize-base..--localize-head` 在 `--work-dir/localize-update/` 下生成 `changed-files.txt` 和 `source-baseline/KR`；显式传入的 `--changed-files` 或 `--source-baseline` 会覆盖自动生成路径。随后 workflow 按 scan policy、changed-files 和可选 source-baseline 生成 `missing-units.json`，再构建 `tm.json`；如果传入 `--glossary`，会写出 `glossary-audit.json` 并在 summary 暴露术语库问题分布；随后对本次新增文本输出 `term-candidates.json`、`refined-terms.json` 和 `term-review/` 审校包，可选导入 `--lore-input` 并生成离线 `lore-index.json`，再 overlay 现有目标树、执行翻译、写出 `translation-candidates.json`、`translation-requests.jsonl` 与 `translation-trace.jsonl`、运行 QA、导出 `translation-review/`，最后写出 `summary.json`。`summary.localize_update` 会记录自动准备的 changed-files / source-baseline 路径和变更数量；`summary.translation_requests.usage` 会按总量、provider 和 response model 汇总 request log 中的 usage。`--candidate-cache` 可指向持久候选缓存；不传时使用工作目录内的 `translation-candidates.json`。`--terms-cache` 可指向持久 refined term cache，summary 会记录 existing、reused、added 和 total；`--terms-provider` 默认 `rules`，可切到 `openai`；`--skip-terms` 可跳过术语步骤；`--lore` / `--lore-index` 可复用已有缓存；`--lore-input` 用于把本地笔记目录作为本次工作目录内的可追踪产物重新导入。`--fail-on-error` 可把 QA error 作为命令失败，warning 不会失败。

`make prepare-current-localize-review` 是面向真实上游更新的审校包入口。它会 checkout `LOCALIZE_COMMIT`（默认 `origin/main`）、同步 Paratranz 术语、以 GitHub `LLC_zh-CN` 为目标基线扫描 gap units，然后运行 `workflow run` 产出 `build/current-review/missing-units.json`、术语候选和 `translation-review/review.csv`。默认 `PROVIDER=dry-run` 只用于打通流程；需要真实候选时可设 `PROVIDER=qwen-mt`、`PROVIDER=openai` 或其他 provider。真实 provider 首跑建议设置 `LIMIT=1` 控制成本，例如 `LIMIT=1 PROVIDER=qwen-mt make prepare-current-localize-review`。若需要只处理某次上游 diff，可设置 `LOCALIZE_BASE=<base-ref>`。

`make check-provider-env` 会检查真实 provider 运行前提，不调用外部 API，也不会输出密钥内容。`PROVIDER=qwen-mt` 需要安装 `openai` Python package，并设置 `DASHSCOPE_API_KEY` 或 `QWEN_API_KEY`；`PROVIDER=openai` 需要 `OPENAI_API_KEY`。预检通过后，可用 `PROVIDER=qwen-mt make prepare-current-localize-review` 生成真实模型候选审校包。

`make prepare-current-model-eval` 会 checkout 当前 LocalizeLimbusCompany、同步 Paratranz 术语，并从 GitHub `LLC_zh-CN` 现有中文译文构建 provider eval 的 gold set。它默认最多收集 `GOLD_LIMIT=1000` 条参考译文，按 `GOLD_GROUP_BY=tag` 每组抽 `GOLD_PER_GROUP=20` 条，输出 `build/current-model-eval/gold-set.json`、`gold-sample.json` 和 `gold-review/review.csv`。该命令不调用翻译 provider；审校者确认 `review.csv` 后，用 `eval apply-review` 生成 curated gold，再用 `eval compare` 做 qwen / openai 模型赛马。

`translate --candidate-cache` 会读取并更新 provider 候选缓存。缓存 key 绑定 provider、source hash、context hash 和 glossary hash，所以术语或 lore 上下文变化后不会误复用旧译文。`translate --request-log` 输出真正发给 provider 的 source、glossary、context、`target_text`、`response_model`、`response_id` 和 `usage`；state、TM 和 candidate cache 命中不会写入 request log。`translate --trace` 输出 JSONL，每行记录 `translation_source`，用于区分 state、TM、candidate cache 和 provider。

`review pack` 会把待译单元、当前候选输出和 QA issue 汇总成 `review.csv` / `review.jsonl`。审校者只需要填写 `approved`，必要时填写 `revised_target`；`review apply` 只接收明确 approved 且有译文的行，写成 `reviewed` / `locked` state，后续 `translate --state` 或 `workflow run --state` 会优先使用并保护这些译文。

`state apply` 会把已有 state 中带 `target_text` 的 reviewed / locked 单元写入同结构输出目录。它不会调用翻译 provider，也不会处理未审校单元；用于在 `review apply` 之后生成只包含人工确认译文的发布候选树。

`state status` 会按本次 `missing-units.json` 统计 reviewed / locked 且有译文的 ready 单元、pending 单元、缺失 state 和缺失 target_text。`--fail-if-pending` 会在仍有 pending 时返回失败码，可作为发布前自动门禁。

`workflow finalize` 会在不调用翻译 provider 的前提下，把 reviewed / locked state 应用到同结构输出树，再对最终输出运行 QA 和全输出可见韩文残留审计，并把 `state-status.json`、`qa-report.json` 和 `summary.json` 写入工作目录。它适合人工审校后的发布候选收口；`--fail-if-pending` 用于拦截未审校单元，`--fail-on-error` 用于把 QA error 变成失败码。

当前已审校的真实 LocalizeLimbusCompany 批次对应上游 commit `9184302e785805924807919587cd5264186b19eb`，reviewed state 已保存在 `data/state/localize-reviewed-9184302e.json`。清理 `build/` 后，可用 `make reproduce-current-localize` 重新 checkout、同步术语，并以 GitHub `LLC_zh-CN` 为目标基线只扫描未翻译或仍为韩文的缺口，用该 state 复现 22 条 reviewed 单元和可应用 patch。需要把本次真实翻译结果发布到仓库时，运行 `make publish-current-localize-artifact`；该命令会复现流程、生成 `artifacts/localize-9184302e/` 下的 patch、summary 和 translations，并对 Localize checkout 执行 `git apply --check`。

`terms review-pack` 会从 refined cache 生成 `review.csv`、`review.jsonl` 和 `paratranz-import.csv`。`review.csv` 面向人工审校，保留空白 `approved` 列；`review.jsonl` 保留完整结构化证据；`paratranz-import.csv` 只包含 `decision=term` 且已有 `suggested_target` 的候选，作为平台导入前的审校材料。

`terms apply-review` 会读取审校后的 `review.csv`，只把 `approved` 为 `yes` / `true` / `1` / `通过` 等明确确认值且 `target` 非空的行写入本地 glossary cache。未确认、空译名和被留空的候选会被跳过。

`terms promote` 只导出 `decision=term` 且存在 `suggested_target` 的记录；`needs_review` 不会进入正式术语缓存。

`qa --length-policy` 接受 JSON 策略文件，按路径、文件前缀、JSON path 后缀或 risk 覆盖字符级长度阈值，并可用 `max_display_width` 按 East Asian Width 估算可见文本宽度。估算会忽略富文本标签，但不替代真实 UI 像素测量。

`lore import` 接受 Markdown、JSON、JSONL、CSV、TXT 或目录输入，输出统一 `LoreEntry[]` cache。Markdown 会按一级到三级标题切分条目，并从 `关键词:` / `anchors:` 等行提取召回锚点。`lore index` 会把 cache 编译为离线 hashed-vector sparse index；`lore search` 可独立验证召回结果；`translate --lore-index` 会优先用索引向 provider context 注入 lore 片段。当前索引是可离线验证的工程接口，不是外部 embedding 服务或专用向量数据库。

`tm evaluate` 用 curated gold set 评估 fuzzy TM 召回，默认排除 exact source，输出每个 case 的 top-k 近似记忆、source similarity、target similarity，并在 summary 中给出覆盖率和 threshold sweep。正式调 `ContextBundle.memory_examples` 的相似度阈值前，应先用真实 curated gold 跑一次该报告。

`eval build-gold` 从已有 `KR` / `LLC_zh-CN` 参考译文中抽取 gold set，跳过空译文、同源残留和仍含韩文的目标文本；可用 `--limit` 控制规模。`eval sample-gold` 可按 `tag`、`risk` 或 `file` 分层抽样，支持固定 `--seed` 和 `--per-group`，用于构建更均衡的模型赛马样本。`eval review-pack` 导出人工审校 CSV 和结构化 JSONL；`eval apply-review` 只接收 `approved` 明确为真的行，并依赖原始 gold set 保留 glossary / context / tags 后写出 curated gold。`eval run` 接受 gold set JSON，调用指定 provider 并输出相似度、格式一致性、术语缺失和 pass rate。`eval compare` 接受多个 `--provider label=spec`，输出每个 provider 的完整评估结果和按 pass rate / similarity 排序的 ranking；provider spec 支持 `dry-run`、`openai`、`openai:<model>`、`openai-chat`、`openai-chat:<model>`、`qwen-mt` 和 `qwen-mt:<model>`。`eval run` / `eval compare` 的 `--candidate-cache` 读取并更新候选缓存，`--request-log` 只记录真实 provider 调用，并包含 `target_text`、响应 metadata 和 `usage`；启用 request log 时 report summary 会按总量、provider 和 response model 汇总 usage。cache key 使用 provider spec 而不是展示 label，所以同一模型在同一 compare 中换 label 不会重复请求。`--fail-under` 可作为 CI 门禁；自动抽取和分层采样的 gold set 必须先经人工审校，curated gold 的覆盖范围仍决定模型评估可信度。

`openai-chat` 使用 OpenAI-compatible Chat Completions，环境变量为 `OPENAI_COMPATIBLE_API_KEY`、`OPENAI_COMPATIBLE_BASE_URL` 和 `OPENAI_COMPATIBLE_MODEL`。`qwen-mt` 专门适配 Qwen-MT：默认模型 `qwen-mt-plus`，默认 base URL `https://dashscope.aliyuncs.com/compatible-mode/v1`，优先读取 `DASHSCOPE_API_KEY`，也支持 `QWEN_MT_API_KEY`、`DASHSCOPE_BASE_URL`、`QWEN_MT_BASE_URL` 和 `QWEN_MT_MODEL`。Qwen-MT provider 只发送一条 `user` message，并通过 `translation_options` 注入 `source_lang=Korean`、`target_lang=Chinese`、术语、TM 示例和领域提示；真实默认 provider 变更前必须跑 curated gold 的 `eval compare`。

## 文档验证

`scripts/validate-docs.sh` 当前做三类检查：

1. 关键入口文件是否存在。
2. 关键目录是否存在。
3. Markdown 相对链接是否能解析到本地文件。

这个脚本是最小门禁，不替代人工评审。后续可以扩展：

- 检查每个目录 README 是否索引了同目录 Markdown。
- 检查 `AGENTS.md` 的权威文档链接是否存在。
- 检查 PRD、设计方案、技术方案、测试方案和验证场景是否包含必填章节。
- 接入 CI，在 PR 合并前运行。

## 维护流程

1. 新增或修改需求：更新 `docs/product/`。
2. 设计、交互或 UI 变化：更新 `docs/design/`。
3. 设计实现方案：更新 `docs/tech/`。
4. 定义测试策略和测试用例：更新 `docs/test/`。
5. 定义或记录业务场景验证：更新 `docs/verification/`。
6. 记录长期上下文：更新 `docs/agent/`。
7. 执行 `make validate-docs`。
8. 在交接记录中写明修改内容、验证结果和遗留风险。
