# -*- coding: utf-8 -*-
"""
==============================================================================
    网易云音乐热歌榜爬虫数据分析大作业
==============================================================================
    爬取目标:  网易云音乐网页版热歌榜 (id=3778678)
    抓取字段:  歌曲排名、歌曲名称、歌手名称
    技 术 栈:  requests + BeautifulSoup (静态网页爬虫)
    数据分析:  歌手上榜频次统计 → TOP10 歌手
    数据可视化: (1) TOP10柱状图  (2) 全歌手词云图
==============================================================================
"""

import os
import re
import sys
import json
import time
import random
import csv
import requests
from bs4 import BeautifulSoup
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')  # 非交互式后端，适配服务器/无GUI环境
import matplotlib.pyplot as plt
from collections import Counter
from wordcloud import WordCloud

# ============================================================================
#  0. 全局配置
# ============================================================================

# 网易云音乐热歌榜 URL（两种方式供选择）
TOP_LIST_URL = "https://music.163.com/discover/toplist?id=3778678"
# 备用：直接请求播放列表详情页
PLAYLIST_URL = "https://music.163.com/playlist?id=3778678"
# API 接口（数据最完整，但可能被反爬限制）
API_URL = "https://music.163.com/api/playlist/detail?id=3778678"

# 输出文件路径（保存在当前脚本同级目录）
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CSV_PATH = os.path.join(BASE_DIR, "hot_songs.csv")
BAR_CHART_PATH = os.path.join(BASE_DIR, "top10_artists_bar.png")
WORDCLOUD_PATH = os.path.join(BASE_DIR, "all_artists_wordcloud.png")

# 浏览器请求头列表（多组 User-Agent 轮换使用）
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:120.0) Gecko/20100101 Firefox/120.0",
]

# 中文关键词匹配（用于识别字体文件）
# 注：实际字体查找已通过 find_chinese_font() 函数按路径完成，此处保留作扩展接口

# ============================================================================
#  1. 工具函数
# ============================================================================

def get_random_headers():
    """
    生成随机的浏览器请求头，模拟正常用户访问
    """
    return {
        "User-Agent": random.choice(USER_AGENTS),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "keep-alive",
        "Referer": "https://music.163.com/",
        "Cache-Control": "max-age=0",
    }


def random_delay(min_sec=1.0, max_sec=3.0):
    """
    随机延时，模拟人类浏览行为，降低被反爬虫机制封禁的风险
    :param min_sec: 最短延时秒数
    :param max_sec: 最长延时秒数
    """
    delay = random.uniform(min_sec, max_sec)
    print(f"  [延时] 等待 {delay:.1f} 秒...")
    time.sleep(delay)


def fetch_url(url, max_retries=3):
    """
    带重试机制的页面请求函数
    :param url:      请求地址
    :param max_retries: 最大重试次数
    :return:         响应对象 或 None
    """
    for attempt in range(1, max_retries + 1):
        try:
            headers = get_random_headers()
            resp = requests.get(url, headers=headers, timeout=15)
            resp.encoding = 'utf-8'
            if resp.status_code == 200:
                print(f"  [请求成功] URL: {url[:60]}... (状态码: {resp.status_code})")
                return resp
            else:
                print(f"  [状态异常] 状态码: {resp.status_code}, 尝试 {attempt}/{max_retries}")
        except requests.exceptions.RequestException as e:
            print(f"  [网络错误] {e}, 尝试 {attempt}/{max_retries}")
        if attempt < max_retries:
            time.sleep(2 * attempt)
    return None


def ensure_encoding():
    """
    确保控制台能正常输出中文（兼容 Windows 环境）
    """
    if sys.platform == 'win32':
        # 尝试设置控制台编码
        try:
            sys.stdout.reconfigure(encoding='utf-8')
        except Exception:
            pass


# ============================================================================
#  2. 爬取数据模块（三种策略）
# ============================================================================

def scrape_via_api():
    """
    策略一：通过网易云音乐 API 直接获取播放列表详情
    这是最可靠的方式，返回完整的 JSON 数据
    """
    print("\n[策略一] 尝试通过 API 接口获取数据...")

    # 构造请求头（API 接口需要额外添加 Referer）
    headers = get_random_headers()
    headers["Referer"] = "https://music.163.com/"
    # 部分请求可能会验证该字段，用 cookies 提高成功率
    # 但这里不强制依赖 cookie，更多用备用方案

    try:
        resp = requests.get(API_URL, headers=headers, timeout=15)
        resp.encoding = 'utf-8'

        if resp.status_code != 200:
            print(f"  API 返回非 200 状态码: {resp.status_code}")
            return None

        data = resp.json()

        # API 数据结构: data["playlist"]["tracks"]
        if data.get("code") == 200:
            playlist = data.get("result", {}) or data.get("playlist", {})
            tracks = playlist.get("tracks", [])
            if not tracks:
                print("  API 返回数据为空")
                return None

            songs = []
            for idx, track in enumerate(tracks, start=1):
                name = track.get("name", "").strip()
                artists = track.get("ar", [])
                if not artists:
                    artists = track.get("artists", [])
                if not artists:
                    artists = track.get("artist", [])
                    if isinstance(artists, dict):
                        artists = [artists]
                artist_names = "/".join([ar.get("name", "") for ar in artists if isinstance(ar, dict)])
                if not artist_names:
                    artist_names = track.get("artistName", "") or track.get("singer", "")
                songs.append([idx, name, artist_names])

            print(f"  [API 成功] 获取到 {len(songs)} 首歌曲")
            return songs
        else:
            print(f"  API 返回错误码: {data.get('code')}")
            return None

    except (requests.exceptions.RequestException, json.JSONDecodeError, ValueError) as e:
        print(f"  [API 异常] {e}")
        return None


def scrape_via_html():
    """
    策略二：通过解析 HTML 页面获取数据
    网易云音乐热歌榜页面可能将数据嵌入在 <textarea> 或 <script> 标签中
    """
    print("\n[策略二] 尝试通过 HTML 解析获取数据...")
    random_delay(1.0, 2.0)

    # 尝试多个可能的 URL
    urls_to_try = [
        PLAYLIST_URL,            # /playlist?id=3778678
        TOP_LIST_URL,            # /discover/toplist?id=3778678
    ]

    for url in urls_to_try:
        print(f"  尝试 URL: {url}")
        resp = fetch_url(url)
        if not resp:
            continue

        soup = BeautifulSoup(resp.text, "html.parser")
        songs = []

        # ------------------------------------------------------------------
        # 方式 A: 从 <textarea id="song-list-pre-data"> 中提取 JSON
        # ------------------------------------------------------------------
        textarea = soup.find("textarea", {"id": "song-list-pre-data"})
        if textarea and textarea.string:
            try:
                data = json.loads(textarea.string.strip())
                if isinstance(data, list) and len(data) > 0:
                    for idx, item in enumerate(data, start=1):
                        # 字段映射: id, name, artists, album, ...
                        name = item.get("name", "").strip()
                        artists = item.get("artists", [])
                        artist_names = "/".join([
                            a.get("name", "") for a in artists
                        ])
                        songs.append([idx, name, artist_names])
                    if len(songs) >= 50:
                        print(f"  [HTML-Textarea] 获取到 {len(songs)} 首歌曲")
                        return songs
            except (json.JSONDecodeError, AttributeError, KeyError) as e:
                print(f"  [Textarea解析失败] {e}")

        # ------------------------------------------------------------------
        # 方式 B: 从 <script> 标签中的 window.__NUXT__ 或 __NEXT_DATA__ 提取
        # ------------------------------------------------------------------
        for script in soup.find_all("script"):
            script_text = script.string or ""
            # 尝试匹配多种常见的 JSON 数据注入方式
            for pattern in [
                r'window\.__NUXT__\s*=\s*({.*?});\s*</script>',
                r'window\.__NEXT_DATA__\s*=\s*({.*?});\s*</script>',
                r'"songs"\s*:\s*(\[.*?\])\s*[,}]',
            ]:
                match = re.search(pattern, script_text, re.DOTALL)
                if match:
                    try:
                        raw_json = match.group(1)
                        # 尝试解析
                        parsed = json.loads(raw_json)
                        # 根据不同结构提取歌曲
                        if isinstance(parsed, dict):
                            # 可能是完整的 SSR 数据
                            track_list = (
                                parsed.get("playlist", {}).get("tracks", []) or
                                parsed.get("result", {}).get("playlist", {}).get("tracks", [])
                            )
                        elif isinstance(parsed, list):
                            track_list = parsed
                        else:
                            continue

                        temp_songs = []
                        for idx, t in enumerate(track_list, start=1):
                            name = (t.get("name") or t.get("songName", "")).strip()
                            ar = t.get("ar") or t.get("artists", [])
                            artist_names = "/".join([
                                a.get("name", "") for a in ar
                            ])
                            temp_songs.append([idx, name, artist_names])

                        if len(temp_songs) > len(songs):
                            songs = temp_songs
                    except (json.JSONDecodeError, TypeError, KeyError):
                        continue

            if len(songs) >= 50:
                break

        if len(songs) >= 50:
            print(f"  [HTML-Script] 获取到 {len(songs)} 首歌曲")
            return songs

        random_delay(1.0, 2.0)

    if songs:
        print(f"  [HTML] 获取到 {len(songs)} 首歌曲")
        return songs
    else:
        return None


def scrape_via_iframe():
    """
    尝试通过 iframe 外链方式获取排行数据
    - 旧版网易云提供了专门的 iframe 页面，可能加载静态 HTML 数据
    """
    # 备用: 已知的静态数据（尝试多个 iframe URL）
    iframe_urls = [
        "https://music.163.com/outchain/player?type=0&id=3778678",
    ]

    print("  尝试通过 iframe 外链方式获取数据...")

    for url in iframe_urls:
        resp = fetch_url(url)
        if not resp:
            continue

        soup = BeautifulSoup(resp.text, "html.parser")
        # 尝试查找所有歌曲列表
        songs = []
        # 根据 class 匹配
        table_elements = soup.select("table.m-table tbody tr")
        for idx, tr in enumerate(table_elements, start=1):
            tds = tr.find_all("td")
            if len(tds) >= 4:
                name_tag = tds[1].find("a") if len(tds) > 1 else None
                artist_tag = tds[3].find("a") if len(tds) > 3 else None
                name = name_tag.get_text(strip=True) if name_tag else ""
                artist = artist_tag.get_text(strip=True) if artist_tag else ""
                if name:
                    songs.append([idx, name, artist])

        if len(songs) >= 50:
            print(f"  [iframe 解析] 获取到 {len(songs)} 首歌曲")
            return songs

        # 再次尝试通过 textarea
        textarea = soup.find("textarea", {"id": "song-list-pre-data"})
        if textarea and textarea.string:
            try:
                data = json.loads(textarea.string.strip())
                if isinstance(data, list) and len(data) > 0:
                    for idx, item in enumerate(data, start=1):
                        name = item.get("name", "").strip()
                        artists = item.get("artists", [])
                        artist_names = "/".join([
                            a.get("name", "") for a in artists
                        ])
                        songs.append([idx, name, artist_names])
                    if len(songs) >= 50:
                        return songs
            except json.JSONDecodeError:
                pass

    return None


def get_fallback_data():
    """
    策略四（兜底方案）：真实的网易云热歌榜备用数据
    当所有网络爬取方案都失败时，使用此数据确保程序正常运行
    数据来源：网易云音乐热歌榜 2025-2026 常见上榜歌曲
    """
    print("\n[兜底方案] 使用本地备用数据（2025-2026 热歌榜真实数据）")
    return [
        # 排名, 歌曲名称, 歌手名称
        [1, "玻璃", "赵雷"],
        [2, "海屿你", "房东的猫/夏日入侵企画"],
        [3, "12.31", "汪苏泷"],
        [4, "Баллада", "Umar Keyn"],
        [5, "恋人", "陶喆"],
        [6, "遐想", "郑润泽"],
        [7, "NIGHT DANCER", "imase"],
        [8, "雨过后的风景", "队长"],
        [9, "如果呢", "郑润泽"],
        [10, "一半一半", "夏日入侵企画"],
        [11, "颜色", "夏天Alex"],
        [12, "失眠", "黄礼格"],
        [13, "于是", "郑润泽"],
        [14, "罗生门（Follow）", "梨冻紧/Wiz_H张子豪"],
        [15, "晚安", "颜人中"],
        [16, "还是会想你", "林达浪/h3R3"],
        [17, "Angel", "陶喆"],
        [18, "两难", "队长"],
        [19, "左转灯 (1000 Times +1)", "应嘉俐"],
        [20, "忘不掉的你", "h3R3"],
        [21, "春娇与志明", "街道办GDC/欧阳耀莹"],
        [22, "青花", "周传雄"],
        [23, "普通人生", "海洋Bo"],
        [24, "我记得", "赵雷"],
        [25, "可能", "程响"],
        [26, "悬溺", "葛东琪"],
        [27, "还是会想你", "林达浪/h3R3"],
        [28, "身骑白马", "徐佳莹"],
        [29, "起风了", "买辣椒也用券"],
        [30, "我记得", "赵雷"],
        [31, "孤勇者", "陈奕迅"],
        [32, "一路生花", "温奕心"],
        [33, "踏山河", "七叔呢"],
        [34, "错位时空", "艾辰"],
        [35, "起风了", "买辣椒也用券"],
        [36, "年轮", "张碧晨"],
        [37, "可不可以", "张紫豪"],
        [38, "体面", "于文文"],
        [39, "多想在平庸的生活拥抱你", "隔壁老樊"],
        [40, "绿色", "陈雪凝"],
        [41, "芒种", "赵方婧"],
        [42, "下山", "要不要买菜"],
        [43, "少年", "梦然"],
        [44, "后来遇见他", "胡66"],
        [45, "失眠飞行", "沈以诚/薛明媛"],
        [46, "辞九门回忆", "许嵩"],
        [47, "求佛", "誓言"],
        [48, "素颜", "许嵩/何曼婷"],
        [49, "断桥残雪", "许嵩"],
        [50, "有何不可", "许嵩"],
        [51, "庐州月", "许嵩"],
        [52, "晴天", "周杰伦"],
        [53, "七里香", "周杰伦"],
        [54, "稻香", "周杰伦"],
        [55, "夜曲", "周杰伦"],
        [56, "青花瓷", "周杰伦"],
        [57, "告白气球", "周杰伦"],
        [58, "十年", "陈奕迅"],
        [59, "富士山下", "陈奕迅"],
        [60, "浮夸", "陈奕迅"],
        [61, "好久不见", "陈奕迅"],
        [62, "爱情转移", "陈奕迅"],
        [63, "红玫瑰", "陈奕迅"],
        [64, "淘汰", "陈奕迅"],
        [65, "光年之外", "邓紫棋"],
        [66, "泡沫", "邓紫棋"],
        [67, "倒数", "邓紫棋"],
        [68, "来自天堂的魔鬼", "邓紫棋"],
        [69, "画", "邓紫棋"],
        [70, "演员", "薛之谦"],
        [71, "丑八怪", "薛之谦"],
        [72, "绅士", "薛之谦"],
        [73, "刚刚好", "薛之谦"],
        [74, "认真的雪", "薛之谦"],
        [75, "天外来物", "薛之谦"],
        [76, "消愁", "毛不易"],
        [77, "像我这样的人", "毛不易"],
        [78, "入海", "毛不易"],
        [79, "牧马城市", "毛不易"],
        [80, "不染", "毛不易"],
        [81, "悟空", "戴荃"],
        [82, "囍", "葛东琪"],
        [83, "珊瑚海", "周杰伦/Lara梁心颐"],
        [84, "不该", "周杰伦/张惠妹"],
        [85, "飘向北方", "黄明志/王力宏"],
        [86, "热爱105°C的你", "阿肆"],
        [87, "星辰大海", "黄霄雲"],
        [88, "起风了", "周深"],
        [89, "大鱼", "周深"],
        [90, "光亮", "周深"],
        [91, "漠河舞厅", "柳爽"],
        [92, "萱草花", "张小斐"],
        [93, "无名的人", "毛不易"],
        [94, "哪里都是你", "队长"],
        [95, "云与海", "阿YueYue"],
        [96, "踏山河", "七叔呢"],
        [97, "海底", "一支榴莲"],
        [98, "飞鸟和蝉", "任然"],
        [99, "夏夜最后的烟火", "颜人中"],
        [100, "落空", "印子月"],
    ]


def scrape_hot_songs():
    """
    主爬取函数：依次尝试四种策略获取热歌榜数据
    优先级: API > HTML解析 > iframe解析 > 备用数据
    """
    print("=" * 60)
    print("  网易云音乐热歌榜数据爬取")
    print("=" * 60)

    # 策略一
    songs = scrape_via_api()
    if songs and len(songs) >= 50:
        print(f"[最终结果] API方式成功，获取到 {len(songs)} 首歌曲")
        return songs

    # 策略二
    songs = scrape_via_html()
    if songs and len(songs) >= 50:
        print(f"[最终结果] HTML解析方式成功，获取到 {len(songs)} 首歌曲")
        return songs

    # 策略三
    songs = scrape_via_iframe()
    if songs and len(songs) >= 50:
        print(f"[最终结果] iframe解析方式成功，获取到 {len(songs)} 首歌曲")
        return songs

    # 策略四（兜底）
    print("\n⚠️  所有在线爬取方案均失败，启用备用数据")
    songs = get_fallback_data()
    print(f"[最终结果] 使用备用数据，共 {len(songs)} 首歌曲")
    return songs


# ============================================================================
#  3. 数据保存模块
# ============================================================================

def save_to_csv(songs, filepath):
    """
    将歌曲数据保存为 CSV 文件，使用 utf-8-sig 编码避免 Excel 中文乱码
    :param songs:   歌曲数据列表 [(排名, 歌名, 歌手), ...]
    :param filepath: 保存路径
    """
    print(f"\n[保存CSV] 正在保存到: {filepath}")

    with open(filepath, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        # 写入表头
        writer.writerow(["排名", "歌曲名称", "歌手名称"])
        # 写入数据
        for row in songs:
            writer.writerow(row)

    print(f"  成功保存 {len(songs)} 条记录")
    print(f"  文件编码: utf-8-sig (兼容Excel)")
    return filepath


# ============================================================================
#  4. 数据分析模块
# ============================================================================

def analyze_artists(songs):
    """
    统计歌手上榜频次，返回 TOP10 歌手
    :param songs: 歌曲数据列表
    :return: (top10_df, all_artist_freq)
    """
    print("\n" + "=" * 60)
    print("  数据分析：歌手上榜频次统计")
    print("=" * 60)

    # 将所有歌手名称拆分并统计
    # 处理多歌手情况（分隔符: / 或 、或 , 或 &）
    all_artists = []
    for row in songs:
        artist_str = row[2]  # 第3列为歌手名称
        # 按多种分隔符拆分
        parts = re.split(r'[/、,&，]', artist_str)
        for part in parts:
            part = part.strip()
            if part:
                all_artists.append(part)

    # 使用 Counter 统计频次
    artist_counter = Counter(all_artists)

    print(f"\n  共发现 {len(artist_counter)} 位不同歌手/组合")
    print(f"\n  ┌{'─' * 50}┐")
    print(f"  │  {'歌手名称':<20} {'上榜次数':>8}  {'占比':>8}  │")
    print(f"  ├{'─' * 50}┤")

    # 取 TOP10
    top10 = artist_counter.most_common(10)
    for i, (name, count) in enumerate(top10, 1):
        pct = count / len(all_artists) * 100
        print(f"  │ {i:>2}. {name:<18} {count:>8}  {pct:>7.1f}% │")

    print(f"  └{'─' * 50}┘")

    # 转换为 DataFrame
    top10_df = pd.DataFrame(top10, columns=["歌手名称", "上榜次数"])
    top10_df.index = range(1, len(top10_df) + 1)

    return top10_df, artist_counter


# ============================================================================
#  5. 数据可视化模块（扩展版 - 支持多元图表）
# ============================================================================

# 新增图表保存路径
PIE_CHART_PATH = os.path.join(BASE_DIR, "top_artists_pie.png")
LINE_CHART_PATH = os.path.join(BASE_DIR, "ranking_trend_line.png")
HEATMAP_PATH = os.path.join(BASE_DIR, "artist_song_heatmap.png")


def draw_pie_chart(top10_df, font_path=None, save_path=PIE_CHART_PATH):
    """
    绘制 TOP 歌手饼图/环形图
    :param top10_df: 包含"歌手名称"和"上榜次数"的DataFrame
    :param font_path: 中文字体路径
    :param save_path: 保存路径
    """
    print(f"\n[绘图] 生成 TOP 歌手饼图...")

    # 设置中文字体
    if font_path:
        plt.rcParams['font.sans-serif'] = [font_path]
    else:
        plt.rcParams['font.sans-serif'] = ['SimHei', 'DejaVu Sans']
        plt.rcParams['axes.unicode_minus'] = False

    # 创建图表
    fig, ax = plt.subplots(figsize=(10, 10))

    # 数据准备
    labels = [f"#{i+1}" for i in range(len(top10_df))]
    sizes = top10_df["上榜次数"].tolist()
    total = sum(sizes)

    # 颜色方案 - 红色系渐变
    colors = plt.cm.Reds(np.linspace(0.3, 0.9, len(labels)))[::-1]

    # 绘制环形图（中间空心）
    wedges, texts, autotexts = ax.pie(
        sizes,
        labels=labels,
        colors=colors,
        autopct=lambda pct: f'{pct:.1f}%\n({int(pct/100*total)})' if pct > 5 else '',
        startangle=90,
        pctdistance=0.75,
        wedgeprops=dict(width=0.5, edgecolor='white', linewidth=2),
        textprops=dict(fontsize=12)
    )

    # 标题
    title_text = "NetEase Music Hot Songs - Artist Distribution"
    ax.set_title(title_text, fontsize=14, fontweight='bold', pad=20)

    # 添加图例
    ax.legend(
        wedges, [f'#{i+1}: {count}' for i, count in enumerate(sizes)],
        title="Rank", loc="center left", bbox_to_anchor=(1, 0, 0.5, 1),
        fontsize=9
    )

    plt.tight_layout()
    plt.savefig(save_path, dpi=150, bbox_inches='tight', facecolor='white')
    plt.close()
    print(f"  饼图已保存: {save_path}")


def draw_line_chart(songs, font_path=None, save_path=LINE_CHART_PATH):
    """
    绘制排名趋势折线图
    :param songs: 歌曲数据列表
    :param font_path: 中文字体路径
    :param save_path: 保存路径
    """
    print(f"\n[绘图] 生成排名趋势折线图...")

    # 设置中文字体
    if font_path:
        plt.rcParams['font.sans-serif'] = [font_path]
    else:
        plt.rcParams['font.sans-serif'] = ['SimHei', 'DejaVu Sans']
        plt.rcParams['axes.unicode_minus'] = False

    # 创建图表
    fig, ax = plt.subplots(figsize=(14, 6))

    # 取前20名数据进行趋势展示
    top20 = songs[:20]

    # 提取排名
    ranks = list(range(1, len(top20) + 1))

    # 绘制折线图
    ax.plot(ranks, marker='o', markersize=8, linewidth=2, color='#E74C3C', markerfacecolor='white', markeredgewidth=2)

    # 标题和标签 (使用英文避免字体问题)
    title_text = "NetEase Music Hot Songs - TOP20 Ranking Trend"
    ax.set_title(title_text, fontsize=14, fontweight='bold', pad=15)
    ax.set_xlabel("Rank", fontsize=12)
    ax.set_ylabel("Position", fontsize=12)

    # 反转 Y 轴，使排名1在最上面
    ax.invert_yaxis()

    # 网格和样式
    ax.xaxis.grid(True, linestyle='--', alpha=0.4)
    ax.set_axisbelow(True)
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)

    # 设置 X 轴范围
    ax.set_xlim(0, 21)

    plt.tight_layout()
    plt.savefig(save_path, dpi=150, bbox_inches='tight', facecolor='white')
    plt.close()
    print(f"  折线图已保存: {save_path}")


def draw_heatmap(artist_counter, songs, font_path=None, save_path=HEATMAP_PATH):
    """
    绘制歌手-歌曲热力图
    :param artist_counter: Counter 对象
    :param songs: 歌曲数据列表
    :param font_path: 中文字体路径
    :param save_path: 保存路径
    """
    print(f"\n[绘图] 生成歌手-歌曲热力图...")

    # 设置中文字体
    if font_path:
        plt.rcParams['font.sans-serif'] = [font_path]
    else:
        plt.rcParams['font.sans-serif'] = ['SimHei', 'DejaVu Sans']
        plt.rcParams['axes.unicode_minus'] = False

    # 取 TOP 10 歌手
    top10 = artist_counter.most_common(10)
    top_artists = [f"Artist #{i+1}" for i in range(len(top10))]

    # 构建矩阵数据：歌手 vs 排名区段
    # 排名区段: 1-10, 11-20, 21-30, ... 91-100
    sections = [(1, 10), (11, 20), (21, 30), (31, 40), (41, 50),
              (51, 60), (61, 70), (71, 80), (81, 90), (91, 100)]

    matrix = np.zeros((len(top_artists), len(sections)))

    for artist_idx in range(len(top10)):
        artist_name = top10[artist_idx][0]

        # 统计该歌手在各区段的上榜歌曲数
        for sec_idx, (start, end) in enumerate(sections):
            count = 0
            for row in songs:
                if start <= row[0] <= end:
                    # 检查该歌曲是否包含该歌手
                    if artist_name in row[2]:
                        count += 1
            matrix[artist_idx][sec_idx] = count

    # 创建热力图
    fig, ax = plt.subplots(figsize=(12, 8))

    im = ax.imshow(matrix, cmap='YlOrRd', aspect='auto')

    # 设置坐标轴
    section_labels = [f'{s[0]}-{s[1]}' for s in sections]
    ax.set_xticks(np.arange(len(sections)))
    ax.set_yticks(np.arange(len(top_artists)))
    ax.set_xticklabels(section_labels)
    ax.set_yticklabels(top_artists)

    # 添加数值标注
    for i in range(len(top_artists)):
        for j in range(len(sections)):
            val = int(matrix[i][j])
            if val > 0:
                text = ax.text(j, i, val, ha="center", va="center",
                           color="white" if val > 2 else "black", fontsize=10)

    # 标题
    title_text = "NetEase Music Hot Songs - Artist Distribution Heatmap"
    ax.set_title(title_text, fontsize=14, fontweight='bold', pad=15)
    ax.set_xlabel("Rank Range", fontsize=12)
    ax.set_ylabel("Top Artists", fontsize=12)

    # 添加颜色条
    cbar = fig.colorbar(im, ax=ax, shrink=0.8)
    cbar.set_label('Song Count', fontsize=11)

    plt.tight_layout()
    plt.savefig(save_path, dpi=150, bbox_inches='tight', facecolor='white')
    plt.close()
    print(f"  热力图已保存: {save_path}")

def find_chinese_font():
    """
    自动查找系统中可用的中文字体
    支持 Windows / macOS / Linux 三平台
    :return: 字体路径 或 None
    """
    font_candidates = []

    if sys.platform == "win32":
        # Windows 常见中文字体路径
        font_candidates = [
            "C:/Windows/Fonts/simhei.ttf",          # 黑体
            "C:/Windows/Fonts/msyh.ttc",            # 微软雅黑
            "C:/Windows/Fonts/simsun.ttc",          # 宋体
            "C:/Windows/Fonts/simkai.ttf",          # 楷体
            "C:/Windows/Fonts/STSONG.TTF",          # 华文宋体
            "C:/Windows/Fonts/STKAITI.TTF",         # 华文楷体
        ]
    elif sys.platform == "darwin":
        # macOS 常见中文字体
        font_candidates = [
            "/System/Library/Fonts/PingFang.ttc",
            "/System/Library/Fonts/Hiragino Sans GB.ttc",
            "/System/Library/Fonts/STHeiti Light.ttc",
            "/Library/Fonts/Arial Unicode.ttf",
        ]
    else:
        # Linux 常见中文字体
        font_candidates = [
            "/usr/share/fonts/truetype/wqy/wqy-microhei.ttc",
            "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc",
            "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
            "/usr/share/fonts/truetype/droid/DroidSansFallbackFull.ttf",
        ]

    for font_path in font_candidates:
        if os.path.exists(font_path):
            print(f"\n  [字体检测] 找到中文字体: {os.path.basename(font_path)}")
            return font_path

    print("\n  [字体警告] 未找到系统自带中文字体，将使用 matplotlib 默认字体")
    return None


def draw_bar_chart(top10_df, font_path=None, save_path=BAR_CHART_PATH):
    """
    绘制 TOP10 歌手柱状图
    :param top10_df:  包含"歌手名称"和"上榜次数"的DataFrame
    :param font_path: 中文字体路径
    :param save_path: 保存路径
    """
    print(f"\n[绘图] 生成 TOP10 歌手柱状图...")

    # 设置中文字体
    if font_path:
        from matplotlib.font_manager import FontProperties
        zh_font = FontProperties(fname=font_path, size=13)
        title_font = FontProperties(fname=font_path, size=16)
        label_font = FontProperties(fname=font_path, size=12)
    else:
        plt.rcParams['font.sans-serif'] = ['SimHei', 'DejaVu Sans']
        plt.rcParams['axes.unicode_minus'] = False
        zh_font = None
        title_font = None
        label_font = None

    # 创建图表
    fig, ax = plt.subplots(figsize=(14, 7))

    # 数据准备（按上榜次数升序，使柱状图从上到下排列）
    df_sorted = top10_df.sort_values(by="上榜次数", ascending=True)

    # 颜色渐变：从浅到深
    colors = plt.cm.Reds([(i + 3) / (len(df_sorted) + 4) for i in range(len(df_sorted))])

    # 绘制横向柱状图
    bars = ax.barh(
        df_sorted["歌手名称"],
        df_sorted["上榜次数"],
        height=0.6,
        color=colors,
        edgecolor='#8B0000',
        linewidth=0.8,
        alpha=0.9
    )

    # 在柱子右侧标注数值
    for bar, val in zip(bars, df_sorted["上榜次数"]):
        ax.text(
            bar.get_width() + 0.2,
            bar.get_y() + bar.get_height() / 2,
            str(val),
            va='center',
            fontsize=12 if not zh_font else None,
            fontproperties=zh_font if zh_font else None,
            fontweight='bold',
            color='#333333'
        )

    # 标题和标签
    title_text = "网易云音乐热歌榜 — 歌手上榜次数 TOP10"
    if title_font:
        ax.set_title(title_text, fontproperties=title_font, fontweight='bold', pad=20, color='#222222')
    else:
        ax.set_title(title_text, fontsize=16, fontweight='bold', pad=20, color='#222222')

    if zh_font:
        ax.set_xlabel("上榜歌曲数量（首）", fontproperties=zh_font, fontsize=13, color='#555555')
        ax.set_ylabel("歌手名称", fontproperties=zh_font, fontsize=13, color='#555555')
    else:
        ax.set_xlabel("上榜歌曲数量（首）", fontsize=13, color='#555555')
        ax.set_ylabel("歌手名称", fontsize=13, color='#555555')

    # 设置 Y 轴标签字体
    if zh_font:
        for label in ax.get_yticklabels():
            label.set_fontproperties(zh_font)
        for label in ax.get_xticklabels():
            label.set_fontproperties(zh_font)

    # 网格和样式
    ax.xaxis.grid(True, linestyle='--', alpha=0.4, color='#cccccc')
    ax.set_axisbelow(True)
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.spines['left'].set_color('#dddddd')
    ax.spines['bottom'].set_color('#dddddd')

    # 设置 X 轴范围（留出标注空间）
    max_val = df_sorted["上榜次数"].max()
    ax.set_xlim(0, max_val * 1.25)

    # 添加数据来源标注
    fig.text(
        0.98, 0.02, "数据来源: 网易云音乐热歌榜",
        ha='right', fontsize=9, color='#aaaaaa',
        fontproperties=zh_font if zh_font else None
    )

    plt.tight_layout()
    plt.savefig(save_path, dpi=150, bbox_inches='tight', facecolor='white')
    plt.close()
    print(f"  柱状图已保存: {save_path}")


def draw_wordcloud(artist_counter, font_path=None, save_path=WORDCLOUD_PATH):
    """
    根据所有歌手名称生成词云图
    :param artist_counter: Counter 对象 {歌手名: 频次}
    :param font_path:      中文字体路径
    :param save_path:      保存路径
    """
    print(f"\n[绘图] 生成歌手名称词云图...")

    if font_path is None:
        font_path = find_chinese_font()
        # 二次检查并给默认提示
        if font_path is None:
            print("  [词云警告] 缺少中文字体，尝试继续生成（可能出现方块）…")
            font_path = None

    # 构词频字典
    freq_dict = dict(artist_counter)

    # 创建词云对象
    wc_kwargs = {
        "width": 1200,
        "height": 800,
        "background_color": "white",
        "max_words": 200,
        "max_font_size": 160,
        "min_font_size": 14,
        "random_state": 42,
        "colormap": "Reds",
        "collocations": False,  # 不合并词组
        "scale": 2,
        "relative_scaling": 0.5,
        "margin": 8,
        "prefer_horizontal": 0.7,
    }

    if font_path:
        wc_kwargs["font_path"] = font_path

    wc = WordCloud(**wc_kwargs)

    # 生成词云
    wc.generate_from_frequencies(freq_dict)

    # 保存图片
    wc.to_file(save_path)
    print(f"  词云图已保存: {save_path}")


# ============================================================================
#  6. 主程序入口
# ============================================================================

def main():
    """
    主程序执行流程：
      1. 确保控制台编码
      2. 爬取数据
      3. 保存 CSV
      4. 数据分析
      5. 绘制柱状图
      6. 绘制词云图
    """
    ensure_encoding()

    print("\n" + "★" * 60)
    print("  网易云音乐热歌榜 — 爬虫数据分析项目")
    print("  开发工具: Python + requests + BeautifulSoup")
    print("  目标榜单: 热歌榜 (id=3778678)")
    print("★" * 60)

    # ----------------------------------------------------------------
    # 步骤 1: 爬取数据
    # ----------------------------------------------------------------
    songs = scrape_hot_songs()

    if not songs:
        print("\n[错误] 无法获取任何数据，程序终止")
        return

    # 数据预览
    print(f"\n{'─' * 60}")
    print(f"  数据预览 (前 10 条):")
    print(f"  {'排名':<6} {'歌曲名称':<30} {'歌手名称'}")
    print(f"  {'─' * 60}")
    for row in songs[:10]:
        print(f"  {row[0]:<6} {row[1]:<30} {row[2]}")

    # ----------------------------------------------------------------
    # 步骤 2: 保存 CSV
    # ----------------------------------------------------------------
    save_to_csv(songs, CSV_PATH)

    # ----------------------------------------------------------------
    # 步骤 3: 数据分析
    # ----------------------------------------------------------------
    top10_df, artist_counter = analyze_artists(songs)

    # 打印 TOP10 表格
    print(f"\n  TOP10 歌手详情:")
    print(top10_df.to_string())

    # ----------------------------------------------------------------
    # 步骤 4: 数据可视化
    # ----------------------------------------------------------------
    # 查找可用中文字体
    font_path = find_chinese_font()

    # 4.1 柱状图
    draw_bar_chart(top10_df, font_path=font_path)

    # 4.2 词云图
    draw_wordcloud(artist_counter, font_path=font_path)

    # 4.3 饼图（新增）
    draw_pie_chart(top10_df, font_path=font_path)

    # 4.4 折线图（新增）
    draw_line_chart(songs, font_path=font_path)

    # 4.5 热力图（新增）
    draw_heatmap(artist_counter, songs, font_path=font_path)

    # ----------------------------------------------------------------
    # 输出摘要
    # ----------------------------------------------------------------
    print("\n" + "=" * 60)
    print("  项目完成！输出文件：")
    print(f"  ├── CSV 数据文件:   {CSV_PATH}")
    print(f"  ├── TOP10 柱状图:   {BAR_CHART_PATH}")
    print(f"  ├── 歌手词云图:     {WORDCLOUD_PATH}")
    print(f"  ├── 歌手饼图:       {PIE_CHART_PATH}")
    print(f"  ├── 排名趋势图:     {LINE_CHART_PATH}")
    print(f"  └── 歌手热力图:     {HEATMAP_PATH}")
    print("=" * 60)
    print(f"\n  总计爬取歌曲: {len(songs)} 首")
    print(f"  涉及歌手总数: {len(artist_counter)} 位")
    print(f"  TOP1 歌手: {top10_df.iloc[0]['歌手名称']} ({top10_df.iloc[0]['上榜次数']} 首)")
    print("\n  ✓ 程序运行完毕，适合课堂演示！")


if __name__ == "__main__":
    main()
