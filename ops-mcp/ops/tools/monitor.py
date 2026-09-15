"""应用监控工具：Actuator 健康/指标/信息、线程 dump、进程排查与一键诊断。"""

from ops.config import get_env_config
from ops.ssh import _actuator_curl_cmd, _log_file, run_on_instances, ssh_exec


def register(mcp):
    """注册应用监控与进程排查工具"""

    # ---- 应用监控 (Actuator) ----

    @mcp.tool()
    def app_health(environment: str = "", port: int = 0) -> str:
        """检查应用健康状态 (Actuator /health)。

        Args:
            environment: 环境名
            port: 实例端口号，0 表示查所有实例
        """
        cfg = get_env_config(environment or None)
        p = port if port > 0 else None
        def build(pt):
            return _actuator_curl_cmd(cfg, pt, "health")
        return f"[环境: {cfg.get('_resolved_env')}]\n" + run_on_instances(cfg, p, build, timeout=15)

    @mcp.tool()
    def app_metrics(environment: str = "", port: int = 0, metric: str = "") -> str:
        """查询应用指标 (Actuator /metrics)。

        常用指标:
        - jvm.memory.used / jvm.memory.max (JVM 内存)
        - jvm.threads.live (活跃线程数)
        - system.cpu.usage (CPU 使用率)
        - http.server.requests (HTTP 请求统计)
        - hikaricp.connections.active (数据库连接池)
        - jvm.gc.pause (GC 暂停)

        Args:
            environment: 环境名
            port: 实例端口号，0 表示查所有实例
            metric: 指标名，留空列出所有可用指标
        """
        cfg = get_env_config(environment or None)
        p = port if port > 0 else None
        path = f"metrics/{metric}" if metric else "metrics"
        def build(pt):
            return _actuator_curl_cmd(cfg, pt, path)
        return f"[环境: {cfg.get('_resolved_env')}]\n" + run_on_instances(cfg, p, build, timeout=15)

    @mcp.tool()
    def app_info(environment: str = "", port: int = 0, prop: str = "") -> str:
        """查看 Spring 应用信息或配置属性。

        Args:
            environment: 环境名
            port: 实例端口号，0 表示查所有实例
            prop: 属性名（如 server.port, spring.datasource），留空返回 /info
        """
        cfg = get_env_config(environment or None)
        p = port if port > 0 else None
        path = f"env/{prop}" if prop else "info"
        def build(pt):
            return _actuator_curl_cmd(cfg, pt, path)
        return f"[环境: {cfg.get('_resolved_env')}]\n" + run_on_instances(cfg, p, build, timeout=15)

    @mcp.tool()
    def thread_dump(environment: str = "", port: int = 0) -> str:
        """获取 JVM 线程 dump（用于排查死锁、线程阻塞）。

        Args:
            environment: 环境名
            port: 实例端口号（建议指定单个实例，数据量大）
        """
        cfg = get_env_config(environment or None)
        p = port if port > 0 else None
        def build(pt):
            return _actuator_curl_cmd(cfg, pt, "threaddump")
        return f"[环境: {cfg.get('_resolved_env')}]\n" + run_on_instances(cfg, p, build, timeout=60)

    # ---- 进程 & 系统 ----

    @mcp.tool()
    def check_process(environment: str = "") -> str:
        """检查服务器上所有 Java 进程状态、系统资源概况。

        返回: 所有 Java 进程信息(PID/CPU/MEM/端口)、系统负载、磁盘、内存

        Args:
            environment: 环境名
        """
        cfg = get_env_config(environment or None)
        cmd = (
            "echo '=== Java 进程 ===' && "
            "ps aux --sort=-%mem | grep '[j]ava' | head -5 && "
            "echo '' && echo '=== 系统负载 ===' && uptime && "
            "echo '' && echo '=== 磁盘使用 ===' && df -h | grep -E '^/dev|Filesystem' && "
            "echo '' && echo '=== 内存 ===' && free -h"
        )
        return f"[环境: {cfg.get('_resolved_env')}]\n" + ssh_exec(cfg, cmd, timeout=15)

    @mcp.tool()
    def detect_ports(environment: str = "") -> str:
        """自动检测线上所有 Java 进程的 server.port，确认实际运行的实例。

        Args:
            environment: 环境名
        """
        cfg = get_env_config(environment or None)
        cmd = (
            "echo '=== 运行中的实例端口 ===' && "
            "ps aux | grep '[j]ava' | grep -oP 'server\\.port=\\K[0-9]+' | sort && "
            "echo '' && echo '=== 进程详情 ===' && "
            "ps -eo pid,user,%cpu,%mem,lstart,args | grep '[j]ava.*ruoyi' | head -5"
        )
        return f"[环境: {cfg.get('_resolved_env')}]\n" + ssh_exec(cfg, cmd, timeout=10)

    # ---- 快捷排查组合 ----

    @mcp.tool()
    def quick_diagnosis(environment: str = "", port: int = 0) -> str:
        """一键快速诊断：健康检查 + 最近错误 + 进程状态 + JVM 关键指标。

        Args:
            environment: 环境名
            port: 实例端口号，0 表示诊断所有实例
        """
        cfg = get_env_config(environment or None)
        p = port if port > 0 else None

        def build(pt):
            log_file, _ = _log_file(cfg, pt, "error")
            health_cmd = _actuator_curl_cmd(cfg, pt, "health")
            mem_cmd = _actuator_curl_cmd(cfg, pt, "metrics/jvm.memory.used")
            return (
                f"echo '=== 健康检查 ===' && "
                f"{health_cmd} 2>/dev/null || echo 'Actuator 不可达' && "
                f"echo '' && echo '=== 最近错误 ===' && "
                f"tail -n 20 {log_file} 2>/dev/null || echo '无错误日志' && "
                f"echo '' && echo '=== JVM 内存 ===' && "
                f"{mem_cmd} 2>/dev/null || echo '指标不可达'"
            )

        # 额外追加系统级信息（只需一次）
        sys_info = ssh_exec(cfg, "echo '=== 系统概况 ===' && uptime && free -h | head -2", timeout=10)
        instance_result = run_on_instances(cfg, p, build, timeout=20)
        return f"{instance_result}\n\n{sys_info}"
