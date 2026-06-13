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
python3 -m limbus_translate.cli scan \
  --source /path/to/LocalizeLimbusCompany/KR \
  --target /path/to/LocalizeLimbusCompany/LLC_zh-CN \
  --output build/missing-units.json

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

python3 -m limbus_translate.cli translate \
  --source /path/to/LocalizeLimbusCompany/KR \
  --target /path/to/LocalizeLimbusCompany/LLC_zh-CN \
  --units build/missing-units.json \
  --glossary cache/glossary/paratranz-6860.json \
  --memory cache/tm/exact.json \
  --state cache/state/units.json \
  --output build/LLC_zh-CN \
  --provider dry-run

python3 -m limbus_translate.cli qa \
  --units build/missing-units.json \
  --output-root build/LLC_zh-CN \
  --glossary cache/glossary/paratranz-6860.json \
  --report build/qa-report.json

python3 -m limbus_translate.cli terms extract \
  --units build/missing-units.json \
  --glossary cache/glossary/paratranz-6860.json \
  --output cache/terms/candidates.json

python3 -m limbus_translate.cli terms refine \
  --candidates cache/terms/candidates.json \
  --output cache/terms/refined.json \
  --provider rules

python3 -m limbus_translate.cli terms promote \
  --refined cache/terms/refined.json \
  --output cache/glossary/local-refined.json \
  --merge cache/glossary/paratranz-6860.json
```

`terms refine --provider openai` 可用于正式术语初筛和建议译名，但它依赖 OpenAI 可选依赖与 API key；输出仍应进入人工审校，不直接写入正式 termbase。

`terms promote` 只导出 `decision=term` 且存在 `suggested_target` 的记录；`needs_review` 不会进入正式术语缓存。

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
