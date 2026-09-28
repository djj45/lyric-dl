# lyric-dl

从网易云音乐 / QQ 音乐下载歌词并导出 SRT 字幕。[lyric-tool](https://github.com/djj45/lyric-tool)（C#）的 Python 重写版，零第三方依赖，仅用标准库。

## 用法

```bash
# 处理一个或多个链接
python3 lyric_tool.py "https://music.163.com/#/song?id=316100"

# 交互模式（同原版）
python3 lyric_tool.py
```

在当前目录生成 `歌名-歌手.srt`，自动检测并打印间奏（相邻两句间隔 > 8 秒）。

## 支持的链接形式

- 网易云网页链接：`https://music.163.com/#/song?id=1469327796`
- 网易云 App 分享文本：`分享xxx的单曲《xxx》: https://y.music.163.com/m/song?id=26096272&...`
- QQ 音乐网页链接：`https://y.qq.com/n/ryqq/songDetail/004emQMs09Z1lz`（含 `ryqq_v2` 路径）
- QQ 音乐短链：`https://c.y.qq.com/base/fcgi-bin/u?__=xxxxx`（自动跟跳转，兼容 `c`/`c1`…`c6` 等子域）

## 接口

| 音源 | 歌词接口 | 备注 |
|---|---|---|
| 网易云 | `music.163.com/api/song/lyric?os=pc&id={id}&lv=-1&tv=-1` | JSON 直出，`tlyric` 为译文 |
| QQ 音乐 | `c.y.qq.com/lyric/fcgi-bin/fcg_query_lyric_new.fcg` | JSONP + base64(UTF-8)，需 `Referer: https://y.qq.com`，songmid / 数字 musicid 均可 |

## 代码结构

- `lyric_tool.py` — 主程序：链接识别、歌词获取（`NetEase` / `QQ`）、LRC 解析、双语交错合并（原文/译文六种组合模式）、LRC→SRT 转换（时间倒退检测、间奏检测、+8s 兜底结束时间）
- `test_lyric_tool.py` — 测试：`python3 test_lyric_tool.py`，含真实接口请求与纯逻辑用例

## 相对原版（C#）的差异

- 修复：QQ 短链只认 `c.y.qq.com` 子域、跳转后只认 `songmid=`/`songid=` 参数形式的问题（现兼容 `c6.y.qq.com` 等子域及 `songDetail/xxx` 路径形式）
- 修复：死短链导致空引用崩溃，现返回"输入链接错误"
- 修复：SRT 中写入字面量 `\n` 字符的问题，输出标准 SRT 格式
- QQ 接口返回成功但歌词为空（版权/VIP）时明确报错，而非静默生成空文件
