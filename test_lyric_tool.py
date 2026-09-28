#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""lyric_tool 的逻辑分支测试"""

import re
import lyric_tool as lt

ok = 0
fail = 0


def check(name, cond, detail=""):
    global ok, fail
    if cond:
        ok += 1
        print(f"  PASS  {name}")
    else:
        fail += 1
        print(f"  FAIL  {name}  {detail}")


print("== 1. get_final_url 能否跟踪真实跳转 ==")
final = lt.get_final_url("http://github.com")
check("http->https 跳转", final is not None and final.startswith("https://github.com"), f"got {final}")

print("== 2. 短链分支(模拟一条新鲜短链的跳转结果) ==")
# QQ 短链 c.y.qq.com / c6.y.qq.com 等子域,跳转后形如:
#   .../songDetail/004emQMs09Z1lz?ADTAG=... (songDetail 路径,2026 年实测形式)
#   ...?songmid=xxx / ...?songid=123        (老式参数形式)
_orig = lt.get_final_url
lt.get_final_url = lambda url: (
    "https://y.qq.com/n/ryqq_v2/songDetail/004emQMs09Z1lz?ADTAG=qr&songtype=0"
)
m = lt.get_music("https://c6.y.qq.com/base/fcgi-bin/u?__=FAKE789")
check("c6 子域 + songDetail 路径", isinstance(m, lt.QQ) and m.id == "004emQMs09Z1lz",
      f"got {type(m).__name__} id={getattr(m, 'id', None)}")
lt.get_final_url = lambda url: (
    "https://i.y.qq.com/v2/playsong.html?songmid=004emQMs09Z1lz&ADTAG=qr"
)
m = lt.get_music("https://c.y.qq.com/base/fcgi-bin/u?__=FAKE123")
check("c 子域 + songmid 正则提取", isinstance(m, lt.QQ) and m.id == "004emQMs09Z1lz",
      f"got {type(m).__name__} id={getattr(m, 'id', None)}")
lt.get_final_url = lambda url: "https://i.y.qq.com/v2/playsong.html?songid=680279"
m = lt.get_music("https://c6.y.qq.com/base/fcgi-bin/u?__=FAKE456")
check("songid 正则提取", isinstance(m, lt.QQ) and m.id == "680279",
      f"got {type(m).__name__} id={getattr(m, 'id', None)}")
lt.get_final_url = _orig

print("== 3. QQ 数字 musicid 分支(真实请求) ==")
m = lt.QQ("680279")
check("歌词获取", len(m.lyric_list) > 10, f"仅 {len(m.lyric_list)} 行")
check("歌曲名", m.song_name == "烟花易冷", m.song_name)
check("歌手", m.singer == "周杰伦", m.singer)

print("== 4. LRC/SRT 工具函数 ==")
check("to_list 保留换行", lt.to_list("a\nb\n") == ["a\n", "b\n"])
check("is_lyric 有效行", lt.is_lyric("[00:14.308]我们去看日落\n"))
check("is_lyric 过滤元数据", not lt.is_lyric("[by:某人]\n"))
check("is_lyric 过滤空行", not lt.is_lyric("[00:14.308]\n"))
check("is_lyric 过滤纯音乐标记", not lt.is_lyric("[00:14.308]//\n"))
check("trans_time 2位百分秒", abs(lt.trans_time("01:30.50") - 90.5) < 1e-9)
check("trans_time 3位毫秒", abs(lt.trans_time("01:30.500") - 90.5) < 1e-9)
check("extend_time +8s", lt.extend_time("01:00.00") == "01:08,000", lt.extend_time("01:00.00"))
check("fmt_time SRT格式", lt.fmt_time("01:02.3") == "01:02,300", lt.fmt_time("01:02.3"))
check("get_valid_name 过滤非法字符", lt.get_valid_name('a/b\\c:d') == "axbxcxd")

print("== 5. 双语交错合并 ==")
lrc = "[00:01.00]hello\n[00:02.00]world\n"
tlrc = "[00:01.00]你好\n"
inter = lt.to_range_list(lt.to_list(lrc), lt.to_list(tlrc), "LT")
check("LT 交错", inter == ["[00:01.00]hello\n", "[00:01.00]你好\n", "[00:02.00]world\n"], str(inter))
inter = lt.to_range_list(lt.to_list(lrc), lt.to_list(tlrc), "TL")
check("TL 交错", inter == ["[00:01.00]你好\n", "[00:01.00]hello\n", "[00:02.00]world\n"], str(inter))

print("== 6. 已生成 SRT 文件格式抽查 ==")
import glob
for f in sorted(glob.glob("*.srt")):
    text = open(f, encoding="utf-8").read()
    blocks = [b for b in text.split("\n\n") if b.strip()]
    times = re.findall(r"(\d{2}:\d{2}:\d{2},\d{3}) --> (\d{2}:\d{2}:\d{2},\d{3})", text)
    idx_ok = all(b.splitlines()[0] == str(i + 1) for i, b in enumerate(blocks))
    fmt_ok = len(times) == len(blocks) and all(len(s) == 12 and len(e) == 12 for s, e in times)
    print(f"  {f}: {len(blocks)} 条, 序号连续={idx_ok}, 时间戳格式={fmt_ok}")
    check(f"{f} SRT结构", idx_ok and fmt_ok and len(blocks) > 0)

print(f"\n结果: {ok} 通过, {fail} 失败")
exit(1 if fail else 0)
