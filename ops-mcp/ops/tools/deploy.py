"""发布工具：上传 jar 包并驱动远程脚本异步滚动发布/回滚。"""

import fnmatch
import os
import re
import subprocess

from ops.config import get_env_config
from ops.ssh import scp_upload, ssh_exec

# 中止指令：任何工具返回以 [中止] 开头的消息时，调用方必须立即结束整个发布流程
ABORT_HINT = (
    "收到 [中止] 后必须立即结束本次发布，不再执行任何后续操作"
    "（包括构建、上传、自行修改配置），将原因原样转告用户，待用户解决后重新发起。"
)


def _deploy_cfg(cfg: dict, strict: bool = True) -> tuple[dict, str]:
    """取并校验 deploy 配置段，返回 (deploy_cfg, 错误信息)，无错误时错误信息为空。

    strict=True（发布类操作）缺失时返回 [中止] 指令；strict=False（只读查询）返回温和提示。
    """
    deploy = cfg.get("deploy")
    if not deploy:
        if not strict:
            return {}, (
                "[未配置] 当前环境未配置 deploy 段，本查询不可用。"
                "请提示用户在 .ops/config.yaml 对应环境补全 deploy 配置。"
            )
        return {}, (
            "[中止] 当前环境未配置 deploy 段。\n"
            f"{ABORT_HINT}\n"
            "配置模板（请原样转告用户）:\n"
            "    deploy:\n"
            "      script: /www/wwwroot/your-app/deploy.sh   # 服务器上的发布脚本\n"
            "      upload_dir: /www/wwwroot/your-app/upload  # jar 上传目录\n"
            "      jar_name: ruoyi-admin.jar\n"
            "      allowed_branches: []   # 允许发布的分支，支持通配符；空 = 不限制"
        )
    missing = [k for k in ("script", "upload_dir", "jar_name") if not deploy.get(k)]
    if missing:
        if not strict:
            return {}, f"[未配置] deploy 配置不完整，缺少: {', '.join(missing)}，本查询不可用。"
        return {}, (
            f"[中止] deploy 配置不完整，缺少: {', '.join(missing)}。\n{ABORT_HINT}"
        )
    return deploy, ""


def _backup_dir(deploy_cfg: dict) -> str:
    """备份目录 = upload_dir 同级 backup/"""
    base = os.path.dirname(deploy_cfg["upload_dir"].rstrip("/"))
    return f"{base}/backup"


def _deploy_log(deploy_cfg: dict) -> str:
    """发布日志 = 发布脚本同目录 .deploy-last.log"""
    base = os.path.dirname(deploy_cfg["script"])
    return f"{base}/.deploy-last.log"


def _deploy_pid(deploy_cfg: dict) -> str:
    """发布进程 pid 文件 = 发布脚本同目录 .deploy.pid"""
    base = os.path.dirname(deploy_cfg["script"])
    return f"{base}/.deploy.pid"


def _strip_ansi(text: str) -> str:
    """去掉 ANSI 颜色转义序列"""
    return re.sub(r"\x1b\[[0-9;]*m", "", text)


def _git(args: list[str]) -> str:
    """在当前目录执行 git 命令，返回 stdout；失败返回空字符串"""
    try:
        result = subprocess.run(
            ["git"] + args, capture_output=True, text=True, timeout=10,
            cwd=os.getcwd(), encoding="utf-8", errors="replace",
        )
        if result.returncode != 0:
            return ""
        return result.stdout.strip()
    except Exception:
        return ""


def _operator() -> str:
    """发布操作人：优先 git user.name，空则系统用户名"""
    name = _git(["config", "user.name"])
    if name:
        return name
    try:
        import getpass
        return getpass.getuser()
    except Exception:
        return "unknown"


def _shell_quote(value: str) -> str:
    """shell 单引号转义"""
    return value.replace("'", "'\\''")


def register(mcp):
    """注册发布相关工具"""

    # ---- 发布前置检查（构建前必须先做） ----

    @mcp.tool()
    def deploy_precheck(environment: str = "") -> str:
        """发布前置检查 —— 本地构建 jar 之前必须先调用，避免打包完成才发现问题。

        检查项: deploy 配置、git 分支策略、工作区是否干净、SSH 连通性、远端脚本/目录是否存在。
        全部通过后才可开始构建；任何 [中止] 项必须先解决并重新检查。

        Args:
            environment: 环境名
        """
        cfg = get_env_config(environment or None)
        deploy_cfg, err = _deploy_cfg(cfg)
        if err:
            return err
        env_name = cfg.get("_resolved_env", "?")

        # 本地 git 状态
        branch = _git(["rev-parse", "--abbrev-ref", "HEAD"]) or "unknown"
        sha = _git(["rev-parse", "--short", "HEAD"]) or "unknown"
        dirty = bool(_git(["status", "--porcelain"]))

        # 分支策略
        allowed = deploy_cfg.get("allowed_branches") or []
        if allowed and not any(fnmatch.fnmatch(branch, p) for p in allowed):
            branch_status = f"⚠️ 分支 {branch} 不在允许列表 {allowed}，发布时需用户确认（force_branch）"
        elif allowed:
            branch_status = f"✓ 分支 {branch} 命中允许列表 {allowed}"
        else:
            branch_status = f"✓ 分支 {branch}（该环境不限制分支）"

        dirty_status = "⚠️ 工作区有未提交改动，发布时需用户确认（allow_dirty）" if dirty else "✓ 工作区干净"

        # 远端检查：SSH 连通 + 脚本与目录存在
        script = deploy_cfg["script"]
        upload_dir = deploy_cfg["upload_dir"].rstrip("/")
        remote = ssh_exec(
            cfg,
            f"echo ssh-ok; test -f {script} && echo script-ok || echo script-missing; "
            f"test -d {upload_dir} && echo upload-ok || echo upload-missing",
            timeout=15,
        )
        if "ssh-ok" not in remote:
            return (
                f"[中止] SSH 连接失败:\n{remote}\n{ABORT_HINT}"
            )
        missing = [name for name, flag in (("script", "script-ok"), ("upload_dir", "upload-ok"))
                   if flag not in remote]
        if missing:
            return (
                f"[中止] 服务器上缺少: {', '.join(missing)}"
                f"（script={script}, upload_dir={upload_dir}）。\n{ABORT_HINT}"
            )

        return (
            f"[通过] 环境 {env_name} 前置检查完成，可以开始构建:\n"
            f"  {branch_status}\n"
            f"  {dirty_status}\n"
            f"  ✓ SSH 连通，远端脚本与上传目录就绪\n"
            f"  当前提交: {sha}\n"
            f"构建完成后调用 deploy 上传并发布。"
        )

    # ---- 发布 ----

    @mcp.tool()
    def deploy(
        jar_path: str,
        environment: str = "",
        allow_dirty: bool = False,
        force_branch: bool = False,
    ) -> str:
        """滚动发布：上传 jar 包并后台执行远程发布脚本（约 3~5 分钟，用 deploy_status 查进度）。

        注意：本地构建之前必须先调 deploy_precheck，通过后才可构建并调用本工具。

        Args:
            jar_path: 本地 jar 包路径（如 ruoyi-admin/target/ruoyi-admin.jar）
            environment: 环境名
            allow_dirty: 工作区有未提交改动时仍发布（需用户确认）
            force_branch: 当前分支不在 allowed_branches 时仍发布（需用户确认）
        """
        cfg = get_env_config(environment or None)
        deploy_cfg, err = _deploy_cfg(cfg)
        if err:
            return err
        env_name = cfg.get("_resolved_env", "?")

        # 1) 校验本地 jar 包
        jar_path = os.path.abspath(os.path.expanduser(jar_path))
        if not jar_path.endswith(".jar"):
            return f"[拒绝] 不是 jar 包: {jar_path}"
        if not os.path.isfile(jar_path):
            return f"[ERROR] 文件不存在: {jar_path}"

        # 2) 本地 git 检查（不在 git 仓库时 branch/sha 记为 unknown）
        branch = _git(["rev-parse", "--abbrev-ref", "HEAD"]) or "unknown"
        sha = _git(["rev-parse", "--short", "HEAD"]) or "unknown"
        status = _git(["status", "--porcelain"])
        operator = _operator()

        # 3) 工作区必须干净（除非 allow_dirty）
        if status and not allow_dirty:
            preview = "\n".join(status.splitlines()[:10])
            return (
                f"[需确认] 工作区有未提交改动:\n{preview}\n\n"
                f"请提交后重试，或由用户确认后以 allow_dirty=true 重新调用"
            )

        # 4) 分支策略：allowed_branches 非空时必须匹配（除非 force_branch）
        allowed = deploy_cfg.get("allowed_branches") or []
        if allowed and not force_branch:
            if not any(fnmatch.fnmatch(branch, pattern) for pattern in allowed):
                return (
                    f"[需确认] 分支 {branch} 不在环境 {env_name} 的允许列表 {allowed}。\n"
                    f"请告知用户并询问是否继续；用户确认后以 force_branch=true 重新调用"
                )

        # 5) 上传 jar 包
        remote_path = f"{deploy_cfg['upload_dir'].rstrip('/')}/{deploy_cfg['jar_name']}"
        err = scp_upload(cfg, jar_path, remote_path)
        if err:
            return f"[ERROR] 上传失败: {err}"

        # 6) 后台启动发布脚本（一次发布 3~5 分钟，必须异步），pid 写入文件供 deploy_status 判断
        deploy_log = _deploy_log(deploy_cfg)
        deploy_pid = _deploy_pid(deploy_cfg)
        cmd = (
            f"OPERATOR='{_shell_quote(operator)}' GIT_SHA='{_shell_quote(sha)}' "
            f"nohup bash {deploy_cfg['script']} > {deploy_log} 2>&1 < /dev/null & "
            f"echo $! > {deploy_pid}; echo \"started pid $(cat {deploy_pid})\""
        )
        started = ssh_exec(cfg, cmd, timeout=15)

        # 7) 返回启动信息
        size_mb = os.path.getsize(jar_path) / 1024 / 1024
        return (
            f"[已启动] 滚动发布后台运行中\n"
            f"  分支: {branch} ({sha})\n"
            f"  包: {os.path.basename(jar_path)} ({size_mb:.1f} MB)\n"
            f"  环境: {env_name}  操作人: {operator}  {started}\n"
            f"发布已后台启动，请用 deploy_status 轮询进度，完成前不要重复调用 deploy"
        )

    @mcp.tool()
    def deploy_status(environment: str = "", lines: int = 80) -> str:
        """查看发布/回滚进度（轮询用）。

        Args:
            environment: 环境名
            lines: 返回日志尾部行数，默认 80
        """
        cfg = get_env_config(environment or None)
        deploy_cfg, err = _deploy_cfg(cfg, strict=False)
        if err:
            return err

        # 通过 pid 文件判断发布进程是否存活（比 pgrep 匹配可靠）
        deploy_pid = _deploy_pid(deploy_cfg)
        running = ssh_exec(
            cfg,
            f"test -f {deploy_pid} && kill -0 $(cat {deploy_pid}) 2>/dev/null "
            f"&& echo RUNNING || echo FINISHED",
            timeout=10,
        )
        status = "RUNNING" if "RUNNING" in running else "FINISHED"

        deploy_log = _deploy_log(deploy_cfg)
        log = ssh_exec(cfg, f"tail -n {lines} {deploy_log} 2>/dev/null", timeout=10)
        env_name = cfg.get("_resolved_env", "?")
        return f"[环境: {env_name}]\n状态: {status}\n{'=' * 40}\n{_strip_ansi(log)}"

    @mcp.tool()
    def rollback(environment: str = "", backup: str = "latest") -> str:
        """回滚到指定备份（后台执行，用 deploy_status 查进度；备份列表用 list_backups 查看）。

        Args:
            environment: 环境名
            backup: 备份文件名（list_backups 输出中的名字），默认 latest 即最新备份
        """
        cfg = get_env_config(environment or None)
        deploy_cfg, err = _deploy_cfg(cfg)
        if err:
            return err

        if backup != "latest" and not re.fullmatch(r"[A-Za-z0-9._-]+", backup):
            return f"[拒绝] 非法备份名: {backup}（仅支持 latest 或 list_backups 输出的文件名）"

        operator = _operator()
        sha = _git(["rev-parse", "--short", "HEAD"]) or "unknown"
        deploy_log = _deploy_log(deploy_cfg)
        deploy_pid = _deploy_pid(deploy_cfg)
        cmd = (
            f"OPERATOR='{_shell_quote(operator)}' GIT_SHA='{_shell_quote(sha)}' "
            f"nohup bash {deploy_cfg['script']} rollback {backup} > {deploy_log} 2>&1 < /dev/null & "
            f"echo $! > {deploy_pid}; echo \"started pid $(cat {deploy_pid})\""
        )
        started = ssh_exec(cfg, cmd, timeout=15)
        env_name = cfg.get("_resolved_env", "?")
        return (
            f"[环境: {env_name}]\n"
            f"[已启动] 回滚后台运行中（目标备份: {backup}）  {started}\n"
            f"请用 deploy_status 轮询进度"
        )

    @mcp.tool()
    def list_backups(environment: str = "") -> str:
        """列出可回滚的备份包（按时间倒序，最多 20 条）。

        Args:
            environment: 环境名
        """
        cfg = get_env_config(environment or None)
        deploy_cfg, err = _deploy_cfg(cfg, strict=False)
        if err:
            return err

        backup_dir = _backup_dir(deploy_cfg)
        out = ssh_exec(
            cfg,
            f"ls -lt {backup_dir}/{deploy_cfg['jar_name']}.* 2>/dev/null | head -20",
            timeout=10,
        )
        env_name = cfg.get("_resolved_env", "?")
        if not out.strip() or "(无输出)" in out:
            return f"[环境: {env_name}]\n暂无备份（备份目录: {backup_dir}）"
        return f"[环境: {env_name}]\n{out}"

    @mcp.tool()
    def deploy_history(environment: str = "", lines: int = 20) -> str:
        """查看发布/回滚历史记录。

        Args:
            environment: 环境名
            lines: 返回最近记录条数，默认 20
        """
        cfg = get_env_config(environment or None)
        deploy_cfg, err = _deploy_cfg(cfg, strict=False)
        if err:
            return err

        backup_dir = _backup_dir(deploy_cfg)
        out = ssh_exec(cfg, f"tail -n {lines} {backup_dir}/history.log 2>/dev/null", timeout=10)
        env_name = cfg.get("_resolved_env", "?")
        if not out.strip() or "(无输出)" in out:
            return f"[环境: {env_name}]\n还没有发布记录"
        return f"[环境: {env_name}]\n{out}"
