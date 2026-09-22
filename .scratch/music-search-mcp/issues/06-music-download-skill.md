# 06: 新增 music-download skill：搜歌 → 选品质 → 下载到本地的完整引导流程

**What to build:** 新建 `skills/music-download/SKILL.md`，结构仿照 `skills/smoke/SKILL.md`（frontmatter 含 name/description/`disable-model-invocation`，正文含 User Input `$ARGUMENTS` 段和分步执行流程）。skill 引导 AI 完成完整链路：解析用户输入的歌名、歌手（`/music-download 歌名 歌手`，歌手可省略；参数缺失或无法推断时向用户询问，不得猜测）→ 调用 `music_search`（keyword 拼歌名+歌手）→ 把结果汇总为编号列表呈现给用户（每项含歌名、歌手、专辑、时长、`minfo` 可用音质）→ 用户选定序号和音质后，取该项的 `id`/`time`/`sign` 及所选 `format`/`bitrate` 调用 `get_download_url` → 拿下载链接调用 `download_file` 保存到本地（文件名用「歌名-歌手」，`save_dir` 默认即可，除非用户另行指定）→ 输出保存路径与文件大小。需覆盖的边界：搜索无结果时提示换关键词；用户未指定音质时默认推荐最高可用音质并说明；`sign`/`time` 必须原样取自搜索结果项，禁止编造；任一步工具返回失败提示时如实转告用户并中止后续步骤。

**Blocked by:** 05: download_file 工具：把下载链接保存为本地文件

**Status:** done

- [x] `skills/music-download/SKILL.md` 存在，frontmatter 与整体结构仿 `skills/smoke/SKILL.md`（含 `$ARGUMENTS` 输入约定）
- [x] 流程完整覆盖：解析输入 → `music_search` → 编号列表汇总 → 用户选序号与音质 → `get_download_url` → `download_file` → 输出保存路径与文件大小
- [x] 明确字段映射规则：`songid`/`time`/`sign` 取自选中结果项的 `id`/`time`/`sign`，`format`/`bitrate` 取自用户所选 `minfo` 音质；`download_file` 的 `filename` 用「歌名-歌手」
- [x] 覆盖边界情况：无结果、缺参数时的追问、音质默认推荐策略、失败信息如实透传并中止链路
