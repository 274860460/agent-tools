# 04: README 与端到端验证

**What to build:** 为 `mcp/music-search-mcp` 编写 README，格式仿照 `mcp/ops-mcp/README.md`：项目简介、`uv tool install` 安装/卸载命令、CLI 子命令说明、MCP 工具表格（`ping`、`music_search`、`get_download_url`、`download_file` 及各参数说明）、`SEARCH_COOKIE` / `SEARCH_URL` / `SEARCH_DOWNLOAD_URL` / `MUSIC_DOWNLOAD_DIR` 环境变量配置方式，以及一段可直接粘贴到 AI 客户端的 MCP server 配置 JSON。随后做端到端验证：安装到本机 → 把配置 JSON 粘贴到某个 MCP 客户端 → 在该客户端中走通完整链路。

**Blocked by:** 02: music_search 工具；03: get_download_url 工具；05: download_file 工具

**Status:** in-progress（README 已完成；真实客户端端到端验证待用户配合，需真实接口地址与 cookie）

- [x] README 覆盖安装、CLI 用法、工具参数表、环境变量说明、MCP server 配置 JSON 示例，风格与 ops-mcp README 一致
- [x] `uv tool install --force mcp/music-search-mcp` 后，按 README 中的配置 JSON 可手动接入客户端
- [ ] 在真实 MCP 客户端中走通完整流程：`music_search` 搜索 → 从结果取 `id`/`time`/`sign` → `get_download_url` 拿到下载链接 → `download_file` 保存成本地可播放文件
