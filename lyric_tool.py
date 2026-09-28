#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
lyric-tool 的 Python 重写版
从网易云音乐 / QQ 音乐获取歌词(LRC)并导出 SRT 字幕。
原版(C#): https://github.com/djj45/lyric-tool

用法:
    python3 lyric_tool.py <分享文本或链接>...   # 处理一个或多个链接
    python3 lyric_tool.py                       # 交互模式,同原版
"""

import base64
import json
import re
import sys
import urllib.request

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/100.0.4896.60 Safari/537.36"
)
TIMEOUT = 5  # 原版 C# 为 2 秒,这里稍放宽


# ---------------- HTTP ----------------

def http_get(url, referer=None):
    """GET 请求,失败返回 None(与 C# 版 Request 行为一致)"""
    headers = {"User-Agent": USER_AGENT}
    if referer:
        headers["Referer"] = referer
    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
            return resp.read().decode("utf-8", errors="replace")
    except Exception:
        return None


def get_final_url(url):
    """请求短链,返回最终跳转地址(等价 C# 的 GetResponseUri)"""
    try:
        req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
        with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
            return resp.geturl()
    except Exception:
        return None


# ---------------- LRC 解析(对应 C# 的 Lyric 静态类) ----------------

def to_list(lyric):
    """按行切分,每行保留结尾换行符(对应 C# 的 ToList)"""
    if not lyric:
        return []
    return lyric.splitlines(keepends=True)


def is_lyric(line):
    """是否为带时间标签的有效歌词行,如 [00:14.308]歌词"""
    m = re.match(r"\[(\d+):", line)
    if not m:
        return False
    content = line.split("]", 1)[1] if "]" in line else ""
    return content not in ("//\n", "\n", "")


def get_time(line):
    """取时间标签内容,如 '00:14.308'"""
    return line.split("[")[1].split("]")[0]


def get_text(line):
    """取时间标签后的歌词文本(含换行)"""
    return line.split("]", 1)[1]


def to_range_list(lyric_list, tlyric_list, mode):
    """按时间标签把原文和译文交错合并;mode='LT' 原文在前,'TL' 译文在前"""
    out = []
    t_times = [get_time(l) for l in tlyric_list if is_lyric(l)]
    t_lines = [l for l in tlyric_list if is_lyric(l)]
    for line in lyric_list:
        if not is_lyric(line):
            continue
        t = get_time(line)
        if t in t_times:
            tl = t_lines[t_times.index(t)]
            out.extend([line, tl] if mode == "LT" else [tl, line])
        else:
            out.append(line)
    return out


def get_valid_name(name):
    """过滤文件名非法字符(对应 C# 的 GetValidName,沿用 Windows 非法字符集)"""
    invalid = '<>:"/\\|?*'
    return "".join(c if c not in invalid and ord(c) >= 32 else "x" for c in name)


# ---------------- SRT 导出(对应 C# 的 Srt 静态类) ----------------

def trans_time(t):
    """[mm:ss.xx] -> 秒。兼容 2 位百分秒 / 3 位毫秒(对应 C# 的 TransTime)"""
    parts = re.split(r"[:.]", t)
    while len(parts) < 3:
        parts.append("0")
    m, s, ms = parts
    return int(m) * 60 + int(s) + int(ms) * 10 ** (-len(ms))


def extend_time(t):
    """时间 +8 秒,格式化为 SRT 的 mm:ss,mmm(对应 C# 的 ExtendTime)"""
    ms = t.split(".")[1].ljust(3, "0") if "." in t else "000"
    total = int(trans_time(t) + 8)
    return f"{total // 60:02d}:{total % 60:02d},{ms}"


def fmt_time(t):
    """LRC 时间 -> SRT 时间"""
    if "." not in t:
        t += ".000"
    m, rest = t.split(":")
    s, ms = rest.split(".")
    return f"{int(m):02d}:{int(s):02d},{ms.ljust(3, '0')}"


def write_srt(lines, path, song_name, singer):
    """把(可能是 原文+译文 拼接的)歌词行写成 SRT。

    与原版一致的处理:
    - 时间倒退超过 60 秒视为拼接的第二份歌词从头开始,上一条用 +8s 兜底结束
    - 相邻两句间隔超过 8 秒视为间奏,打印提示
    """
    count = 0
    pre_time = None
    pre_lyric = ""
    entries = []
    interludes = []

    for line in lines:
        if not is_lyric(line):
            continue
        if count == 0:
            pre_time = get_time(line)
            pre_lyric = get_text(line).rstrip("\n/")
            count += 1
            continue

        t = get_time(line)
        backward = trans_time(pre_time) - trans_time(t) > 60
        if trans_time(t) - trans_time(pre_time) > 8:
            interludes.append(f"[间奏] {pre_time} --> {t}")

        end = extend_time(pre_time) if backward else fmt_time(t)
        entries.append(
            f"{count}\n00:{fmt_time(pre_time)} --> 00:{end}\n{pre_lyric}\n"
        )

        pre_time = t
        pre_lyric = get_text(line).rstrip("\n/")
        count += 1

    if count:
        entries.append(
            f"{count}\n00:{fmt_time(pre_time)} --> 00:{extend_time(pre_time)}\n{pre_lyric}\n"
        )

    filename = f"{path}{get_valid_name(song_name)}-{get_valid_name(singer)}.srt"
    with open(filename, "w", encoding="utf-8") as f:
        f.write("\n".join(entries))
    for item in interludes:
        print(item)
    print(f"已写出: {filename} 共 {count} 条")
    return filename


# ---------------- 音乐基类(对应 C# 的 Music 抽象类) ----------------

class Music:
    source = ""

    @property
    def lyric_list(self):
        return to_list(self.lrc)

    @property
    def tlyric_list(self):
        return to_list(self.tlrc)

    @property
    def ltlyric_list(self):  # 原文在前,译文在后
        return to_list(self.lrc + self.tlrc)

    @property
    def tllyric_list(self):  # 译文在前,原文在后(原版 Main 使用的模式)
        return to_list(self.tlrc + self.lrc)

    @property
    def ltrange_lyric_list(self):  # 双语交错,原文在前
        return to_range_list(self.lyric_list, self.tlyric_list, "LT")

    @property
    def tlrange_lyric_list(self):  # 双语交错,译文在前
        return to_range_list(self.lyric_list, self.tlyric_list, "TL")


class NetEase(Music):
    source = "网易云"

    def __init__(self, song_id):
        self.id = song_id
        lyric_data = http_get(
            f"http://music.163.com/api/song/lyric?os=pc&id={song_id}&lv=-1&tv=-1"
        )
        info_data = http_get(
            f"http://music.163.com/api/song/detail/?id={song_id}&ids=[{song_id}]"
        )
        if not lyric_data:
            raise ValueError("歌词接口请求失败")
        self.lyric_json = json.loads(lyric_data)
        if not info_data:
            self.info_json = {}
        else:
            self.info_json = json.loads(info_data)

    @property
    def lrc(self):
        s = self.lyric_json.get("lrc", {}).get("lyric", "")
        return s if (not s or s.endswith("\n")) else s + "\n"

    @property
    def tlrc(self):
        s = self.lyric_json.get("tlyric", {}).get("lyric", "") or ""
        return s if (not s or s.endswith("\n")) else s + "\n"

    @property
    def song_name(self):
        songs = self.info_json.get("songs", [])
        return songs[0]["name"] if songs else f"网易{id}"

    @property
    def singer(self):
        songs = self.info_json.get("songs", [])
        return songs[0]["artists"][0]["name"] if songs else "未知歌手"


class QQ(Music):
    source = "QQ音乐"
    referer = "https://y.qq.com"

    def __init__(self, song_id):
        self.id = song_id
        if song_id.isdigit():  # 数字 id 与 songmid 两种参数名
            lyric_id_param, info_id_param = "musicid=", "songid="
        else:
            lyric_id_param = info_id_param = "songmid="
        common = "callback=MusicJsonCallback_lrc&g_tk=5381&format=jsonp"
        lyric_data = http_get(
            f"https://c.y.qq.com/lyric/fcgi-bin/fcg_query_lyric_new.fcg"
            f"?{common}&{lyric_id_param}{song_id}",
            referer=self.referer,
        )
        info_data = http_get(
            f"https://c.y.qq.com/v8/fcg-bin/fcg_play_single_song.fcg"
            f"?{common}&{info_id_param}{song_id}",
            referer=self.referer,
        )
        if not lyric_data:
            raise ValueError("歌词接口请求失败")
        self.lyric_json = self._parse_jsonp(lyric_data)
        self.info_json = self._parse_jsonp(info_data) if info_data else {}

        lrc_b64 = self.lyric_json.get("lyric", "")
        tlrc_b64 = self.lyric_json.get("trans", "")
        if not lrc_b64:
            raise ValueError("接口返回成功但歌词为空(可能因版权限制)")
        self._lrc = base64.b64decode(lrc_b64).decode("utf-8", errors="replace")
        self._tlrc = (
            base64.b64decode(tlrc_b64).decode("utf-8", errors="replace")
            if tlrc_b64
            else ""
        )

    @staticmethod
    def _parse_jsonp(text):
        """去掉 MusicJsonCallback_lrc(...) 包装,解析内部 JSON"""
        s = text.strip()
        if s.startswith("MusicJsonCallback_lrc("):
            s = s[len("MusicJsonCallback_lrc(") :].rstrip(")")
        return json.loads(s)

    @property
    def lrc(self):
        return self._lrc if self._lrc.endswith("\n") else self._lrc + "\n"

    @property
    def tlrc(self):
        if not self._tlrc:
            return ""
        return self._tlrc if self._tlrc.endswith("\n") else self._tlrc + "\n"

    @property
    def song_name(self):
        data = self.info_json.get("data", [])
        return data[0]["name"] if data else f"QQ{self.id}"

    @property
    def singer(self):
        data = self.info_json.get("data", [])
        return data[0]["singer"][0]["name"] if data else "未知歌手"


# ---------------- 链接识别(对应 C# 的 Lyric.GetMusic) ----------------

def get_music(text):
    """从分享文本/链接中识别歌曲并返回 Music 对象,失败返回 None

    支持:
      https://music.163.com/#/song?id=1469327796
      https://music.163.com/song?id=1384482575&userid=...
      https://y.qq.com/n/ryqq/songDetail/004emQMs09Z1lz
      https://y.qq.com/n/ryqq_v2/songDetail/004emQMs09Z1lz
      https://c.y.qq.com/base/fcgi-bin/u?__=xxxxx   (短链,自动跟跳转)
      https://c6.y.qq.com/base/fcgi-bin/u?__=xxxxx  (短链 c/c1...c6 等子域)
    """
    m = re.search(
        r"(https?://[-A-Za-z0-9+&@#/%?=~_|!:,.;]+[-A-Za-z0-9+&@#/%=~_|])", text
    )
    if not m:
        return None
    url = m.group(1)

    # QQ 短链(c.y.qq.com / c6.y.qq.com 等子域),跟跳转后用最终地址重新识别
    if re.search(r"//[\w.]+\.y\.qq\.com/base/fcgi-bin/u\?", url):
        final = get_final_url(url)
        return get_music(final) if final else None

    if "y.qq.com" in url:
        sid = re.search(r"songDetail/([0-9a-zA-Z]+)", url)
        if not sid:  # 兼容老式跳转的参数形式
            sid = re.search(r"songid=(\d+)", url) or re.search(
                r"songmid=([0-9a-zA-Z]+)", url
            )
        return QQ(sid.group(1)) if sid else None

    sid = re.search(r"id=(\d+)", url)
    return NetEase(sid.group(1)) if sid else None


# ---------------- 入口(对应 C# 的 Start.Main) ----------------

def process(text):
    try:
        music = get_music(text)
    except Exception as e:
        print(f"[失败] {text}\n       {e}")
        return None
    if music is None:
        print(f"[失败] {text}\n       输入链接错误")
        return None

    print(f"[成功] {music.source}: {music.song_name} - {music.singer}")
    print(f"       原文 {len(music.lyric_list)} 行, 译文 {len(music.tlyric_list)} 行")
    for line in music.tllyric_list[:6]:
        print(f"       {line.rstrip()}")
    write_srt(music.tllyric_list, "", music.song_name, music.singer)
    return music


def main(argv):
    print("lyric-tool (Python 版)  https://github.com/djj45/lyric-tool")
    if argv:
        for text in argv:
            process(text)
    else:
        print("请输入网易云音乐或者qq音乐的链接")
        while True:
            try:
                text = input()
            except EOFError:
                break
            if not text:
                break
            process(text)


if __name__ == "__main__":
    main(sys.argv[1:])
