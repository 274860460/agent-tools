"""music_search 工具：POST 表单搜索歌曲，返回精简结果列表。"""

import json

from music_search.config import resolve_cookie, resolve_search_url
from music_search.http import RequestError, post_json

_MAX_RESULT_CHARS = 12000
_MAX_PAGE = 10
_MAX_SIZE = 50

_HINT = (
    "提示：选中歌曲后，把该项的 id/time/sign 原样传给 get_download_url "
    "（songid←id，sign 与 time 绑定，禁止编造或用当前时间戳代替），"
    "format/bitrate 取自 minfo 中所选音质。"
)


def register(mcp):
    """注册搜索工具"""

    @mcp.tool()
    def music_search(
        keyword: str,
        platform: str = "kuwo",
        page: int = 1,
        size: int = 20,
        url: str | None = None,
        cookie: str | None = None,
    ) -> str:
        """搜索歌曲，返回精简结果列表（含 id/name/artist/album_name/duration/minfo/time/sign 和 total）。

        典型流程第一步：搜索后从结果项取 id/time/sign，连同所选音质 format/bitrate
        一起传给 get_download_url 获取下载链接。

        Args:
            keyword: 搜索关键词（必填），如歌名或「歌名 歌手」
            platform: 平台，默认 kuwo
            page: 页码，默认 1，上限 10（防止翻页过深）
            size: 每页条数，默认 20，上限 50（防止结果过大）
            url: 搜索接口地址，缺省读环境变量 SEARCH_URL
            cookie: 会话 cookie，缺省读环境变量 SEARCH_COOKIE
        """
        target = resolve_search_url(url)
        if not target:
            return "[未配置] 缺少搜索接口地址：请传 url 参数，或配置环境变量 SEARCH_URL"
        cookie_value = resolve_cookie(cookie)

        clamped = ""
        if page > _MAX_PAGE or size > _MAX_SIZE:
            clamped = f"（page/size 已钳制到上限 {_MAX_PAGE}/{_MAX_SIZE}）"
        page = max(1, min(page, _MAX_PAGE))
        size = max(1, min(size, _MAX_SIZE))

        try:
            payload = post_json(
                target,
                data={"platform": platform, "keyword": keyword,
                      "page": page, "size": size},
                cookie=cookie_value,
            )
        except RequestError as e:
            return f"[失败] {e}"

        if payload.get("code") != 0:
            raw = json.dumps(payload, ensure_ascii=False)[:2000]
            return (f"[失败] 接口返回 code={payload.get('code')}，"
                    f"msg={payload.get('msg')!r}，原始响应（截断）：\n{raw}")

        data = payload.get("data") or {}
        items = data.get("list") or []
        results = [
            {
                "id": item.get("id"),
                "name": item.get("name"),
                "artist": item.get("artist"),
                "album_name": item.get("album_name"),
                "duration": item.get("duration"),
                "minfo": item.get("minfo"),
                "time": item.get("time"),
                "sign": item.get("sign"),
            }
            for item in items
        ]
        total = data.get("total", 0)
        output = json.dumps({"total": total, "list": results},
                            ensure_ascii=False, separators=(",", ":"))
        if len(output) > _MAX_RESULT_CHARS:
            # 截断保护：整条丢弃末尾记录，避免把某条的 time/sign 切残
            while results and len(output) > _MAX_RESULT_CHARS:
                results.pop()
                output = json.dumps({"total": total, "list": results},
                                    ensure_ascii=False, separators=(",", ":"))
            output += f"... [已截断，仅展示前 {len(results)} 条] "
        return output + clamped + "\n\n" + _HINT
