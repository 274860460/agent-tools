"""日志查询工具：搜索、查看、上下文与近期错误。"""

from ops.config import get_env_config
from ops.ssh import _log_file, run_on_instances


def register(mcp):
    """注册日志查询工具"""

    # ---- 日志查询 ----

    @mcp.tool()
    def search_log(
        keyword: str,
        environment: str = "",
        port: int = 0,
        level: str = "error",
        lines: int = 50,
        date: str = "",
    ) -> str:
        """搜索应用日志（支持正则匹配）。

        Args:
            keyword: 搜索关键字或正则表达式（如异常类名、订单号、traceId）
            environment: 环境名
            port: 实例端口号，0 表示查所有实例
            level: 日志级别文件 error|info|console，默认 error
            lines: 最多返回行数，默认 50
            date: 查归档日志的日期 YYYY-MM-DD，留空查当天
        """
        cfg = get_env_config(environment or None)
        p = port if port > 0 else None

        def build(pt):
            log_file, grep = _log_file(cfg, pt, level, date)
            return f"{grep} -i -- '{keyword}' {log_file} 2>/dev/null | tail -n {lines}"

        return run_on_instances(cfg, p, build, timeout=30)

    @mcp.tool()
    def tail_log(
        environment: str = "",
        port: int = 0,
        level: str = "error",
        lines: int = 100,
    ) -> str:
        """查看最近 N 行日志。

        Args:
            environment: 环境名
            port: 实例端口号，0 表示查所有实例
            level: 日志级别文件 error|info|console，默认 error
            lines: 行数，默认 100
        """
        cfg = get_env_config(environment or None)
        p = port if port > 0 else None

        def build(pt):
            log_file, _ = _log_file(cfg, pt, level)
            return f"tail -n {lines} {log_file}"

        return run_on_instances(cfg, p, build)

    @mcp.tool()
    def log_context(
        keyword: str,
        environment: str = "",
        port: int = 0,
        level: str = "console",
        before: int = 3,
        after: int = 15,
    ) -> str:
        """搜索日志并显示上下文（适合查看完整异常堆栈）。

        Args:
            keyword: 搜索关键字
            environment: 环境名
            port: 实例端口号，0 表示查所有实例
            level: 日志级别文件，默认 console（包含所有级别）
            before: 匹配行之前显示行数
            after: 匹配行之后显示行数（异常堆栈通常需要 15-30 行）
        """
        cfg = get_env_config(environment or None)
        p = port if port > 0 else None

        def build(pt):
            log_file, _ = _log_file(cfg, pt, level)
            return (
                f"grep -B {before} -A {after} -- '{keyword}' {log_file} "
                f"2>/dev/null | tail -n 500"
            )

        return run_on_instances(cfg, p, build, timeout=30)

    @mcp.tool()
    def recent_errors(environment: str = "", port: int = 0, minutes: int = 30) -> str:
        """查看最近 N 分钟内的错误日志。

        Args:
            environment: 环境名
            port: 实例端口号，0 表示查所有实例
            minutes: 最近多少分钟，默认 30
        """
        cfg = get_env_config(environment or None)
        p = port if port > 0 else None

        def build(pt):
            log_file, _ = _log_file(cfg, pt, "error")
            return (
                f"awk -v cutoff=\"$(date -d '{minutes} minutes ago' '+%Y-%m-%d %H:%M:%S')\" "
                f"'$0 >= cutoff' {log_file} 2>/dev/null | head -300"
            )

        return run_on_instances(cfg, p, build, timeout=30)
