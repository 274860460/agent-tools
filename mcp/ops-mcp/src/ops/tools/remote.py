"""远程命令工具：带危险命令黑名单校验的自定义 Shell 执行。"""

from ops.config import get_env_config
from ops.ssh import ssh_exec

# 危险命令黑名单
_DANGEROUS_COMMANDS = (
    "rm ", "rm\t", "rmdir ", "mv ", "cp ",
    "dd ", "mkfs", "fdisk",
    "reboot", "shutdown", "poweroff", "halt", "init ",
    "kill ", "killall ", "pkill ",
    "systemctl stop", "systemctl disable", "systemctl restart",
    "service stop", "service restart",
    "iptables", "firewall-cmd",
    "chmod ", "chown ", "chattr ",
    "useradd", "userdel", "passwd",
    "crontab -r", "crontab -e",
    "wget ", "curl -o", "curl -O",
    "yum remove", "yum erase", "apt remove", "apt purge", "dnf remove",
    "pip install", "pip uninstall", "npm install",
    "> /", ">> /",
    "truncate ",
    "mysql -e", "mysqldump",
)

_DANGEROUS_PATTERNS = (
    "|rm ", "; rm ", "&& rm ",
    "|dd ", "; dd ", "&& dd ",
    "$(", "`",  # 命令替换
)


def register(mcp):
    """注册远程命令工具"""

    # ---- 远程命令 ----

    @mcp.tool()
    def remote_exec(command: str, environment: str = "", timeout: int = 30) -> str:
        """在远程服务器执行自定义 Shell 命令（仅限排查诊断，禁止破坏性操作）。

        常用场景:
        - 查看磁盘: df -h
        - 查看内存: free -h
        - 查看网络: ss -tlnp / netstat -tlnp
        - 查看文件: cat /path/to/file / head -n 100 /path/to/file
        - 查看系统日志: journalctl -u xxx --no-pager -n 50
        - 查看 nginx 配置: cat /etc/nginx/conf.d/xxx.conf
        - 查看环境变量: env | grep JAVA
        - 查看 crontab: crontab -l

        Args:
            command: 要执行的 Shell 命令
            environment: 环境名
            timeout: 超时秒数，默认 30，最大 120
        """
        cfg = get_env_config(environment or None)

        # 安全检查
        cmd_lower = command.lower().strip()

        # 1) 黑名单前缀
        for dangerous in _DANGEROUS_COMMANDS:
            if cmd_lower.startswith(dangerous.lower()):
                return f"[拒绝] 禁止执行危险命令: {dangerous.strip()}"

        # 2) 危险模式（管道/链式中嵌入危险命令）
        for pattern in _DANGEROUS_PATTERNS:
            if pattern.lower() in cmd_lower:
                return f"[拒绝] 命令包含危险模式: {pattern.strip()}"

        # 3) 限制超时
        timeout = min(max(timeout, 5), 120)

        env_name = cfg.get("_resolved_env", "?")
        result = ssh_exec(cfg, command, timeout=timeout)
        return f"[环境: {env_name}]\n{result}"
