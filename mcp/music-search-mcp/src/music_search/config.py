"""环境变量与默认值解析：接口地址、cookie、下载目录。"""

import os

ENV_SEARCH_URL = "SEARCH_URL"
ENV_DOWNLOAD_URL = "SEARCH_DOWNLOAD_URL"
ENV_COOKIE = "SEARCH_COOKIE"
ENV_DOWNLOAD_DIR = "MUSIC_DOWNLOAD_DIR"


def resolve_search_url(url: str | None = None) -> str:
    """搜索接口地址：参数 → SEARCH_URL"""
    return url or os.environ.get(ENV_SEARCH_URL, "")


def resolve_download_url(url: str | None = None) -> str:
    """下载链接接口地址：参数 → SEARCH_DOWNLOAD_URL → SEARCH_URL"""
    return url or os.environ.get(ENV_DOWNLOAD_URL, "") or os.environ.get(ENV_SEARCH_URL, "")


def resolve_cookie(cookie: str | None = None) -> str:
    """cookie：参数 → SEARCH_COOKIE"""
    return cookie or os.environ.get(ENV_COOKIE, "")


def resolve_save_dir(save_dir: str | None = None) -> str:
    """下载保存目录：参数 → MUSIC_DOWNLOAD_DIR → ~/Downloads"""
    d = save_dir or os.environ.get(ENV_DOWNLOAD_DIR, "") or "~/Downloads"
    return os.path.expanduser(d)
