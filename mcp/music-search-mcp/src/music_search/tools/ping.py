"""骨架验证工具：ping。"""


def register(mcp):
    """注册骨架验证工具"""

    @mcp.tool()
    def ping() -> str:
        """验证 server 是否可用，返回 pong。"""
        return "pong"
