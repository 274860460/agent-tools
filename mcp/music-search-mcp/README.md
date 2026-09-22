# music-search

音乐搜索/下载 MCP Server — 搜索歌曲、查询下载链接、流式下载到本地。

## 安装

```bash
# 安装
uv tool install --force --no-cache mcp/music-search-mcp

# 卸载
uv tool uninstall music-search
```

## 使用

```bash
music-search          # 显示帮助（含可粘贴的 MCP server 配置 JSON）
music-search help     # 同上
music-search serve    # 启动 MCP Server（由 AI 客户端自动调用）
```

## 提供的 MCP 工具

| 工具 | 说明 |
|------|------|
| ping | 验证 server 是否可用 |
| music_search | 搜索歌曲，返回精简列表（id/name/artist/album_name/duration/minfo/time/sign + total） |
| get_download_url | 查询歌曲下载链接，成功时只返回下载 URL |
| download_file | 把下载链接流式保存为本地文件，重名自动加序号 |

### music_search

| 参数 | 必填 | 默认 | 说明 |
|------|------|------|------|
| keyword | ✅ | — | 搜索关键词，如歌名或「歌名 歌手」 |
| platform | | kuwo | 平台 |
| page | | 1 | 页码，上限 10（防翻页过深） |
| size | | 20 | 每页条数，上限 50（超出自动钳制） |
| url | | 环境变量 SEARCH_URL | 搜索接口地址 |
| cookie | | 环境变量 SEARCH_COOKIE | 会话 cookie |

### get_download_url

| 参数 | 必填 | 默认 | 说明 |
|------|------|------|------|
| songid | ✅ | — | 取 music_search 结果项的 `id` |
| time | ✅ | — | 取结果项的 `time`（sign 与之绑定，禁止用当前时间戳代替） |
| sign | ✅ | — | 取结果项的 `sign`，原样传递 |
| platform | | kuwo | 平台 |
| format | | mp3 | 音频格式，可选值见结果项 `minfo`（如 mp3、flac） |
| bitrate | | 320 | 码率，可选值见结果项 `minfo`（如 320、817） |
| url | | SEARCH_DOWNLOAD_URL → SEARCH_URL | 下载链接接口地址 |
| cookie | | 环境变量 SEARCH_COOKIE | 会话 cookie |

### download_file

| 参数 | 必填 | 默认 | 说明 |
|------|------|------|------|
| url | ✅ | — | 文件下载地址，通常即 get_download_url 的返回值 |
| filename | | 从 URL 推断 | 保存文件名（不含扩展名也可，自动补上） |
| save_dir | | MUSIC_DOWNLOAD_DIR → ~/Downloads | 保存目录 |

## 环境变量

| 变量 | 说明 |
|------|------|
| SEARCH_URL | 搜索接口地址（必配） |
| SEARCH_DOWNLOAD_URL | 下载链接接口地址（可选，缺省复用 SEARCH_URL） |
| SEARCH_COOKIE | 接口会话 cookie（必配） |
| MUSIC_DOWNLOAD_DIR | 下载保存目录（可选，缺省 ~/Downloads） |

## 接入 AI 客户端

`music-search help` 会输出一段可直接粘贴的 MCP server 配置 JSON，形如：

```json
{
  "mcpServers": {
    "music-search": {
      "command": "music-search",
      "args": ["serve"],
      "env": {
        "SEARCH_URL": "https://your-search-endpoint",
        "SEARCH_COOKIE": "your-session-cookie"
      }
    }
  }
}
```

填入真实的 `SEARCH_URL` / `SEARCH_COOKIE` 后粘贴到客户端配置，重启客户端即可使用。

## 典型流程

1. `music_search(keyword="...")` 搜索，从结果列表中选定歌曲；
2. 把该项的 `id`/`time`/`sign` 原样传给 `get_download_url`（`sign` 与 `time` 绑定，禁止编造），`format`/`bitrate` 取自该项 `minfo` 中所选音质，拿到下载链接；
3. `download_file(url=<下载链接>, filename="歌名-歌手")` 保存到本地。
