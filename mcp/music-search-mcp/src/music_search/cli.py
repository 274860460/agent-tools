"""CLI：help 输出与可粘贴的 MCP server 配置 JSON。"""

import json
import shutil as _shutil
import sys


def _get_mcp_entry() -> dict:
    """生成 MCP 注册条目（使用已安装到 PATH 的 music-search 命令）"""
    which_result = _shutil.which("music-search")
    if which_result:
        command = which_result
    else:
        command = "music-search"
    # Windows 反斜杠转正斜杠，避免 JSON 转义问题
    return {"command": command.replace("\\", "/"), "args": ["serve"]}


def _print_help():
    from importlib.metadata import version
    ver = version("music-search")
    entry = _get_mcp_entry()
    config = {
        "mcpServers": {
            "music-search": {
                **entry,
                "env": {
                    "SEARCH_URL": "https://your-search-endpoint",
                    "SEARCH_COOKIE": "your-session-cookie",
                },
            }
        }
    }
    print(f"music-search {ver} — 音乐搜索/下载 MCP Server")
    print()
    print("用法:")
    print("  music-search serve    启动 MCP Server（由 AI 客户端自动调用）")
    print("  music-search help     显示此帮助")
    print()
    print("环境变量:")
    print("  SEARCH_URL            搜索接口地址（必配）")
    print("  SEARCH_DOWNLOAD_URL   下载链接接口地址（可选，缺省复用 SEARCH_URL）")
    print("  SEARCH_COOKIE         接口会话 cookie（必配）")
    print("  MUSIC_DOWNLOAD_DIR    下载保存目录（可选，缺省 ~/Downloads）")
    print()
    print("MCP server 配置（粘贴到你的 AI 客户端配置中）:")
    print()
    print(json.dumps(config, indent=2, ensure_ascii=False))
