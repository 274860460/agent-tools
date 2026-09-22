# 03: get_download_url 工具：查询歌曲下载链接

**What to build:** 在 server 上注册 `get_download_url` 工具，行为等价于参考 curl（仓库根目录 `2.txt`）：POST 表单请求，请求头与 cookie 处理和 `music_search` 完全共用（02 中建好的请求辅助逻辑，包括 UA/sec-ch-* 等 header 集、`cookie` 参数优先于 `SEARCH_COOKIE` 的解析）。`--data-raw` 的各字段作为工具参数传入：`platform`（默认 kuwo）、`songid`（必填）、`format`（默认 mp3）、`bitrate`（默认 320）、`time`（必填）、`sign`（必填）。**`songid`、`time`、`sign` 三者都从 `music_search` 的搜索结果项原样取用**（对应 `r1.json` 中每项的 `id`、`time`、`sign`——`sign` 与该 `time` 绑定，不能用当前时间戳代替）；`format`/`bitrate` 按用户选择的音质传，可取搜索项 `minfo` 中列出的组合（如 mp3/320、flac/817）。典型流程：先调 `music_search`，从结果中选中歌曲和音质，把该项的 `id`/`time`/`sign` 及所选 `format`/`bitrate` 传给本工具；工具的 docstring 和 server instructions 里要写清这个两步流程和字段映射，引导调用方不要自己编造 sign 或 time。目标 URL 解析顺序：`url` 参数 → 环境变量 `SEARCH_DOWNLOAD_URL` → 环境变量 `SEARCH_URL`；都没有时返回明确错误提示。解析响应 JSON（结构见 `r2.json`），只返回 `data.url` 下载链接；`code != 0` 或缺少 `url` 时返回 `msg` 和可读的失败提示。

**Blocked by:** 02: music_search 工具：POST 表单搜索，data 字段与 cookie 均可传参

**Status:** done

- [x] 典型流程可跑通：`music_search(keyword=...)` 返回结果项的 `id`/`time`/`sign`，原样传给 `get_download_url` 能发出与 `2.txt` 等价的请求
- [x] 成功时只返回 `r2.json` 中 `data.url` 的下载链接；`code != 0` 或缺少 `url` 时返回 `msg` 及可读失败提示
- [x] `platform`、`format`、`bitrate` 均可覆盖；`time` 为必填，不做时间戳兜底
- [x] 工具 docstring / server instructions 明确说明字段映射：`songid←id`、`time←time`、`sign←sign`、`format`/`bitrate←minfo` 中所选音质
- [x] 与 `music_search` 共用同一套 header 构造、cookie 解析和错误处理，无重复实现
- [x] URL 按 参数 → `SEARCH_DOWNLOAD_URL` → `SEARCH_URL` 顺序解析，缺省时返回明确配置指引
