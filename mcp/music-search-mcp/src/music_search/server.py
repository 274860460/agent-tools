#!/usr/bin/env python3
"""
music-search — 音乐搜索/下载 MCP Server

搜索歌曲、查询下载链接、流式下载到本地。
"""

import os
import sys
import warnings

warnings.filterwarnings("ignore", message=".*incomplete definition.*", module="pydantic")

from mcp.server.fastmcp import FastMCP

from music_search.cli import _print_help
from music_search.tools import register_all

# Windows 控制台强制 UTF-8
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

# ---------------------------------------------------------------------------
# MCP Server
# ---------------------------------------------------------------------------

mcp = FastMCP(
    "music-search",
    instructions=(
        "音乐搜索与下载工具。典型两步流程：\n"
        "1) 调 music_search 搜索歌曲，返回列表每项含 id/name/artist/album_name/duration/minfo/time/sign 和 total；\n"
        "2) 用户选定歌曲和音质后，调 get_download_url 获取下载链接——字段映射：songid←结果项 id、"
        "time←结果项 time、sign←结果项 sign（sign 与该 time 绑定，必须原样传递，"
        "禁止编造或用当前时间戳代替），format/bitrate←该项 minfo 中所选音质（如 mp3/320、flac/817）；\n"
        "3) 调 download_file 把返回的链接保存到本地，可指定 filename 和 save_dir。\n"
        "接口地址与 cookie 通过工具参数或环境变量 SEARCH_URL / SEARCH_DOWNLOAD_URL / SEARCH_COOKIE 提供。"
    ),
)

register_all(mcp)


# ---------------------------------------------------------------------------
# 入口
# ---------------------------------------------------------------------------

def main():
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""
    if cmd == "serve":
        import signal, threading
        evt = threading.Event()
        signal.signal(signal.SIGINT, lambda *_: evt.set())
        threading.Thread(target=lambda: (evt.wait(), os._exit(0)), daemon=True).start()
        mcp.run()
    else:
        _print_help()


if __name__ == "__main__":
    main()
