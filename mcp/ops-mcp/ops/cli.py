"""CLI 安装器：install/init/uninstall/help 及 AI 客户端配置写入。"""

import json
import os
import subprocess
import sys

import shutil as _shutil

from ops.config import _DEFAULT_CONFIG

# 各 AI 客户端的 MCP 配置文件位置
_AI_CLIENTS = [
    {
        "name": "Gemini CLI / Antigravity",
        "config_path": "~/.gemini/config/mcp_config.json",
        "detect_paths": ["~/.gemini/config"],
        "format": "json",
    },
    {
        "name": "Claude Code",
        "config_path": "",
        "detect_paths": ["~/.claude"],
        "format": "cli",
    },
    {
        "name": "Codex CLI",
        "config_path": "",
        "detect_paths": ["~/.codex"],
        "format": "cli",
        "cli_cmd": "codex",
    },
    {
        "name": "Cursor",
        "config_path": "~/.cursor/mcp.json",
        "detect_paths": ["~/.cursor"],
        "format": "json",
    },
    {
        "name": "Windsurf",
        "config_path": "~/.codeium/windsurf/mcp_config.json",
        "detect_paths": ["~/.codeium/windsurf"],
        "format": "json",
    },
]


def _detect_clients() -> list[dict]:
    """检测已安装的 AI 客户端"""
    results = []
    for client in _AI_CLIENTS:
        detected = any(
            os.path.isdir(os.path.expanduser(p)) for p in client["detect_paths"]
        )
        results.append({**client, "detected": detected})
    return results


def _get_mcp_entry() -> dict:
    """生成 MCP 注册条目（使用已安装到 PATH 的 ops 命令）"""
    candidates = [
        os.path.expanduser("~/.local/bin/ops"),
    ]
    # Windows 常见路径
    if sys.platform == "win32":
        candidates.extend([
            os.path.expanduser("~/AppData/Roaming/Python/Scripts/ops.exe"),
            os.path.expanduser("~/.local/bin/ops.exe"),
        ])
    else:
        candidates.extend([
            "/opt/homebrew/bin/ops",
            "/usr/local/bin/ops",
        ])

    # 也检查 which（shell 环境下能找到）
    which_result = _shutil.which("ops")
    if which_result:
        candidates.insert(0, which_result)

    for path in candidates:
        if os.path.isfile(path):
            # Windows 反斜杠转正斜杠，避免 JSON/TOML 转义问题
            return {"command": path.replace("\\", "/"), "args": ["serve"]}
    # fallback: uvx
    uvx_path = _shutil.which("uvx")
    if uvx_path:
        return {"command": uvx_path.replace("\\", "/"), "args": ["ops", "serve"]}
    return {"command": "ops", "args": ["serve"]}


def _write_mcp_config(client: dict):
    """将 ops 写入指定客户端的 MCP 配置文件"""
    fmt = client.get("format", "json")

    if fmt == "cli":
        return _write_cli_config(client)
    if fmt == "toml":
        config_path = os.path.expanduser(client["config_path"])
        os.makedirs(os.path.dirname(config_path), exist_ok=True)
        return _write_toml_config(config_path)

    config_path = os.path.expanduser(client["config_path"])
    os.makedirs(os.path.dirname(config_path), exist_ok=True)
    return _write_json_config(config_path, client)


def _write_cli_config(client: dict) -> str:
    """通过 CLI 命令注册 MCP（Claude Code / Codex CLI）"""
    entry = _get_mcp_entry()
    cli = client.get("cli_cmd", "claude")

    # claude: claude mcp add --scope user ops -- /path/to/ops serve
    # codex:  codex mcp add ops -- /path/to/ops serve
    if cli == "claude":
        add_cmd = [cli, "mcp", "add", "--scope", "user", "ops", "--", entry["command"]]
        remove_cmd = [cli, "mcp", "remove", "--scope", "user", "ops"]
    else:
        add_cmd = [cli, "mcp", "add", "ops", "--", entry["command"]]
        remove_cmd = [cli, "mcp", "remove", "ops"]
    add_cmd.extend(entry.get("args", []))

    try:
        # 先移除旧的（忽略错误）
        subprocess.run(remove_cmd, capture_output=True, timeout=10)
        result = subprocess.run(
            add_cmd, capture_output=True, text=True, timeout=15,
            encoding="utf-8", errors="replace"
        )
        if result.returncode == 0:
            return f"{cli} mcp add (global)"
        return f"{cli} mcp add 失败: {result.stderr.strip()}"
    except FileNotFoundError:
        return f"{cli} 命令未找到，请手动运行: " + " ".join(add_cmd)
    except Exception as e:
        return f"错误: {e}"


def _write_json_config(config_path: str, client: dict = None) -> str:
    """写入 JSON 格式的 MCP 配置"""
    existing = {}
    if os.path.isfile(config_path):
        with open(config_path, "r", encoding="utf-8") as f:
            try:
                existing = json.load(f)
            except json.JSONDecodeError:
                existing = {}

    entry = _get_mcp_entry()
    client_name = client.get("name", "") if client else ""

    # Claude Code 需要 type 和 env
    if "Claude" in client_name:
        entry["type"] = "stdio"
        entry["env"] = {"PYTHONUTF8": "1"}

    servers = existing.get("mcpServers", {})
    servers["ops"] = entry
    existing["mcpServers"] = servers

    with open(config_path, "w", encoding="utf-8") as f:
        json.dump(existing, f, indent=2)
    return config_path


def _strip_toml_sections(content: str, prefixes: list[str]) -> str:
    """按行过滤，移除匹配 prefixes 的 TOML section 及其内容"""
    lines = content.split("\n")
    result = []
    skip = False
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("["):
            # 检查是否是要删除的 section
            skip = any(stripped.startswith(f"[{p}]") for p in prefixes)
        if not skip:
            result.append(line)
    # 去掉末尾多余空行
    text = "\n".join(result)
    while "\n\n\n" in text:
        text = text.replace("\n\n\n", "\n\n")
    return text


def _write_toml_config(config_path: str) -> str:
    """写入 TOML 格式的 MCP 配置（Codex CLI）"""
    entry = _get_mcp_entry()
    # 读取现有内容
    content = ""
    if os.path.isfile(config_path):
        with open(config_path, "r", encoding="utf-8") as f:
            content = f.read()

    # 先清除旧的 ops 段（包括 .env 子段）
    content = _strip_toml_sections(content, ["mcp_servers.ops", "mcp_servers.ops.env"])

    # 构建 TOML 段
    args_str = ", ".join(f'"{a}"' for a in entry.get("args", []))
    toml_section = (
        f'\n[mcp_servers.ops]\n'
        f'command = "{entry["command"]}"\n'
        f'args = [{args_str}]\n'
        f'\n[mcp_servers.ops.env]\n'
        f'PYTHONUTF8 = "1"\n'
    )

    content += toml_section

    with open(config_path, "w", encoding="utf-8") as f:
        f.write(content)
    return config_path


def _run_setup():
    """交互式安装"""
    import sys as _sys

    print("┌  ops MCP Server")
    print("│")

    clients = _detect_clients()

    # 展示检测结果
    print("◆  检测到以下 AI 客户端:")
    print("│")
    detected = []
    for i, c in enumerate(clients):
        status = "detected" if c["detected"] else "not found"
        mark = "◼" if c["detected"] else "◻"
        suffix = " — global only" if c.get("global_only") else ""
        print(f"│  {mark} {c['name']} ({status}){suffix}")
        if c["detected"]:
            detected.append(c)
    print("│")

    if not detected:
        print("└  未检测到已安装的 AI 客户端。")
        return

    # 让用户确认
    print("◆  要为哪些客户端配置 ops MCP?")
    print("│  回车 = 全部已检测到的，或输入编号（逗号分隔）:")
    print("│")
    for i, c in enumerate(detected):
        print(f"│  [{i + 1}] {c['name']}")
    print("│")

    choice = input("│  > ").strip()
    if not choice:
        selected = detected
    else:
        indices = [int(x.strip()) - 1 for x in choice.split(",") if x.strip().isdigit()]
        selected = [detected[i] for i in indices if 0 <= i < len(detected)]

    if not selected:
        print("└  未选择任何客户端。")
        return

    # 写入配置
    print("│")
    for c in selected:
        path = _write_mcp_config(c)
        print(f"│  ✅ {c['name']} → {path}")

    print("│")
    print("│  配置完成！重启对应的 AI 客户端即可使用。")
    print("│")
    print("│  下一步: 在项目中运行 `ops init` 生成配置")
    print("│")
    print("└  Done!")


def _run_init():
    """在当前项目中初始化 ops 配置"""
    target_dir = os.path.join(os.getcwd(), ".ops")
    target_file = os.path.join(target_dir, "config.yaml")

    print("┌  ops init")
    print("│")

    if os.path.isfile(target_file):
        print(f"│  ⚠️  配置已存在: {target_file}")
        print("│  如需重新生成，请先删除该文件")
        print("└  跳过")
        return

    os.makedirs(target_dir, exist_ok=True)
    with open(target_file, "w", encoding="utf-8") as f:
        f.write(_DEFAULT_CONFIG)

    print(f"│  ✅ 已创建: {target_file}")
    print("│")
    print("│  请编辑该文件，填入你的 SSH 和数据库信息。")
    print("│")
    print("└  Done!")


def _run_uninstall():
    """从所有 AI 客户端中移除 ops MCP 配置"""
    print("┌  ops uninstall")
    print("│")

    removed = 0
    for client in _AI_CLIENTS:
        try:
            if client.get("format") == "cli":
                cli = client.get("cli_cmd", "claude")
                if cli == "claude":
                    rm_cmd = [cli, "mcp", "remove", "--scope", "user", "ops"]
                else:
                    rm_cmd = [cli, "mcp", "remove", "ops"]
                result = subprocess.run(
                    rm_cmd, capture_output=True, text=True, timeout=10,
                    encoding="utf-8", errors="replace"
                )
                if result.returncode == 0:
                    print(f"│  ✅ 已移除: {client['name']} ({cli} mcp remove)")
                    removed += 1
                continue
            config_path = os.path.expanduser(client["config_path"])
            if not os.path.isfile(config_path):
                continue
            if client.get("format") == "toml":
                with open(config_path, "r", encoding="utf-8") as f:
                    content = f.read()
                if "[mcp_servers.ops]" in content:
                    content = _strip_toml_sections(content, ["mcp_servers.ops", "mcp_servers.ops.env"])
                    with open(config_path, "w", encoding="utf-8") as f:
                        f.write(content)
                    print(f"│  ✅ 已移除: {client['name']} ({config_path})")
                    removed += 1
            else:
                with open(config_path, "r", encoding="utf-8") as f:
                    existing = json.load(f)
                servers = existing.get("mcpServers", {})
                if "ops" in servers:
                    del servers["ops"]
                    existing["mcpServers"] = servers
                    with open(config_path, "w", encoding="utf-8") as f:
                        json.dump(existing, f, indent=2)
                    print(f"│  ✅ 已移除: {client['name']} ({config_path})")
                    removed += 1
        except (json.JSONDecodeError, KeyError, OSError):
            pass

    if removed == 0:
        print("│  未找到已配置的客户端")
    print("│")
    print("└  Done!")


def _print_help():
    from importlib.metadata import version
    ver = version("ops")
    print(f"ops {ver} — 线上运维排查 MCP Server")
    print()
    print("用法:")
    print("  ops install      注册到 AI 客户端（Gemini CLI / Claude / Cursor 等）")
    print("  ops init         在当前项目生成 .ops/config.yaml")
    print("  ops uninstall    从所有 AI 客户端中移除")
    print("  ops serve        启动 MCP Server（由 AI 客户端自动调用）")
    print("  ops help         显示此帮助")
