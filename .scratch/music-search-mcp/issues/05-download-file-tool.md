# 05: download_file 工具：把下载链接保存为本地文件

**What to build:** 在 server 上注册 `download_file` 工具，输入 `url`（必填，通常即 `get_download_url` 返回的下载链接）、`filename`（可选，不含扩展名也可——从 URL 推断扩展名补上；都推断不出时用 url 末段）、`save_dir`（可选，未传时读环境变量 `MUSIC_DOWNLOAD_DIR`，再缺省 `~/Downloads`）。流式下载写入本地（分块读写，避免大文件撑爆内存），带超时与失败重读错误处理；目标文件已存在时自动追加序号避免覆盖。成功后返回保存的完整路径与文件大小；失败（网络错误、非 200、写入失败）返回可读错误信息。

**Blocked by:** 03: get_download_url 工具：查询歌曲下载链接

**Status:** done

- [x] 传入 `get_download_url` 返回的 URL 能下载出可播放的音频文件，返回完整保存路径和文件大小
- [x] `filename`、`save_dir` 可覆盖；`save_dir` 解析顺序：参数 → `MUSIC_DOWNLOAD_DIR` → `~/Downloads`
- [x] 分块流式写入；目标重名时自动加序号（如 `歌名-2.mp3`）不覆盖已有文件
- [x] 网络错误 / 非 200 响应 / 磁盘写入失败时返回可读错误，不留半截文件（失败时清理不完整的临时文件）
