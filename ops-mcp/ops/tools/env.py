"""环境工具：list_environments 查看配置状态与可用环境。"""

from ops.config import (
    CONFIG_PATH,
    _CONFIG_SEARCH_PATHS,
    _DEFAULT_CONFIG,
    _GLOBAL_CONFIG,
    load_config,
)


def register(mcp):
    """注册环境相关工具"""

    # ---- 环境 ----

    @mcp.tool()
    def list_environments() -> str:
        """列出配置状态和所有可用环境。未配置时返回初始化引导信息。"""
        # 展示配置查找结果
        info = [f"配置文件: {CONFIG_PATH or '未找到'}"]
        if not CONFIG_PATH:
            project_path = _CONFIG_SEARCH_PATHS[0]
            info.append(f"\n[未配置] 请创建配置文件:")
            info.append(f"  项目级: {project_path}")
            info.append(f"  全局:   {_GLOBAL_CONFIG}")
            info.append(f"\n配置模板:\n{_DEFAULT_CONFIG}")
            return "\n".join(info)

        config = load_config()
        envs = config.get("environments", {})
        if not envs:
            info.append("[空配置] environments 为空，请添加环境配置")
            info.append(f"\n配置模板:\n{_DEFAULT_CONFIG}")
            return "\n".join(info)

        info.append(f"环境数量: {len(envs)}")
        for name, cfg in envs.items():
            app = cfg.get("app", {})
            ports = app.get("ports", [])
            db = "✅" if cfg.get("db") else "❌"
            hc = "✅" if cfg.get("healthcheck", {}).get("endpoint") else "❌"
            jump = f" (via {cfg.get('ssh_jump', '')})" if cfg.get("ssh_jump") else ""
            info.append(
                f"  [{name}] {cfg.get('ssh_host','')}{jump}  "
                f"端口: {ports}  Healthcheck: {hc}  DB: {db}"
            )
        return "\n".join(info)
