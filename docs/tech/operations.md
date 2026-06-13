# Operations

本文档维护本地操作、验证命令和后续自动化方向。

## 本地命令

```bash
make validate-docs
make test
make smoke
make sync-glossary
rg "TODO|待确认|阻塞" docs
```

## CLI 命令

```bash
git -C /path/to/LocalizeLimbusCompany diff --name-only HEAD~1 HEAD > build/changed-files.txt

python3 -m limbus_translate.cli scan \
  --source /path/to/LocalizeLimbusCompany/KR \
  --target /path/to/LocalizeLimbusCompany/LLC_zh-CN \
  --output build/missing-units.json \
  --scan-policy config/scan-policy.sample.json \
  --changed-files build/changed-files.txt

python3 -m limbus_translate.cli glossary sync-paratranz \
  --project-id 6860 \
  --output cache/glossary/paratranz-6860.json

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
  --changed-files build/changed-files.txt \
  --glossary cache/glossary/paratranz-6860.json \
  --lore-input docs/lore \
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
  --output build/LLC_zh-CN \
  --provider dry-run

python3 -m limbus_translate.cli qa \
  --units build/missing-units.json \
  --output-root build/LLC_zh-CN \
  --glossary cache/glossary/paratranz-6860.json \
  --report build/qa-report.json \
  --length-policy config/length-policy.sample.json

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

python3 -m limbus_translate.cli eval run \
  --gold cache/eval/gold-curated.json \
  --provider dry-run \
  --report build/eval-report.json

python3 -m limbus_translate.cli eval compare \
  --gold cache/eval/gold-curated.json \
  --provider baseline=dry-run \
  --provider gpt41=openai:gpt-4.1 \
  --report build/eval-compare-report.json

python3 -m limbus_translate.cli terms extract \
  --units build/missing-units.json \
  --glossary cache/glossary/paratranz-6860.json \
  --output cache/terms/candidates.json

python3 -m limbus_translate.cli terms refine \
  --candidates cache/terms/candidates.json \
  --output cache/terms/refined.json \
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

`terms refine --provider openai` 可用于正式术语初筛和建议译名，但它依赖 OpenAI 可选依赖与 API key；输出仍应进入人工审校，不直接写入正式 termbase。

`scan --scan-policy` 接受 JSON 策略文件，当前示例为 `config/scan-policy.sample.json`。规则按顺序匹配，支持 `include` / `exclude` 两种 action，并可按 `relative_file`、`relative_file_prefix`、`json_path`、`json_path_suffix`、`key`、`source_contains` 过滤。`include` 可把非默认文本 key 纳入扫描并可覆盖 `risk`；`exclude` 用于过滤内部事件名、占位文案、无用文本或特定文件类型的噪声。不传该参数时扫描行为保持内置默认。

`scan --changed-files` 接受 `git diff --name-only` 生成的换行分隔文件清单，只扫描涉及的 JSON 相对文件。路径可以是仓库根目录形式的 `KR/Foo.json` / `LLC_zh-CN/Foo.json`，也可以是语言目录内的 `Foo.json`；非 JSON 文件会被忽略。该参数用于 RAW/GTP 更新后把扫描范围收敛到本次变更，减少全量扫描和人工审查成本。

`workflow run` 是一次上游更新的默认串联入口：先按 scan policy 和 changed-files 生成 `missing-units.json`，再构建 `tm.json`，对本次新增文本输出 `term-candidates.json`、`refined-terms.json` 和 `term-review/` 审校包，可选导入 `--lore-input` 并生成离线 `lore-index.json`，随后 overlay 现有目标树、执行翻译、运行 QA，最后写出 `summary.json`。`--terms-provider` 默认 `rules`，可切到 `openai`；`--skip-terms` 可跳过术语步骤；`--lore` / `--lore-index` 可复用已有缓存；`--lore-input` 用于把本地笔记目录作为本次工作目录内的可追踪产物重新导入。`--fail-on-error` 可把 QA error 作为命令失败，warning 不会失败。

`terms review-pack` 会从 refined cache 生成 `review.csv`、`review.jsonl` 和 `paratranz-import.csv`。`review.csv` 面向人工审校，保留空白 `approved` 列；`review.jsonl` 保留完整结构化证据；`paratranz-import.csv` 只包含 `decision=term` 且已有 `suggested_target` 的候选，作为平台导入前的审校材料。

`terms apply-review` 会读取审校后的 `review.csv`，只把 `approved` 为 `yes` / `true` / `1` / `通过` 等明确确认值且 `target` 非空的行写入本地 glossary cache。未确认、空译名和被留空的候选会被跳过。

`terms promote` 只导出 `decision=term` 且存在 `suggested_target` 的记录；`needs_review` 不会进入正式术语缓存。

`qa --length-policy` 接受 JSON 策略文件，按路径、文件前缀、JSON path 后缀或 risk 覆盖字符级长度阈值，并可用 `max_display_width` 按 East Asian Width 估算可见文本宽度。估算会忽略富文本标签，但不替代真实 UI 像素测量。

`lore import` 接受 Markdown、JSON、JSONL、CSV、TXT 或目录输入，输出统一 `LoreEntry[]` cache。Markdown 会按一级到三级标题切分条目，并从 `关键词:` / `anchors:` 等行提取召回锚点。`lore index` 会把 cache 编译为离线 hashed-vector sparse index；`lore search` 可独立验证召回结果；`translate --lore-index` 会优先用索引向 provider context 注入 lore 片段。当前索引是可离线验证的工程接口，不是外部 embedding 服务或专用向量数据库。

`eval build-gold` 从已有 `KR` / `LLC_zh-CN` 参考译文中抽取 gold set，跳过空译文、同源残留和仍含韩文的目标文本；可用 `--limit` 控制规模。`eval sample-gold` 可按 `tag`、`risk` 或 `file` 分层抽样，支持固定 `--seed` 和 `--per-group`，用于构建更均衡的模型赛马样本。`eval review-pack` 导出人工审校 CSV 和结构化 JSONL；`eval apply-review` 只接收 `approved` 明确为真的行，并依赖原始 gold set 保留 glossary / context / tags 后写出 curated gold。`eval run` 接受 gold set JSON，调用指定 provider 并输出相似度、格式一致性、术语缺失和 pass rate。`eval compare` 接受多个 `--provider label=spec`，输出每个 provider 的完整评估结果和按 pass rate / similarity 排序的 ranking；provider spec 支持 `dry-run`、`openai` 和 `openai:<model>`。`--fail-under` 可作为 CI 门禁；自动抽取和分层采样的 gold set 必须先经人工审校，curated gold 的覆盖范围仍决定模型评估可信度。

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
