"""MCP 工具注册入口：聚合各工具模块的 register(mcp)。"""

from ops.tools import db, deploy, env, logs, monitor, remote


def register_all(mcp):
    """依次调用各模块的 register(mcp) 注册全部工具"""
    env.register(mcp)
    logs.register(mcp)
    monitor.register(mcp)
    remote.register(mcp)
    db.register(mcp)
    deploy.register(mcp)
