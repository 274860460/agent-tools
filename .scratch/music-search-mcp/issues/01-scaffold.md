# 01: music-search-mcp 脚手架：可运行的空 MCP Server

**What to build:** 新建 `mcp/music-search-mcp` 包，结构完全仿照 `mcp/ops-mcp`（pyproject.toml 用 hatchling + `mcp[cli]<2`，`src/music_search/` 下放 `server.py`、`cli.py`、`tools/`）。CLI 只提供 `music-search help` 和 `music-search serve`（默认无参数时显示帮助）：`serve` 启动 FastMCP server，并暴露一个 `ping` 工具用于验证骨架可跑通。不做 install/uninstall 等客户端注册逻辑——`music-search help` 中直接输出一段 MCP server 配置 JSON（`mcpServers` 条目，command 指向已安装的 `music-search`），由用户自行粘贴到自己的 AI 客户端配置中。此阶段不包含任何真实搜索逻辑。

**Blocked by:** None (can start immediately)

**Status:** done

- [x] `uv tool install --force mcp/music-search-mcp` 安装成功，`music-search help` 输出帮助
- [x] `music-search help` 输出中包含一段可直接粘贴的 MCP server 配置（`mcpServers` 条目，command/args 指向 `music-search serve`）
- [x] `music-search serve` 启动后，MCP 客户端能列出并调用 `ping` 工具
- [x] 包结构（目录布局、入口脚本名、CLI 交互风格）与 ops-mcp 保持一致
