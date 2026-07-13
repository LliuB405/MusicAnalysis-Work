# -*- coding: utf-8 -*-
"""
多榜单爬取脚本 — 飙升榜 / 新歌榜 / 原创榜
===========================================
使用 src/music_analytics 模块逐个爬取并保存为独立 CSV。
"""

import os
import sys
import csv
import logging

# 确保 src/ 在 Python 路径中
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_SRC_DIR = os.path.join(_PROJECT_ROOT, "src")
if _SRC_DIR not in sys.path:
    sys.path.insert(0, _SRC_DIR)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("scrape_charts")

from music_analytics.config import Config      # noqa: E402
from music_analytics.scraper import MusicScraper  # noqa: E402


# 目标榜单
TARGET_CHARTS = {
    "飙升榜": "19723756",
    "新歌榜": "3779629",
    "原创榜": "2884035",
}

OUTPUT_DIR = _PROJECT_ROOT


def main():
    config = Config()
    scraper = MusicScraper(config)

    print("=" * 60)
    print("  网易云音乐多榜单爬取")
    print("  目标: 飙升榜 / 新歌榜 / 原创榜")
    print("=" * 60)

    total_songs = 0
    for chart_name, chart_id in TARGET_CHARTS.items():
        print(f"\n{'─' * 60}")
        print(f"  ▶ 正在爬取: {chart_name} (ID: {chart_id})")
        print(f"{'─' * 60}")

        songs = scraper.scrape_chart(chart_id)

        if not songs:
            print(f"  ✗ {chart_name} 爬取失败，跳过")
            continue

        # 保存 CSV
        filename = f"{chart_name}.csv"
        filepath = os.path.join(OUTPUT_DIR, filename)
        with open(filepath, "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.writer(f)
            writer.writerow(["排名", "歌曲名称", "歌手名称"])
            for s in songs:
                writer.writerow([s.rank, s.title, s.artist])

        print(f"  ✓ {chart_name}: {len(songs)} 首 → {filename}")
        total_songs += len(songs)

    print(f"\n{'=' * 60}")
    print(f"  完成！共爬取 {total_songs} 首歌曲，保存至:")
    for name in TARGET_CHARTS:
        fp = os.path.join(OUTPUT_DIR, f"{name}.csv")
        if os.path.exists(fp):
            print(f"    ├── {name}.csv")
    print(f"{'=' * 60}")


if __name__ == "__main__":
    main()
