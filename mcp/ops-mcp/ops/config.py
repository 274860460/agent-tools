"""配置加载：多环境多实例配置的查找、读取与端口解析。"""

import os

import yaml

_CWD = os.getcwd()
_GLOBAL_CONFIG = os.path.expanduser("~/.config/ops/config.yaml")
_CONFIG_SEARCH_PATHS = [
    os.path.join(_CWD, ".ops", "config.yaml"),            # 项目级（推荐）
    _GLOBAL_CONFIG,                                              # 全局兜底
]

_DEFAULT_CONFIG = """\
# ops MCP - 多环境多实例配置
# 文档: https://github.com/xxx/ops

environments:
  test:
    ssh_host: root@your-server
    ssh_key:
    app:
      ports:
        - 8001
      path: /path/your-app/app-{port}
      log_path: /path/your-app/app-{port}/logs
    healthcheck:
      endpoint:              # actuator 基础路径，如 /actuator，留空禁用
      username:
      password:
    db:
      host: 127.0.0.1
      port: 3306
      user: readonly_user
      password: your_password
      database: your_database
      ssh_proxy:             # DB 所在机器的 SSH，留空则复用 ssh_host
    deploy:
      script: /path/your-app/deploy.sh   # 服务器上的发布脚本
      upload_dir: /path/your-app/upload  # jar 上传目录
      jar_name: ruoyi-admin.jar
      allowed_branches: []   # 允许发布的分支，支持通配符如 ["master", "release/*"]；空 = 不限制
"""


def _find_config() -> str:
    for p in _CONFIG_SEARCH_PATHS:
        if os.path.isfile(p):
            return p
    return ""


CONFIG_PATH = _find_config()


def load_config() -> dict:
    if not CONFIG_PATH:
        raise FileNotFoundError(
            f"未找到配置文件。请在以下位置创建:\n"
            f"  项目级: {_CONFIG_SEARCH_PATHS[0]}\n"
            f"  全局:   {_GLOBAL_CONFIG}\n"
            f"可通过 list_environments 工具查看配置状态。"
        )
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def get_env_config(env: str | None = None) -> dict:
    config = load_config()
    envs = config.get("environments", {})
    if not env:
        names = list(envs.keys())
        raise ValueError(
            f"未指定环境，请从以下环境中选择: {names}"
        )
    if env not in envs:
        raise ValueError(f"环境 '{env}' 不存在，可用: {list(envs.keys())}")
    cfg = envs[env]
    cfg["_resolved_env"] = env
    return cfg


def resolve_ports(cfg: dict, port: int | None = None) -> list[int]:
    """解析要操作的端口列表。port 为 None 时返回该环境所有端口。"""
    app = cfg.get("app", {})
    all_ports = app.get("ports", [])
    if port is not None:
        if port not in all_ports:
            raise ValueError(f"端口 {port} 不在该环境配置中，可用: {all_ports}")
        return [port]
    return all_ports
