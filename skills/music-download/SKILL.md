---
name: music-download
description: 音乐下载 - 搜歌 → 选品质 → 下载到本地的完整引导流程，基于 music-search MCP 工具。
disable-model-invocation: true
---

## User Input

```text
$ARGUMENTS
```

> 格式：`/music-download 歌名 [歌手]`（歌手可省略）
> 示例：`/music-download 童话`、`/music-download 晴天 周杰伦`
> 若 `$ARGUMENTS` 为空或无法推断出歌名，向用户询问，**不得猜测**。

---

## 前置条件

依赖 music-search MCP server 提供的三个工具：`music_search`、`get_download_url`、`download_file`。
若工具不可用或返回 `[未配置]`（缺 `SEARCH_URL` / `SEARCH_COOKIE` 等环境变量），如实转告用户并中止，由用户完成配置后重试。

---

## 执行步骤

1. **解析输入**：从 `$ARGUMENTS` 拆出歌名与歌手（歌手可省略）。keyword 用「歌名 歌手」拼接；无歌手时只用歌名。
2. **搜索**：调用 `music_search(keyword=<拼接结果>)`，其余参数保持默认。
   - 无结果（列表为空 / total 为 0）：告知用户并建议更换关键词（如补上歌手、改用别名），中止本次流程。
3. **呈现候选**：把结果汇总为编号列表展示给用户，每项包含：歌名、歌手、专辑、时长、可用音质（`minfo` 中各 `format`/`bitrate`/`size`）。等用户选定**序号**和**音质**。
   - 用户未指定音质时：默认推荐该曲目 `minfo` 中的最高可用音质（优先无损 flac，否则最高码率），并向用户说明该推荐。
4. **取下载链接**：用户确认后，取选中项的字段原样传参调用 `get_download_url`：
   - `songid` ← 结果项 `id`
   - `time` ← 结果项 `time`
   - `sign` ← 结果项 `sign`（**与该 `time` 绑定，必须原样传递，禁止编造或用当前时间戳代替**）
   - `format` / `bitrate` ← 用户所选 `minfo` 音质
5. **下载保存**：调用 `download_file(url=<上一步返回的链接>, filename="歌名-歌手")`。
   - `save_dir` 保持默认，除非用户另行指定。
6. **汇报结果**：输出保存的完整路径与文件大小。

---

## 边界与纪律

- 任一步工具返回以 `[失败]` 开头的信息时，如实转告用户并**立即中止**后续步骤，不要自行重试编造参数。
- `id`/`time`/`sign` 只能来自本次 `music_search` 的返回项，禁止凭记忆或推测填写。
- 搜索接口若返回鉴权类失败（如 cookie 失效），提示用户更新 `SEARCH_COOKIE` 后重试。
