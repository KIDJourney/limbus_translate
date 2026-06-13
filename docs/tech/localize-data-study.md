# LocalizeLimbusCompany 数据研究

AS_OF: 2026-06-13

## 仓库状态

- 仓库：https://github.com/LocalizeLimbusCompany/LocalizeLimbusCompany
- 默认分支：`main`
- 抽样 HEAD：`9184302e785805924807919587cd5264186b19eb`
- 最新公开 release 抽样：`2026060701`

## 目录结构

| 目录 | 含义 |
|---|---|
| `KR/` | 韩文原始资源，当前抽样约 2003 个 JSON |
| `EN/` | 英文资源，当前抽样约 2020 个 JSON |
| `JP/` | 日文资源 |
| `LLC_zh-CN/` | 简体中文语言包，当前抽样约 1992 个 JSON |
| `Fonts/` | 字体资源 |
| `.github/workflows/` | Issue 自动处理、MirrorChyan 发布/字体上传 |

## 对齐方式

主要对齐规则是“相同相对路径 + JSON 结构 + 记录 id / 数组位置 + 文本字段”。典型 JSON 为：

```json
{
  "dataList": [
    {
      "id": 877401,
      "name": "...",
      "desc": "...",
      "options": [
        {
          "message": "...",
          "result": ["..."]
        }
      ]
    }
  ]
}
```

当前工具优先按相对文件和 JSON path 对齐；当 `dataList[*].id` 是唯一且不是 `-1` 时，会用该 id 解析目标侧实际数组位置，避免数组插入导致路径漂移。`StoryData` 中大量记录使用 `id=-1`，这类 id 不可作为稳定主键，工具会自动回退到 JSON path。

## Commit 模式

| Commit | 类型 | 观察 |
|---|---|---|
| `9184302` | `Auto RAW Update` | 只重命名 `JP/Voice_Faust_ShiAsso2_10213.json`，说明 RAW 更新不一定涉及韩文或中文 |
| `3d0a480` | `Auto GTP Update` | 只改 `LLC_zh-CN/BattleSpeechBubbleDlg.json`，`+7/-7`，属于小规模译文修正 |
| `8279409` | `Auto RAW Update` | 批量改 `EN/JP/KR`，体现上游原始文本同步 |
| `cef3d33` | `Auto GTP Update` | 批量改中文文件，可视为 RAW 后翻译落地 |
| `f216577` | 文档维护 | README 更新，不属于翻译数据更新 |

## 当前扫描结果

在本机临时 checkout 上执行：

```bash
python3 -m limbus_translate.cli scan \
  --source /tmp/limbus-translate-work/LocalizeLimbusCompany/KR \
  --target /tmp/limbus-translate-work/LocalizeLimbusCompany/LLC_zh-CN \
  --output /tmp/limbus-real-missing.json
```

结果：

```text
scan complete: 19 units -> /tmp/limbus-real-missing-v4.json
{"target_same_as_source": 19}
```

默认扫描已经过滤同源残留里的内部事件名、显示占位、无用 `subDesc`、战斗气泡元数据等噪声。剩余 19 条全部是 `StoryData/*.content` 高风险剧情/演出文本，仍需要人工判断哪些是要翻译的可见文本、哪些是演出指令。使用 `--include-internal` 可审计完整 263 条同源残留。

## Paratranz 术语源

- 项目页：https://paratranz.cn/projects/6860/terms
- 项目 API：https://paratranz.cn/api/projects/6860
- 术语 API：https://paratranz.cn/api/projects/6860/terms?page=1&pageSize=3
- 当前抽样结果：术语约 1963，`source` 为 `ko`，`dest` 为 `zh-cn`

工具主路径使用分页 JSON API 同步术语，artifact/download 需要登录，不作为默认依赖。
