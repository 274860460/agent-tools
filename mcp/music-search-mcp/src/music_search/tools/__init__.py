"""MCP 工具注册入口：聚合各工具模块的 register(mcp)。"""

from music_search.tools import download, ping, search


def register_all(mcp):
    """依次调用各模块的 register(mcp) 注册全部工具"""
    ping.register(mcp)
    search.register(mcp)
    download.register(mcp)
