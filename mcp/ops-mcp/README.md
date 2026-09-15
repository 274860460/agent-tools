# ops

线上运维排查 MCP Server — 通过 SSH 远程执行命令，支持多环境、多实例的日志查询、应用监控、数据库查询、进程排查。

## 安装

```bash
# 安装
uv tool install --force tools/ops-mcp

# 卸载
uv tool uninstall ops
```

## 使用

```bash
ops              # 显示帮助
ops install      # 注册到 AI 客户端（Gemini CLI / Claude / Cursor 等）
ops init         # 在当前项目生成 tools/ops/config.yaml
ops serve        # 启动 MCP Server（由 AI 客户端自动调用）
ops uninstall    # 从所有 AI 客户端中移除
```

## 提供的 MCP 工具

| 工具 | 说明 |
|------|------|
| list_environments | 查看配置状态和所有环境 |
| search_log | 搜索日志关键字 |
| tail_log | 查看最新日志 |
| log_context | 查看日志上下文 |
| recent_errors | 最近错误汇总 |
| app_health | 应用健康检查 |
| app_metrics | JVM/应用指标 |
| app_info | Spring 应用信息 |
| thread_dump | JVM 线程 dump |
| check_process | 进程和系统状态 |
| detect_ports | 检测运行中的实例端口 |
| quick_diagnosis | 一键快速诊断 |
| mysql_query | 只读 SQL 查询 |
| deploy_precheck | 发布前置检查（构建前必须先调） |
| deploy | 滚动发布（上传 jar + 后台执行发布脚本） |
| deploy_status | 查看发布/回滚进度 |
| rollback | 回滚到指定备份（默认最新） |
| list_backups | 列出可回滚的备份包 |
| deploy_history | 发布/回滚历史记录 |


## 项目配置

在项目中运行 `ops init` 后，编辑 `.ops/config.yaml`：

```yaml
default_env: test

environments:
  test:
    ssh_host: root@your-server
    ssh_key:
    app:
      ports:
       - 8001
      path: /www/wwwroot/your-app/app-{port}
      log_path: /www/wwwroot/your-app/app-{port}/logs/ruoyi-admin
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
      script: /www/wwwroot/your-app/deploy.sh   # 服务器上的发布脚本
      upload_dir: /www/wwwroot/your-app/upload  # jar 上传目录
      jar_name: ruoyi-admin.jar
      allowed_branches: []   # 允许发布的分支，支持通配符如 ["master", "release/*"]；空 = 不限制
```
