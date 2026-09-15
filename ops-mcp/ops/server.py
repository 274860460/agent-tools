#!/usr/bin/env python3
"""
ops — 线上运维排查 MCP Server

通过 SSH 远程执行命令，提供日志查询、应用监控、进程排查等能力。
支持 test / uat / prod 多环境，同机多实例（不同 server.port）。
"""

import os
import sys
import warnings

warnings.filterwarnings("ignore", message=".*incomplete definition.*", module="pydantic")

from mcp.server.fastmcp import FastMCP

from ops.cli import _print_help, _run_init, _run_setup, _run_uninstall
from ops.tools import register_all

# Windows 控制台强制 UTF-8
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

# ---------------------------------------------------------------------------
# MCP Server
# ---------------------------------------------------------------------------

mcp = FastMCP(
    "ops",
    instructions=(
        "线上运维排查与发布工具 —— 支持多环境、同机多实例的日志查询、应用监控、数据库查询、进程排查、滚动发布与回滚。\n"
        "【重要】所有工具的环境参数名统一为 environment（不是 env），传错参数名会被静默忽略并 fallback 到默认环境！\n"
        "调用示例：quick_diagnosis(environment='prod')、remote_exec(command='hostname', environment='prod')。\n"
        "每个工具的返回值首行会标注 [环境: xxx]，务必核对是否为预期环境。\n"
        "发布流程：必须先调 deploy_precheck 做前置检查（配置/分支/工作区/远端脚本），通过后才可本地构建 jar，"
        "再调 deploy 上传并后台发布，用 deploy_status 轮询进度。"
        "任何工具返回以 [中止] 开头的消息时，必须立即停止全部后续操作，将原因转告用户。"
    ),
)

register_all(mcp)


# ---------------------------------------------------------------------------
# 入口
# ---------------------------------------------------------------------------

def main():
    import sys
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""
    if cmd in ("install", "setup"):
        _run_setup()
    elif cmd == "init":
        _run_init()
    elif cmd == "uninstall":
        _run_uninstall()
    elif cmd == "serve":
        import signal, threading
        evt = threading.Event()
        signal.signal(signal.SIGINT, lambda *_: evt.set())
        threading.Thread(target=lambda: (evt.wait(), os._exit(0)), daemon=True).start()
        mcp.run()
    else:
        _print_help()


if __name__ == "__main__":
    main()
