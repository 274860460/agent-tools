"""HTTP 公共逻辑：请求头构造、cookie、POST 表单与错误处理（各工具共用）。"""

import json

import httpx

_USER_AGENT = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
               "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/153.0.0.0 Safari/537.36")

_DEFAULT_HEADERS = {
    "accept": "*/*",
    "accept-language": "zh-CN,zh;q=0.9,en;q=0.8",
    "content-type": "application/x-www-form-urlencoded;charset=UTF-8",
    "priority": "u=1, i",
    "sec-ch-ua": '"Google Chrome";v="153", "Not_A Brand";v="8", "Chromium";v="153"',
    "sec-ch-ua-mobile": "?0",
    "sec-ch-ua-platform": '"macOS"',
    "sec-fetch-dest": "empty",
    "sec-fetch-mode": "cors",
    "sec-fetch-site": "same-origin",
    "user-agent": _USER_AGENT,
}

_MAX_BODY_PREVIEW = 500


class RequestError(Exception):
    """可读的错误信息，工具层直接返回给用户，不抛堆栈。"""


def _origin_of(url: str) -> str:
    try:
        u = httpx.URL(url)
        if u.scheme and u.host:
            port = f":{u.port}" if u.port else ""
            return f"{u.scheme}://{u.host}{port}"
    except Exception:
        pass
    return ""


def post_form(url: str, data: dict, cookie: str = "", timeout: float = 30) -> str:
    """发送 POST 表单请求，返回响应文本；失败抛 RequestError（信息可直接展示）。"""
    headers = dict(_DEFAULT_HEADERS)
    origin = _origin_of(url)
    if origin:
        headers["origin"] = origin
    if cookie:
        headers["cookie"] = cookie

    try:
        resp = httpx.post(url, data=data, headers=headers, timeout=timeout,
                          follow_redirects=True)
    except httpx.TimeoutException:
        raise RequestError(f"请求超时（{timeout:.0f}s）：{url}")
    except httpx.RequestError as e:
        raise RequestError(f"网络错误：{e}")

    if resp.status_code != 200:
        preview = resp.text[:_MAX_BODY_PREVIEW]
        raise RequestError(f"HTTP {resp.status_code}，响应预览：{preview}")
    return resp.text


def post_json(url: str, data: dict, cookie: str = "", timeout: float = 30) -> dict:
    """POST 表单并解析 JSON 响应；网络错误/非 JSON 抛 RequestError。"""
    text = post_form(url, data, cookie, timeout)
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        raise RequestError(f"响应不是 JSON，原始文本（截断）：\n{text[:2000]}")
