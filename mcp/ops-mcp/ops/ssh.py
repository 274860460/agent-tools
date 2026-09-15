"""SSH 远程执行：命令下发、多实例批量执行与日志/actuator 路径助手。"""

import os
import re
import subprocess

from ops.config import resolve_ports


def _base_ssh_cmd(cfg: dict) -> list[str]:
    """组装 ssh/scp 共用的连接选项（含密钥与跳板机）"""
    cmd = [
        "-o", "StrictHostKeyChecking=no",
        "-o", "ConnectTimeout=10",
    ]
    ssh_key = cfg.get("ssh_key", "")
    if ssh_key:
        cmd.extend(["-i", os.path.expanduser(ssh_key)])
    ssh_jump = cfg.get("ssh_jump", "")
    if ssh_jump:
        cmd.extend(["-J", ssh_jump])
    return cmd


def ssh_exec(cfg: dict, command: str, timeout: int = 30) -> str:
    """通过 SSH 执行远程命令并返回输出"""
    ssh_cmd = ["ssh"] + _base_ssh_cmd(cfg)
    ssh_cmd.extend([cfg["ssh_host"], command])

    try:
        result = subprocess.run(
            ssh_cmd, capture_output=True, text=True, timeout=timeout, encoding="utf-8", errors="replace"
        )
        output = result.stdout
        if result.returncode != 0 and result.stderr:
            output = f"[STDERR] {result.stderr.strip()}\n{output}"
        return output.strip() or "(无输出)"
    except subprocess.TimeoutExpired:
        return f"[TIMEOUT] 命令执行超过 {timeout}s 超时"
    except Exception as e:
        return f"[ERROR] {e}"


def scp_upload(cfg: dict, local_path: str, remote_path: str, timeout: int = 600) -> str:
    """通过 SCP 上传文件到远程服务器。成功返回空字符串，失败返回错误描述"""
    scp_cmd = ["scp"] + _base_ssh_cmd(cfg)
    scp_cmd.extend([local_path, f"{cfg['ssh_host']}:{remote_path}"])
    try:
        result = subprocess.run(
            scp_cmd, capture_output=True, text=True, timeout=timeout, encoding="utf-8", errors="replace"
        )
        if result.returncode != 0:
            return result.stderr.strip() or f"scp 退出码 {result.returncode}"
        return ""
    except subprocess.TimeoutExpired:
        return f"[TIMEOUT] 上传超过 {timeout}s 超时"
    except Exception as e:
        return f"[ERROR] {e}"


def run_on_instances(cfg: dict, port: int | None, build_cmd, timeout: int = 30) -> str:
    """对指定或所有实例执行命令，自动标注端口来源。

    build_cmd: callable(port: int) -> str  根据端口生成 shell 命令
    """
    ports = resolve_ports(cfg, port)
    env_name = cfg.get("_resolved_env", "?")
    results = []
    for p in ports:
        header = f"[:{p}]" if len(ports) > 1 else ""
        cmd = build_cmd(p)
        try:
            output = ssh_exec(cfg, cmd, timeout=timeout)
        except Exception as e:
            output = f"执行失败: {e}"
        if header:
            results.append(f"{header}\n{output}")
        else:
            results.append(output)
    body = "\n\n".join(results)
    return f"[环境: {env_name}]\n{body}"


def _resolve_log_file(cfg: dict, port: int, level: str) -> str:
    """从 log_path 模板解析出具体日志文件路径。

    支持模板变量:
      {port}               → 替换为端口号
      {console,info,error}  → 替换为实际 level（bash brace expansion 风格）

    示例: .../app-{port}/logs/{console,info,error}.log
        → .../app-8001/logs/error.log
    """
    app = cfg.get("app", {})
    log_path = app.get("log_path", "")
    if log_path:
        resolved = log_path.replace("{port}", str(port))
        resolved = re.sub(r"\{[^}]*,[^}]*\}", level, resolved)
        return resolved
    # 兜底：从 app.path 推导
    app_path = app.get("path", "").replace("{port}", str(port))
    base = f"{app_path}/logs" if app_path else "/tmp"
    return f"{base}/{level}.log"


def _log_file(cfg: dict, port: int, level: str, date: str = "") -> tuple[str, str]:
    """返回 (日志文件路径, grep命令)"""
    path = _resolve_log_file(cfg, port, level)
    if date:
        log_dir = path.rsplit("/", 1)[0]
        return f"{log_dir}/archive/{level}.{date}.log.gz", "zgrep"
    return path, "grep"


def _curl_actuator(cfg: dict, port: int, path: str) -> str:
    try:
        return ssh_exec(cfg, _actuator_curl_cmd(cfg, port, path), timeout=15)
    except Exception:
        return f"[端口 {port}] Actuator 不可用 — 请确认应用已启用 spring-boot-actuator 并暴露了 /{path} 端点"


def _actuator_curl_cmd(cfg: dict, port: int, path: str) -> str:
    """生成带认证的 actuator curl 命令"""
    hc = cfg.get("healthcheck", {})
    endpoint = hc.get("endpoint", "/actuator")
    if not endpoint:
        return f"echo '[跳过] healthcheck.endpoint 未配置'"
    user = hc.get("username", "")
    pwd = hc.get("password", "")
    auth = f" -u '{user}:{pwd}'" if user else ""
    return f"curl -sf{auth} http://localhost:{port}{endpoint}/{path}"
