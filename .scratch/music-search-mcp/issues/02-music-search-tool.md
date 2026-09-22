# 02: music_search 工具：POST 表单搜索，data 字段与 cookie 均可传参

**What to build:** 在 server 上注册 `music_search` 工具，行为等价于参考 curl（仓库根目录 `1.txt`）：向目标 URL 发 POST 表单请求，请求头按 `1.txt` 原样携带（UA、sec-ch-*、accept-language 等），`content-type` 为 `application/x-www-form-urlencoded`。`--data-raw` 的各字段作为工具参数传入：`platform`（默认 kuwo）、`keyword`（必填）、`page`（默认 1）、`size`（默认 20）。cookie（curl 中的 `-b`）也可通过 `cookie` 参数传入；未传时读环境变量 `SEARCH_COOKIE` 兜底。目标 URL 同样支持 `url` 参数，未传时读环境变量 `SEARCH_URL`；两者都没有时返回明确错误提示。工具解析响应 JSON（结构见 `r1.json`），把 `data.list` 整理成精简列表返回——每项保留 `id`、`name`、`artist`、`album_name`、`duration`、`minfo`（可用音质列表）、`time`、`sign`，并附 `total`；超长时截断保护；网络错误返回可读的错误信息而不是抛异常。返回中需提示：`id`/`time`/`sign` 可直接传给 `get_download_url`。

**Blocked by:** 01: music-search-mcp 脚手架：可安装、可注册的空 MCP Server

**Status:** done

- [x] 调用 `music_search(keyword="陈一发儿")`（其余默认）能发出与 `1.txt` 等价的请求并返回结果列表
- [x] 返回的每项包含 `id`、`name`、`artist`、`minfo`、`time`、`sign`（字段名与 `r1.json` 对应），并附 `total`；响应非 JSON 或 `code != 0` 时返回原始文本与可读提示
- [x] `platform`、`page`、`size` 均可覆盖，且正确拼进表单 body
- [x] `cookie` 参数优先于 `SEARCH_COOKIE`；`url` 参数优先于 `SEARCH_URL`；都缺省时返回明确的配置指引
- [x] 响应文本有长度截断保护；连接失败/超时时返回可读错误而非堆栈
