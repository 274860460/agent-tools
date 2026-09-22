# Handoff: music-search-mcp（音乐搜索/下载 MCP 工具）

日期：2026-09-21
工作目录：`/Users/ye.ridong/Code/agent-tools`

## 背景与目标

用户要做一个音乐搜索/下载 MCP Server（`mcp/music-search-mcp`），结构仿照同仓库的 `mcp/ops-mcp`。需求已全部拆成 ticket，发布在**本地 markdown tracker**，尚未开始实现。下一步会话的任务：按依赖顺序执行这 6 个 ticket（frontier 是 01）。

## 必读 artifacts（不要重复造这些文档的内容，直接读）

- **Ticket 列表（6 个，编号即依赖顺序）**：`.scratch/music-search-mcp/issues/`
  - `01-scaffold.md` — 脚手架：包结构 + CLI（仅 `help`/`serve`，无 install/uninstall；help 里输出一段可粘贴的 MCP server 配置 JSON）+ `ping` 工具。**无阻塞，从这里开始。**
  - `02-music-search-tool.md` — `music_search` 工具（POST 表单，参考 `1.txt`；解析响应为精简列表）
  - `03-download-link-tool.md` — `get_download_url` 工具（参考 `2.txt`；只返回 `data.url`）
  - `04-readme-e2e.md` — README + 端到端验证
  - `05-download-file-tool.md` — `download_file` 工具（流式落盘）
  - `06-music-download-skill.md` — `skills/music-download/SKILL.md`，串起完整链路
- **接口参考报文（含敏感 session cookie，勿外泄）**：仓库根目录 `1.txt`（搜索 POST）、`2.txt`（下载链接 POST）
- **真实响应样例**：`r1.json`（搜索返回，每项含 `id`/`time`/`sign`/`minfo`）、`r2.json`（下载链接返回，`data.url`）
- **结构参照**：`mcp/ops-mcp/`（pyproject 用 hatchling + `mcp[cli]<2`，`src/<pkg>/{server,cli,config,tools}` 布局）
- **skill 结构参照**：`skills/smoke/SKILL.md`（frontmatter + `$ARGUMENTS` + 分步流程）

## 已确认的关键决策（来自多轮用户确认）

- 项目名 `music-search-mcp`，包名 `music_search`，CLI 命令 `music-search`
- 工具命名：`music_search`（不叫 web_search）、`get_download_url`、`download_file`、`ping`
- **data 字段全部工具参数化**；cookie（curl `-b`）支持 `cookie` 参数，缺省读环境变量 `SEARCH_COOKIE`
- URL 解析：`url` 参数 → `SEARCH_URL`（下载链接工具先试 `SEARCH_DOWNLOAD_URL`）；`save_dir`：参数 → `MUSIC_DOWNLOAD_DIR` → `~/Downloads`
- **`sign` 与 `time` 来自 `music_search` 结果项的 `sign`/`time`，原样传递（绑定关系，禁止用当前时间戳兜底）**；`songid` ← 结果项 `id`；`format`/`bitrate` ← 用户所选 `minfo` 音质
- `get_download_url` 成功时**只返回** `r2.json` 的 `data.url`
- 不做自动客户端注册，只输出配置 JSON 让用户粘贴
- 沟通语言：简体中文（全局 AGENTS.md 要求）

## 执行提示

- 依赖链：01 → 02 → 03 → {04, 05} → 06；03 完成后 04/05 可并行，06 依赖 05
- 完成一个 ticket 就把对应 `.md` 的 Status 改为 done 并勾掉验收项
- ticket 04 的"真实 MCP 客户端端到端验证"需要用户配合（配置真实 URL/cookie 环境变量、接入客户端），到时先问用户拿真实接口地址（`1.txt`/`2.txt` 中是 example.com 占位符）

## Suggested skills

- **to-tickets**：若 ticket 需要再拆分/调整，重新调用该 skill（tracker 已配置为本地文件，`.scratch/music-search-mcp/issues/`）
- 执行 ticket 本身不需要其他特定 skill；如需代码审查可调用 **code-review**
