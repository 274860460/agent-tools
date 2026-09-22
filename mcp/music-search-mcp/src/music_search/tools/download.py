"""下载工具：get_download_url 查下载链接，download_file 流式落盘。"""

import os
import re
import urllib.parse

import httpx

from music_search.config import resolve_cookie, resolve_download_url, resolve_save_dir
from music_search.http import _USER_AGENT, RequestError, post_json

_CHUNK_SIZE = 256 * 1024
_DOWNLOAD_TIMEOUT = 120


def register(mcp):
    """注册下载相关工具"""

    @mcp.tool()
    def get_download_url(
        songid: int | str,
        time: int | str,
        sign: str,
        platform: str = "kuwo",
        format: str = "mp3",
        bitrate: int = 320,
        url: str | None = None,
        cookie: str | None = None,
    ) -> str:
        """查询歌曲下载链接，成功时只返回下载 URL。

        典型流程第二步：先用 music_search 搜索，从选中结果项取字段原样传入——
        songid←结果项 id，time←结果项 time，sign←结果项 sign
        （sign 与该 time 绑定，禁止用当前时间戳代替或自行编造）；
        format/bitrate 取自该项 minfo 中用户选择的音质（如 mp3/320、flac/817）。

        Args:
            songid: 歌曲 ID（必填），取 music_search 结果项的 id
            time: 时间戳（必填），取 music_search 结果项的 time，不做兜底
            sign: 签名（必填），取 music_search 结果项的 sign
            platform: 平台，默认 kuwo
            format: 音频格式，默认 mp3（可选值见结果项 minfo）
            bitrate: 码率，默认 320（可选值见结果项 minfo）
            url: 下载链接接口地址，缺省依次读 SEARCH_DOWNLOAD_URL、SEARCH_URL
            cookie: 会话 cookie，缺省读环境变量 SEARCH_COOKIE
        """
        target = resolve_download_url(url)
        if not target:
            return ("[未配置] 缺少下载链接接口地址：请传 url 参数，"
                    "或配置环境变量 SEARCH_DOWNLOAD_URL / SEARCH_URL")
        cookie_value = resolve_cookie(cookie)

        try:
            payload = post_json(
                target,
                data={
                    "platform": platform,
                    "songid": str(songid),
                    "format": format,
                    "bitrate": str(bitrate),
                    "time": str(time),
                    "sign": sign,
                },
                cookie=cookie_value,
            )
        except RequestError as e:
            return f"[失败] {e}"

        if payload.get("code") != 0:
            return (f"[失败] 获取下载链接失败：code={payload.get('code')}，"
                    f"msg={payload.get('msg')!r}")
        download_url = (payload.get("data") or {}).get("url")
        if not download_url:
            return f"[失败] 响应缺少下载链接，msg={payload.get('msg')!r}"
        return download_url

    @mcp.tool()
    def download_file(
        url: str,
        filename: str | None = None,
        save_dir: str | None = None,
    ) -> str:
        """把下载链接保存为本地文件（流式写入，重名自动加序号）。

        典型流程第三步：把 get_download_url 返回的链接传给本工具保存到本地。

        Args:
            url: 文件下载地址（必填），通常即 get_download_url 的返回值
            filename: 保存文件名（可选，不含扩展名也可——自动从 URL 推断补上）
            save_dir: 保存目录（可选，缺省读 MUSIC_DOWNLOAD_DIR，再缺省 ~/Downloads）
        """
        target_dir = resolve_save_dir(save_dir)
        try:
            os.makedirs(target_dir, exist_ok=True)
        except OSError as e:
            return f"[失败] 创建保存目录失败：{e}"

        name = _resolve_filename(url, filename)
        path = _dedupe_path(os.path.join(target_dir, name))
        tmp_path = path + ".part"

        size = 0
        try:
            with httpx.stream("GET", url, timeout=_DOWNLOAD_TIMEOUT,
                              follow_redirects=True,
                              headers={"user-agent": _USER_AGENT}) as resp:
                if resp.status_code != 200:
                    return f"[失败] 下载返回 HTTP {resp.status_code}"
                with open(tmp_path, "wb") as f:
                    for chunk in resp.iter_bytes(_CHUNK_SIZE):
                        f.write(chunk)
                        size += len(chunk)
        except httpx.TimeoutException:
            _cleanup(tmp_path)
            return f"[失败] 下载超时（{_DOWNLOAD_TIMEOUT}s）：{url}"
        except httpx.RequestError as e:
            _cleanup(tmp_path)
            return f"[失败] 网络错误：{e}"
        except OSError as e:
            _cleanup(tmp_path)
            return f"[失败] 写入文件失败：{e}"
        except Exception as e:
            _cleanup(tmp_path)
            return f"[失败] 下载出错：{type(e).__name__}: {e}"

        try:
            os.replace(tmp_path, path)
        except OSError as e:
            _cleanup(tmp_path)
            return f"[失败] 保存文件失败：{e}"

        return f"[成功] 已保存：{path}（{_human_size(size)}）"


_INVALID_CHARS = re.compile(r'[\\/:*?"<>|]')


def _resolve_filename(url: str, filename: str | None) -> str:
    """确定保存文件名：补扩展名；都推断不出时用 URL 末段。"""
    url_name = ""
    try:
        url_path = urllib.parse.urlparse(url).path
        url_name = os.path.basename(urllib.parse.unquote(url_path))
    except Exception:
        pass

    name = (filename or "").strip() or url_name or "download"
    name = _INVALID_CHARS.sub("_", name)

    if not os.path.splitext(name)[1]:
        ext = os.path.splitext(url_name)[1]
        if ext:
            name += ext
    return name


def _dedupe_path(path: str) -> str:
    """目标已存在时自动追加序号（如 歌名-2.mp3），不覆盖已有文件。"""
    if not os.path.exists(path):
        return path
    stem, ext = os.path.splitext(path)
    n = 2
    while os.path.exists(f"{stem}-{n}{ext}"):
        n += 1
    return f"{stem}-{n}{ext}"


def _cleanup(tmp_path: str):
    """失败时清理不完整的临时文件，不留半截文件。"""
    try:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)
    except OSError:
        pass


def _human_size(size: int) -> str:
    if size >= 1024 * 1024:
        return f"{size / 1024 / 1024:.2f} MB"
    if size >= 1024:
        return f"{size / 1024:.1f} KB"
    return f"{size} B"
