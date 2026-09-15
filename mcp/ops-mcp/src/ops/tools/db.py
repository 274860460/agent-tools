"""数据库查询工具：只读 SQL 执行（SELECT / SHOW / DESCRIBE / EXPLAIN）。"""

from ops.config import get_env_config
from ops.ssh import ssh_exec


def register(mcp):
    """注册数据库查询工具"""

    # ---- 数据库查询 ----

    @mcp.tool()
    def mysql_query(query: str, environment: str = "") -> str:
        """在指定环境的数据库上执行只读 SQL 查询。

        仅允许 SELECT / SHOW / DESCRIBE / EXPLAIN 语句，禁止写操作。
        禁止多条 SQL 语句（不允许分号分隔）。
        禁止SQL 包含危险操作。

        Args:
            query: SQL 查询语句（仅限只读操作，如 SELECT * FROM table LIMIT 10）
            environment: 环境名
        """
        cfg = get_env_config(environment or None)
        db = cfg.get("db")
        if not db:
            return f"[ERROR] 环境 '{environment}' 未配置数据库连接信息"

        # 安全检查：只允许只读操作
        sql_stripped = query.strip()
        sql_upper = sql_stripped.upper()

        # 1) 前缀白名单
        allowed_prefixes = ("SELECT", "SHOW", "DESCRIBE", "DESC", "EXPLAIN")
        if not sql_upper.startswith(allowed_prefixes):
            return "[拒绝] 仅允许 SELECT / SHOW / DESCRIBE / EXPLAIN 查询"

        # 2) 禁止分号（防多语句注入）
        if ";" in sql_stripped.rstrip(";"):
            return "[拒绝] 禁止多条 SQL 语句（不允许分号分隔）"

        # 3) 危险关键字黑名单
        dangerous = ("INTO OUTFILE", "INTO DUMPFILE", "LOAD_FILE", "BENCHMARK(", "SLEEP(")
        if any(kw in sql_upper for kw in dangerous):
            return "[拒绝] SQL 包含危险操作"

        # 转义单引号
        safe_sql = query.replace("'", "'\\''")

        cmd = (
            f"mysql -h {db['host']} -P {db['port']} "
            f"-u {db['user']} -p'{db['password']}' "
            f"{db['database']} --safe-updates "
            f"-e '{safe_sql}' --table 2>&1 | head -500"
        )
        # DB 可能在不同机器，支持 ssh_proxy
        db_proxy = db.get("ssh_proxy", "")
        env_name = cfg.get("_resolved_env", "?")
        if db_proxy:
            db_cfg = dict(cfg)
            db_cfg["ssh_host"] = db_proxy
            return f"[环境: {env_name}]\n" + ssh_exec(db_cfg, cmd, timeout=30)
        return f"[环境: {env_name}]\n" + ssh_exec(cfg, cmd, timeout=30)
