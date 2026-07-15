# -*- coding: utf-8 -*-
"""
Music Analytics Dashboard — NetEase Cloud Music Hot Songs
=========================================================
Real-time web scraping + data analysis + visualization platform.

Tech Stack:
- Flask (Web framework)
- requests + BeautifulSoup (Web scraping)
- matplotlib + wordcloud (Visualization)
- Modular architecture (src/music_analytics)

Run:
    python app.py
    Open http://127.0.0.1:5000
"""

import logging
import os
import sys
import tempfile
import threading
from datetime import datetime

import requests

# Ensure src/ directory is on the Python path so that the
# `music_analytics` package can be imported regardless of the
# directory from which the user launches the application.
_PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
_SRC_DIR = os.path.join(_PROJECT_ROOT, "src")
if _SRC_DIR not in sys.path:
    sys.path.insert(0, _SRC_DIR)

from flask import Flask, render_template, jsonify, Response  # noqa: E402

from music_analytics.config import Config  # noqa: E402
from music_analytics.models import SongData  # noqa: E402
from music_analytics.scraper import MusicScraper  # noqa: E402
from music_analytics.analyzer import ArtistAnalyzer  # noqa: E402
from music_analytics.visualizer import ChartGenerator  # noqa: E402
from music_analytics.history import HistoryManager  # noqa: E402
from music_analytics.scheduler import Scheduler  # noqa: E402

# ============================================================
# Logging
# ============================================================
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

# ============================================================
# App & dependencies
# ============================================================
config = Config()
app = Flask(__name__)
app.config["SECRET_KEY"] = config.secret_key
app.config["TEMPLATES_AUTO_RELOAD"] = True
app.config["SEND_FILE_MAX_AGE_DEFAULT"] = 0


@app.after_request
def disable_ui_cache(response):
    """Always serve the current UI while this project is under active development."""
    if response.mimetype in {"text/html", "text/css", "application/javascript", "text/javascript"}:
        response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
    return response


@app.route("/api/health", methods=["GET"])
def api_health():
    """轻量健康检查，供启动脚本、隧道与外部监控验证服务。"""
    return jsonify({
        "success": True,
        "service": "MusicAnalysis-Work",
        "charts": len(config.chart_ids),
    })

# Make sure the static directory exists (for any files we may write)
os.makedirs(config.static_dir, exist_ok=True)

_scraper = MusicScraper(config)
_chart_gen = ChartGenerator(config)
_history_mgr = HistoryManager()
_scheduler: Scheduler | None = None
_scraped_data: list = []  # in-memory cache of the latest scrape result


def do_scrape():
    """Run the multi-strategy scraper and cache its result."""
    global _scraped_data
    result = _scraper.scrape()
    _scraped_data = result.data
    # 自动保存到历史记录
    if _scraped_data:
        try:
            _history_mgr.save_snapshot("热歌榜", "3778678", _scraped_data)
        except Exception as e:
            logger.warning("自动保存历史数据失败: %s", e)
    return result


# ============================================================
# Routes
# ============================================================
@app.route("/")
def index() -> str:
    """Dashboard home page."""
    return render_template("index.html")


@app.route("/player")
def music_player() -> str:
    """多榜单歌曲列表 + 在线听歌页面"""
    return render_template("music_player.html")


@app.route("/api/scrape", methods=["POST"])
def api_scrape():
    """Trigger a fresh scrape and return the data + method used."""
    try:
        result = do_scrape()
        payload = result.to_dict()
        payload["data"] = [s.to_dict() for s in _scraped_data]
        return jsonify(payload)
    except Exception as e:
        logger.error("Scrape failed: %s", e, exc_info=True)
        return jsonify({"success": False, "error": str(e)})


@app.route("/api/analyze", methods=["GET"])
def api_analyze():
    """Return artist frequency analysis for the current dataset."""
    try:
        if not _scraped_data:
            return jsonify({"success": False, "error": "没有数据，请先爬取"})

        analyzer = ArtistAnalyzer(_scraped_data)
        result = analyzer.analyze()
        return jsonify({"success": True, **result.to_dict()})
    except Exception as e:
        logger.error("Analyze failed: %s", e, exc_info=True)
        return jsonify({"success": False, "error": str(e)})


@app.route("/api/chart/bar", methods=["GET"])
def api_bar_chart():
    """Return the TOP10 artist bar chart as a base64-encoded PNG."""
    try:
        if not _scraped_data:
            return jsonify({"success": False, "error": "没有数据，请先爬取"})

        analyzer = ArtistAnalyzer(_scraped_data)
        top10 = analyzer.get_top_artists(10)
        image = _chart_gen.generate_bar_chart(top10)
        if image:
            return jsonify({"success": True, "image": image})
        return jsonify({"success": False, "error": "生成失败"})
    except Exception as e:
        logger.error("Bar chart failed: %s", e, exc_info=True)
        return jsonify({"success": False, "error": str(e)})


@app.route("/api/chart/wordcloud", methods=["GET"])
def api_wordcloud():
    """Return the artist word-cloud as a base64-encoded PNG."""
    try:
        if not _scraped_data:
            return jsonify({"success": False, "error": "没有数据，请先爬取"})

        analyzer = ArtistAnalyzer(_scraped_data)
        artist_counter = analyzer.get_artist_dict()
        image = _chart_gen.generate_wordcloud(artist_counter)
        if image:
            return jsonify({"success": True, "image": image})
        return jsonify({"success": False, "error": "生成失败"})
    except Exception as e:
        logger.error("Word cloud failed: %s", e, exc_info=True)
        return jsonify({"success": False, "error": str(e)})


@app.route("/api/chart/pie", methods=["GET"])
def api_pie_chart():
    """Return the TOP10 artist pie chart as a base64-encoded PNG."""
    try:
        if not _scraped_data:
            return jsonify({"success": False, "error": "没有数据，请先爬取"})

        analyzer = ArtistAnalyzer(_scraped_data)
        top10 = analyzer.get_top_artists(10)
        image = _chart_gen.generate_pie_chart(top10)
        if image:
            return jsonify({"success": True, "image": image})
        return jsonify({"success": False, "error": "生成失败"})
    except Exception as e:
        logger.error("Pie chart failed: %s", e, exc_info=True)
        return jsonify({"success": False, "error": str(e)})


@app.route("/api/chart/line", methods=["GET"])
def api_line_chart():
    """Return the ranking trend line chart as a base64-encoded PNG."""
    try:
        if not _scraped_data:
            return jsonify({"success": False, "error": "没有数据，请先爬取"})

        analyzer = ArtistAnalyzer(_scraped_data)
        image = _chart_gen.generate_line_chart(_scraped_data)
        if image:
            return jsonify({"success": True, "image": image})
        return jsonify({"success": False, "error": "生成失败"})
    except Exception as e:
        logger.error("Line chart failed: %s", e, exc_info=True)
        return jsonify({"success": False, "error": str(e)})


@app.route("/api/chart/heatmap", methods=["GET"])
def api_heatmap():
    """Return the artist-song heatmap as a base64-encoded PNG."""
    try:
        if not _scraped_data:
            return jsonify({"success": False, "error": "没有数据，请先爬取"})

        analyzer = ArtistAnalyzer(_scraped_data)
        top_artists = analyzer.get_top_artists(15)
        image = _chart_gen.generate_heatmap(top_artists, _scraped_data)
        if image:
            return jsonify({"success": True, "image": image})
        return jsonify({"success": False, "error": "生成失败"})
    except Exception as e:
        logger.error("Heatmap failed: %s", e, exc_info=True)
        return jsonify({"success": False, "error": str(e)})


@app.route("/api/export_csv", methods=["GET"])
def api_export_csv():
    """Stream the current dataset as a CSV download.

    CSV 文件包含 3 个 section：
      1. 网易云热歌榜（排名 / 歌曲 / 歌手）
      2. 歌手词云榜（TOP 50 歌手出现次数 + 占比）
      3. 歌手-排名热力榜（每个歌手在各排名区间的歌曲数 + 合计）
    """
    try:
        if not _scraped_data:
            return jsonify({"success": False, "error": "没有数据，请先爬取"}), 400

        # 复用图表的中间数据
        artist_counter = None
        heatmap_data = None
        heatmap_labels = None
        try:
            analyzer = ArtistAnalyzer(_scraped_data)
            artist_counter = analyzer.get_artist_dict()
            top15 = analyzer.get_top_artists(15)
            # 热力图数据：和 generate_heatmap 同样的 7 个排名区间
            bins = [0, 10, 25, 50, 75, 100, 150, 200]
            heatmap_labels = ['1-10', '11-25', '26-50', '51-75', '76-100', '101-150', '151-200'][:len(bins) - 1]
            heatmap_data = {}
            for stat in top15[:15]:
                row = []
                for i in range(len(bins) - 1):
                    low, high = bins[i], bins[i + 1]
                    count = sum(1 for s in _scraped_data[low - 1:high] if stat.name in s.artist)
                    row.append(count)
                heatmap_data[stat.name] = row
        except Exception as e:
            logger.warning("CSV 导出时词云/热力数据计算失败，仅导出歌曲列表: %s", e)

        csv_content = _chart_gen.generate_csv(
            _scraped_data,
            artist_counter=artist_counter,
            heatmap_data=heatmap_data,
            heatmap_labels=heatmap_labels,
        )
        if not csv_content:
            return jsonify({"success": False, "error": "数据为空"}), 400

        # 文件名带时间戳，避免覆盖
        ts = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"hot_songs_full_{ts}.csv"
        return Response(
            csv_content,
            mimetype="text/csv",
            headers={
                "Content-Disposition": f"attachment; filename={filename}",
                "Content-Type": "text/csv; charset=utf-8-sig",
            },
        )
    except Exception as e:
        logger.error("CSV export failed: %s", e, exc_info=True)
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/clear", methods=["POST"])
def api_clear():
    """Clear the in-memory dataset."""
    global _scraped_data
    _scraped_data = []
    return jsonify({"success": True, "message": "数据已清空"})


@app.route("/api/data", methods=["GET"])
def api_data():
    """Return the raw cached dataset."""
    return jsonify(
        {
            "success": True,
            "data": [s.to_dict() for s in _scraped_data],
            "count": len(_scraped_data),
        }
    )


# ============================================================
# 历史数据管理 API
# ============================================================
@app.route("/api/history/charts", methods=["GET"])
def api_history_charts():
    """返回当前支持的官方榜单目录，并标记本地是否已有快照。"""
    try:
        stored_charts = _history_mgr.get_all_charts()
        stored_set = set(stored_charts)
        configured = list(config.chart_ids.items())
        return jsonify({
            "success": True,
            "charts": [name for name, _ in configured],
            "chart_meta": [
                {"name": name, "id": chart_id, "available": name in stored_set}
                for name, chart_id in configured
            ],
            "archived_charts": [name for name in stored_charts if name not in config.chart_ids],
        })
    except Exception as e:
        logger.error("获取历史榜单列表失败: %s", e, exc_info=True)
        return jsonify({"success": False, "error": str(e)})


@app.route("/api/history/snapshot_dates/<chart_name>", methods=["GET"])
def api_history_snapshot_dates(chart_name: str):
    """获取指定榜单的快照日期列表"""
    try:
        from flask import request
        limit = request.args.get("limit", 30, type=int)
        dates = _history_mgr.get_snapshot_dates(chart_name, limit=limit)
        return jsonify({"success": True, "chart_name": chart_name, "dates": dates})
    except Exception as e:
        logger.error("获取快照日期失败: %s", e, exc_info=True)
        return jsonify({"success": False, "error": str(e)})


@app.route("/api/history/snapshot/<chart_name>", methods=["GET"])
def api_history_snapshot(chart_name: str):
    """获取指定榜单的最新快照（或指定时间戳的快照）"""
    try:
        from flask import request
        timestamp = request.args.get("timestamp")
        data = _history_mgr.get_chart_snapshot(chart_name, timestamp=timestamp or None)
        if data is None:
            return jsonify({"success": False, "error": f"榜单「{chart_name}」暂无历史数据"})
        return jsonify({"success": True, "chart_name": chart_name, "data": data, "count": len(data)})
    except Exception as e:
        logger.error("获取历史快照失败: %s", e, exc_info=True)
        return jsonify({"success": False, "error": str(e)})


@app.route("/api/history/trend", methods=["GET"])
def api_history_trend():
    """获取歌曲的历史排名趋势

    Query params: chart_name, song_title, artist, days (可选, 默认30)
    """
    try:
        from flask import request
        chart_name = (request.args.get("chart_name") or "").strip()
        song_title = (request.args.get("song_title") or "").strip()
        artist = (request.args.get("artist") or "").strip()
        days = request.args.get("days", 30, type=int)

        if not chart_name or not song_title or not artist:
            return jsonify({"success": False, "error": "缺少 chart_name / song_title / artist 参数"}), 400

        trend = _history_mgr.get_song_trend(chart_name, song_title, artist, days=days)
        return jsonify({
            "success": True,
            "chart_name": chart_name,
            "song_title": song_title,
            "artist": artist,
            "trend": trend,
            "count": len(trend),
        })
    except Exception as e:
        logger.error("获取歌曲趋势失败: %s", e, exc_info=True)
        return jsonify({"success": False, "error": str(e)})


@app.route("/api/history/rank_changes/<chart_name>", methods=["GET"])
def api_history_rank_changes(chart_name: str):
    """获取指定榜单的排名变化（前后快照对比）"""
    try:
        from flask import request
        days = request.args.get("days", 7, type=int)
        changes = _history_mgr.get_rank_changes(chart_name, days=days)
        return jsonify({"success": True, "chart_name": chart_name, "changes": changes, "count": len(changes)})
    except Exception as e:
        logger.error("获取排名变化失败: %s", e, exc_info=True)
        return jsonify({"success": False, "error": str(e)})


@app.route("/api/history/cleanup", methods=["POST"])
def api_history_cleanup():
    """手动清理过期历史数据"""
    try:
        from flask import request
        body = request.get_json(silent=True) or {}
        days = body.get("days", config.history_retention_days)
        deleted = _history_mgr.cleanup_old_data(retention_days=days)
        return jsonify({"success": True, "deleted": deleted, "message": f"已清理 {deleted} 条过期数据"})
    except Exception as e:
        logger.error("清理历史数据失败: %s", e, exc_info=True)
        return jsonify({"success": False, "error": str(e)})


@app.route("/api/history/save", methods=["POST"])
def api_history_save():
    """手动将当前内存数据保存到历史记录"""
    try:
        if not _scraped_data:
            return jsonify({"success": False, "error": "没有数据，请先爬取"})

        from flask import request
        body = request.get_json(silent=True) or {}
        chart_name = body.get("chart_name", "热歌榜")

        snapshot_id = _history_mgr.save_snapshot(chart_name, "3778678", _scraped_data)
        return jsonify({
            "success": True,
            "snapshot_id": snapshot_id,
            "chart_name": chart_name,
            "song_count": len(_scraped_data),
        })
    except Exception as e:
        logger.error("保存历史数据失败: %s", e, exc_info=True)
        return jsonify({"success": False, "error": str(e)})


@app.route("/api/history/trend_chart", methods=["GET"])
def api_history_trend_chart():
    """获取歌曲历史排名趋势折线图（base64 编码 PNG）

    Query params: chart_name, song_title, artist, days (可选, 默认30)
    """
    try:
        from flask import request
        chart_name = (request.args.get("chart_name") or "").strip()
        song_title = (request.args.get("song_title") or "").strip()
        artist = (request.args.get("artist") or "").strip()
        days = request.args.get("days", 30, type=int)

        if not chart_name or not song_title or not artist:
            return jsonify({"success": False, "error": "缺少 chart_name / song_title / artist 参数"}), 400

        trend = _history_mgr.get_song_trend(chart_name, song_title, artist, days=days)
        if not trend or len(trend) < 2:
            return jsonify({"success": False, "error": f"「{song_title}」- {artist} 在近{days}天内数据不足，无法生成趋势图"})

        image = _chart_gen.generate_trend_chart(trend, song_title=song_title, artist=artist)
        if image:
            return jsonify({"success": True, "image": image, "trend": trend, "count": len(trend)})
        return jsonify({"success": False, "error": "趋势图生成失败"})
    except Exception as e:
        logger.error("生成趋势图失败: %s", e, exc_info=True)
        return jsonify({"success": False, "error": str(e)})


@app.route("/api/chart/topn_trend", methods=["GET"])
def api_chart_topn_trend():
    """获取某榜单当前 TopN 歌曲在 N 天内的排名走势

    Query: chart_name, top_n (默认10), days (默认7)
    """
    try:
        from flask import request
        chart_name = (request.args.get("chart_name") or "").strip()
        if not chart_name:
            return jsonify({"success": False, "error": "缺少 chart_name 参数"}), 400
        top_n = request.args.get("top_n", 10, type=int)
        days = request.args.get("days", 7, type=int)
        result = _history_mgr.get_chart_topn_trend(chart_name, top_n=top_n, days=days)
        return jsonify({"success": True, **result})
    except Exception as e:
        logger.error("获取 TopN 趋势失败: %s", e, exc_info=True)
        return jsonify({"success": False, "error": str(e)}), 500


# ============================================================
# 多榜单对比 API
# ============================================================
@app.route("/api/scrape_all", methods=["POST"])
def api_scrape_all():
    """一次性爬取全部已配置榜单，并存到历史记录"""
    try:
        results = _scraper.scrape_all_charts()
        saved = {}
        for chart_name, songs in results.items():
            try:
                chart_id = config.chart_ids.get(chart_name, "0")
                _history_mgr.save_snapshot(chart_name, chart_id, songs)
                saved[chart_name] = len(songs)
            except Exception as e:
                logger.warning("保存榜单 %s 失败: %s", chart_name, e)
                saved[chart_name] = 0

        return jsonify({
            "success": True,
            "saved": saved,
            "total_charts": len(saved),
        })
    except Exception as e:
        logger.error("全榜单爬取失败: %s", e, exc_info=True)
        return jsonify({"success": False, "error": str(e)})


@app.route("/api/charts/compare", methods=["GET"])
def api_charts_compare():
    """多榜单对比数据：每个榜单的 TOP 歌手排行

    Query params: top_n (默认10)
    """
    try:
        from flask import request
        top_n = request.args.get("top_n", 10, type=int)
        from collections import Counter

        charts = _history_mgr.get_all_charts()
        if not charts:
            return jsonify({"success": False, "error": "暂无历史数据，请先爬取"})

        compare_data = {}
        for chart_name in charts:
            snapshot = _history_mgr.get_chart_snapshot(chart_name)
            if not snapshot:
                continue

            songs_for_chart = [
                SongData(rank=s["rank"], title=s["title"], artist=s["artist"])
                for s in snapshot
            ]
            _comp_analyzer = ArtistAnalyzer(songs_for_chart)
            top = _comp_analyzer.get_top_artists(top_n)
            compare_data[chart_name] = [
                {"rank": i + 1, "name": stat.name, "count": stat.count, "pct": stat.percentage}
                for i, stat in enumerate(top)
            ]

        return jsonify({"success": True, "compare": compare_data, "charts": list(compare_data.keys())})
    except Exception as e:
        logger.error("多榜单对比失败: %s", e, exc_info=True)
        return jsonify({"success": False, "error": str(e)})


# ── 跨榜交集分析 ──
@app.route("/api/analysis/cross-chart", methods=["GET"])
def api_cross_chart():
    """跨榜单交集分析：找出同时在多个榜单出现的歌曲"""
    try:
        charts = _history_mgr.get_all_charts()
        if len(charts) < 2:
            return jsonify({"success": False, "error": "至少需要 2 个榜单的快照数据"})

        # 收集每个榜单的歌曲集合 {(title, artist): rank}
        chart_songs = {}
        for chart_name in charts:
            snapshot = _history_mgr.get_chart_snapshot(chart_name)
            if snapshot:
                chart_songs[chart_name] = {(s["title"], s["artist"]): s["rank"] for s in snapshot}

        # 找交集：出现在至少 2 个榜单的歌
        all_keys = {}  # {(title, artist): [(chart_name, rank), ...]}
        for chart_name, songs in chart_songs.items():
            for key, rank in songs.items():
                if key not in all_keys:
                    all_keys[key] = []
                all_keys[key].append((chart_name, rank))

        # 过滤 + 排序
        crossing = []
        for (title, artist), entries in all_keys.items():
            if len(entries) >= 2:
                entries.sort(key=lambda x: x[1])  # 按排名排序
                crossing.append({
                    "title": title,
                    "artist": artist,
                    "chart_count": len(entries),
                    "appearances": [{"chart": c, "rank": r} for c, r in entries],
                })

        crossing.sort(key=lambda x: -x["chart_count"])  # 出现次数多的排前面

        # 汇总统计
        summary = {
            "total_charts": len(charts),
            "total_crossing": len(crossing),
            "crossing_2_charts": sum(1 for x in crossing if x["chart_count"] == 2),
            "crossing_3_charts": sum(1 for x in crossing if x["chart_count"] == 3),
            "crossing_4plus": sum(1 for x in crossing if x["chart_count"] >= 4),
        }

        return jsonify({
            "success": True,
            "crossing": crossing,
            "summary": summary,
        })
    except Exception as e:
        logger.error("跨榜分析失败: %s", e, exc_info=True)
        return jsonify({"success": False, "error": str(e)})


# ============================================================
# 数据导出 API（Excel + PDF）
# ============================================================
@app.route("/api/export/excel", methods=["GET"])
def api_export_excel():
    """导出 Excel 多 Sheet 报表"""
    try:
        from flask import request
        chart_name = (request.args.get("chart_name") or "热歌榜").strip()

        if not _scraped_data:
            return jsonify({"success": False, "error": "没有数据，请先爬取"}), 400

        analyzer = ArtistAnalyzer(_scraped_data)
        artist_counter = analyzer.get_artist_dict()

        # 尝试获取排名变化数据
        rank_changes = None
        try:
            rank_changes = _history_mgr.get_rank_changes(chart_name, days=7)
        except Exception:
            pass

        content = _chart_gen.generate_excel(
            songs=_scraped_data,
            artist_counter=artist_counter,
            chart_name=chart_name,
            rank_changes=rank_changes,
        )
        if content is None:
            return jsonify({"success": False, "error": "Excel 生成失败"}), 500

        ts = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"music_analytics_{ts}.xlsx"
        return Response(
            content,
            mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={
                "Content-Disposition": f"attachment; filename={filename}",
                "Content-Type": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            },
        )
    except Exception as e:
        logger.error("Excel 导出失败: %s", e, exc_info=True)
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/export/pdf", methods=["GET"])
def api_export_pdf():
    """导出 PDF 报表"""
    try:
        from flask import request
        chart_name = (request.args.get("chart_name") or "热歌榜").strip()

        if not _scraped_data:
            return jsonify({"success": False, "error": "没有数据，请先爬取"}), 400

        analyzer = ArtistAnalyzer(_scraped_data)
        artist_counter = analyzer.get_artist_dict()
        top10 = analyzer.get_top_artists(10)

        content = _chart_gen.generate_pdf(
            songs=_scraped_data,
            artist_counter=artist_counter,
            top10=top10,
            chart_name=chart_name,
        )
        if content is None:
            return jsonify({"success": False, "error": "PDF 生成失败"}), 500

        ts = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"music_analytics_{ts}.pdf"
        return Response(
            content,
            mimetype="application/pdf",
            headers={
                "Content-Disposition": f"attachment; filename={filename}",
                "Content-Type": "application/pdf",
            },
        )
    except Exception as e:
        logger.error("PDF 导出失败: %s", e, exc_info=True)
        return jsonify({"success": False, "error": str(e)}), 500


# ============================================================
# 定时调度器 API
# ============================================================
def _get_or_create_scheduler() -> Scheduler:
    """获取或创建全局调度器实例（懒加载）"""
    global _scheduler
    if _scheduler is None:
        _scheduler = Scheduler(config)
    return _scheduler


@app.route("/api/scheduler/status", methods=["GET"])
def api_scheduler_status():
    """获取调度器运行状态"""
    try:
        s = _get_or_create_scheduler()
        status = s.get_status()
        return jsonify({"success": True, **status})
    except Exception as e:
        logger.error("获取调度器状态失败: %s", e, exc_info=True)
        return jsonify({"success": False, "error": str(e)})


@app.route("/api/scheduler/start", methods=["POST"])
def api_scheduler_start():
    """启动定时调度器"""
    try:
        s = _get_or_create_scheduler()
        if s._running:
            return jsonify({"success": False, "message": "调度器已在运行中"})
        ok = s.start()
        if ok:
            logger.info("定时调度器已通过 API 启动（间隔 %s 秒）", config.auto_refresh_interval)
            return jsonify({"success": True, "message": f"调度器已启动，每 {config.auto_refresh_interval} 秒刷新"})
        return jsonify({"success": False, "message": "启动失败"})
    except Exception as e:
        logger.error("启动调度器失败: %s", e, exc_info=True)
        return jsonify({"success": False, "error": str(e)})


@app.route("/api/scheduler/stop", methods=["POST"])
def api_scheduler_stop():
    """停止定时调度器"""
    try:
        s = _get_or_create_scheduler()
        if not s._running:
            return jsonify({"success": False, "message": "调度器未在运行"})
        ok = s.stop()
        if ok:
            logger.info("定时调度器已通过 API 停止")
            return jsonify({"success": True, "message": "调度器已停止"})
        return jsonify({"success": False, "message": "停止失败"})
    except Exception as e:
        logger.error("停止调度器失败: %s", e, exc_info=True)
        return jsonify({"success": False, "error": str(e)})


@app.route("/api/scheduler/run_now", methods=["POST"])
def api_scheduler_run_now():
    """立即执行一次爬取任务"""
    try:
        s = _get_or_create_scheduler()
        result = s.run_now()
        return jsonify({"success": True, "result": result.to_dict()})
    except Exception as e:
        logger.error("立即执行调度任务失败: %s", e, exc_info=True)
        return jsonify({"success": False, "error": str(e)})


# ============================================================
# VIP 账号管理
# ============================================================
# 持久化文件：保存 cookie，避免重启服务后丢失
import json as _json
_VIP_FILE = os.path.join(_PROJECT_ROOT, ".vip_session.json")


def _is_local_admin_request(request) -> bool:
    """账号 Cookie 管理只允许本机访问，防止公网访客覆盖服务器凭据。"""
    import ipaddress
    forwarded = (
        request.headers.get("CF-Connecting-IP")
        or (request.headers.get("X-Forwarded-For") or "").split(",")[0].strip()
    )
    address = forwarded or request.remote_addr or ""
    try:
        return ipaddress.ip_address(address).is_loopback
    except ValueError:
        return False


def _load_vip_from_disk() -> None:
    """启动时从 .vip_session.json 加载 cookie（如果存在）"""
    if not os.path.exists(_VIP_FILE):
        return
    try:
        with open(_VIP_FILE, "r", encoding="utf-8") as f:
            data = _json.load(f)
        config.vip_music_u = (data.get("music_u") or "").strip()
        config.vip_csrf = (data.get("csrf") or "").strip()
        if config.vip_music_u:
            logger.info("VIP cookie 已从 .vip_session.json 恢复")
    except Exception as e:
        logger.warning("加载 VIP cookie 失败: %s", e)


def _save_vip_to_disk() -> bool:
    """把当前 cookie 写入 .vip_session.json"""
    try:
        with open(_VIP_FILE, "w", encoding="utf-8") as f:
            _json.dump({"music_u": config.vip_music_u, "csrf": config.vip_csrf}, f)
        return True
    except Exception as e:
        logger.warning("保存 VIP cookie 失败: %s", e)
        return False


# 启动时尝试恢复
_load_vip_from_disk()


@app.route("/api/vip/status", methods=["GET"])
def api_vip_status():
    """查询当前 VIP 登录状态"""
    has_music_u = bool(config.vip_music_u)
    return jsonify({
        "success": True,
        "logged_in": has_music_u,
        "music_u_preview": (config.vip_music_u[:8] + "...") if has_music_u else "",
    })


@app.route("/api/vip/login", methods=["POST"])
def api_vip_login():
    """设置 VIP 账号 cookie（运行时注入，无需重启）

    请求体: {"music_u": "...", "csrf": "..."}
    获取方式: 浏览器登录 music.163.com → F12 → Application → Cookies
    """
    try:
        from flask import request
        if not _is_local_admin_request(request):
            return jsonify({"success": False, "error": "账号设置仅允许在服务器本机操作"}), 403
        body = request.get_json(silent=True) or {}
        music_u = (body.get("music_u") or "").strip()
        csrf = (body.get("csrf") or "").strip()

        if not music_u:
            return jsonify({"success": False, "error": "缺少 music_u 字段"}), 400

        # 运行时更新 config（不持久化）
        config.vip_music_u = music_u
        config.vip_csrf = csrf

        # 关键：VIP 账号变更时清空旧缓存（旧的 mp3 url 是按未登录账号签发的，新账号拉会 403）
        cleared = len(_play_url_cache)
        _play_url_cache.clear()
        _play_url_sessions.clear()
        _playability_cache.clear()

        # 持久化到磁盘（重启不丢）
        _save_vip_to_disk()

        logger.info("VIP cookie 已更新 (music_u: %s..., 清空 %d 条旧缓存)", music_u[:8], cleared)
        return jsonify({"success": True, "message": f"VIP cookie 已注入，清空 {cleared} 条旧缓存，刷新榜单后可听 VIP 歌曲"})
    except Exception as e:
        logger.error("设置 VIP cookie 失败: %s", e, exc_info=True)
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/vip/logout", methods=["POST"])
def api_vip_logout():
    """退出 VIP 登录"""
    from flask import request
    if not _is_local_admin_request(request):
        return jsonify({"success": False, "error": "账号设置仅允许在服务器本机操作"}), 403
    config.vip_music_u = ""
    config.vip_csrf = ""
    # 同步清空缓存（退出后旧 url 不可用）
    _play_url_cache.clear()
    _play_url_sessions.clear()
    _playability_cache.clear()
    # 同步删除持久化文件
    try:
        if os.path.exists(_VIP_FILE):
            os.remove(_VIP_FILE)
    except Exception as e:
        logger.warning("删除 .vip_session.json 失败: %s", e)
    return jsonify({"success": True, "message": "已退出 VIP 登录"})


# ============================================================
# 收藏歌单 API（后端持久化，跨页面同步）
# ============================================================
_FAVORITES_FILE = os.path.join(_PROJECT_ROOT, ".favorites.json")
_FAVORITES_LOCK = threading.RLock()
_FAVORITES_MAX_COUNT = 500
_FAVORITES_MAX_PAYLOAD_BYTES = 4096
_FAVORITES_FIELD_LIMITS = {"title": 200, "artist": 200, "chart": 100}


class _FavoritesStorageError(RuntimeError):
    """收藏文件无法安全读取或写入。"""


def _normalize_favorite_field(value, field, *, required=False):
    """校验并规范化收藏字段，避免匿名接口无限扩张存储。"""
    if value is None:
        value = ""
    if not isinstance(value, str):
        raise ValueError(f"{field} 必须是字符串")
    value = value.strip()
    if required and not value:
        raise ValueError(f"缺少 {field}")
    if len(value) > _FAVORITES_FIELD_LIMITS[field]:
        raise ValueError(
            f"{field} 不能超过 {_FAVORITES_FIELD_LIMITS[field]} 个字符"
        )
    return value


def _validate_favorites(favorites):
    """验证磁盘数据，避免在损坏文件上继续覆盖写入。"""
    if not isinstance(favorites, list):
        raise _FavoritesStorageError("收藏文件格式无效")
    if len(favorites) > _FAVORITES_MAX_COUNT:
        raise _FavoritesStorageError("收藏文件超过数量限制")

    validated = []
    try:
        for item in favorites:
            if not isinstance(item, dict):
                raise ValueError("收藏项必须是对象")
            validated.append({
                "title": _normalize_favorite_field(
                    item.get("title"), "title", required=True
                ),
                "artist": _normalize_favorite_field(
                    item.get("artist"), "artist", required=True
                ),
                "chart": _normalize_favorite_field(item.get("chart"), "chart"),
            })
    except ValueError as exc:
        raise _FavoritesStorageError("收藏文件内容无效") from exc
    return validated


def _load_favorites_unlocked():
    """在调用方持锁时从磁盘加载收藏列表。"""
    if not os.path.exists(_FAVORITES_FILE):
        return []
    try:
        with open(_FAVORITES_FILE, "r", encoding="utf-8") as file_obj:
            return _validate_favorites(_json.load(file_obj))
    except _FavoritesStorageError:
        raise
    except (OSError, ValueError, TypeError, _json.JSONDecodeError) as exc:
        raise _FavoritesStorageError("无法读取收藏文件") from exc


def _save_favorites_unlocked(favorites):
    """在调用方持锁时，通过同目录临时文件原子保存收藏。"""
    favorites = _validate_favorites(favorites)
    target_dir = os.path.dirname(_FAVORITES_FILE) or "."
    temp_path = None
    file_descriptor = None
    try:
        file_descriptor, temp_path = tempfile.mkstemp(
            prefix=".favorites-", suffix=".tmp", dir=target_dir
        )
        with os.fdopen(file_descriptor, "w", encoding="utf-8", newline="\n") as file_obj:
            file_descriptor = None
            _json.dump(favorites, file_obj, ensure_ascii=False, separators=(",", ":"))
            file_obj.write("\n")
            file_obj.flush()
            os.fsync(file_obj.fileno())
        os.replace(temp_path, _FAVORITES_FILE)
        temp_path = None
    except (OSError, ValueError, TypeError) as exc:
        raise _FavoritesStorageError("无法保存收藏文件") from exc
    finally:
        if file_descriptor is not None:
            try:
                os.close(file_descriptor)
            except OSError:
                pass
        if temp_path is not None:
            try:
                os.remove(temp_path)
            except OSError:
                pass


def _load_favorites():
    """线程安全地从磁盘加载收藏列表。"""
    with _FAVORITES_LOCK:
        return _load_favorites_unlocked()


def _favorites_storage_error_response(exc):
    logger.warning("收藏存储操作失败: %s", exc)
    return jsonify({
        "success": False,
        "error": "收藏数据暂时不可用，请稍后重试",
        "code": "favorites_storage_error",
    }), 500


@app.route("/api/favorites", methods=["GET"])
def api_get_favorites():
    """获取收藏列表"""
    try:
        return jsonify({"success": True, "favorites": _load_favorites()})
    except _FavoritesStorageError as exc:
        return _favorites_storage_error_response(exc)


@app.route("/api/favorites", methods=["POST"])
def api_toggle_favorite():
    """添加/取消收藏（明确指定 action，避免 toggle 竞态）"""
    from flask import request

    if (
        request.content_length is not None
        and request.content_length > _FAVORITES_MAX_PAYLOAD_BYTES
    ):
        return jsonify({
            "success": False,
            "error": "请求体过大",
            "code": "payload_too_large",
        }), 413

    body = request.get_json(silent=True)
    if not isinstance(body, dict):
        return jsonify({
            "success": False,
            "error": "请求体必须是 JSON 对象",
            "code": "invalid_request",
        }), 400

    try:
        title = _normalize_favorite_field(body.get("title"), "title", required=True)
        artist = _normalize_favorite_field(
            body.get("artist"), "artist", required=True
        )
        chart = _normalize_favorite_field(body.get("chart"), "chart")
    except ValueError as exc:
        return jsonify({
            "success": False,
            "error": str(exc),
            "code": "validation_error",
        }), 400

    raw_action = body.get("action", "")
    if raw_action is None:
        raw_action = ""
    if not isinstance(raw_action, str):
        return jsonify({
            "success": False,
            "error": "action 必须是字符串",
            "code": "invalid_action",
        }), 400
    action = raw_action.strip().lower()
    if action not in ("", "toggle", "add", "remove"):
        return jsonify({
            "success": False,
            "error": "action 仅支持 add、remove 或 toggle",
            "code": "invalid_action",
        }), 400

    try:
        with _FAVORITES_LOCK:
            favorites = _load_favorites_unlocked()
            index = next((
                index
                for index, favorite in enumerate(favorites)
                if favorite["title"] == title and favorite["artist"] == artist
            ), -1)
            changed = False

            if action == "add":
                result = "added"
                if index < 0:
                    if len(favorites) >= _FAVORITES_MAX_COUNT:
                        return jsonify({
                            "success": False,
                            "error": f"收藏数量不能超过 {_FAVORITES_MAX_COUNT} 首",
                            "code": "favorite_limit_reached",
                        }), 409
                    favorites.append({"title": title, "artist": artist, "chart": chart})
                    changed = True
            elif action == "remove":
                result = "removed"
                if index >= 0:
                    favorites.pop(index)
                    changed = True
            elif index >= 0:
                favorites.pop(index)
                result = "removed"
                changed = True
            else:
                if len(favorites) >= _FAVORITES_MAX_COUNT:
                    return jsonify({
                        "success": False,
                        "error": f"收藏数量不能超过 {_FAVORITES_MAX_COUNT} 首",
                        "code": "favorite_limit_reached",
                    }), 409
                favorites.append({"title": title, "artist": artist, "chart": chart})
                result = "added"
                changed = True

            if changed:
                _save_favorites_unlocked(favorites)
    except _FavoritesStorageError as exc:
        return _favorites_storage_error_response(exc)

    return jsonify({
        "success": True,
        "action": result,
        "changed": changed,
        "favorites": favorites,
    })


@app.route("/api/spotify/config", methods=["GET"])
def api_spotify_config():
    """返回公开的 Spotify PKCE 配置，不返回或要求 Client Secret。"""
    from flask import request

    client_id = os.environ.get("SPOTIFY_CLIENT_ID", "").strip()
    redirect_uri = os.environ.get("SPOTIFY_REDIRECT_URI", "").strip()
    if not redirect_uri:
        redirect_uri = request.url_root.rstrip("/") + "/player"
    return jsonify({
        "success": True,
        "configured": bool(client_id),
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "scopes": [
            "streaming",
            "user-read-email",
            "user-read-private",
            "user-read-playback-state",
            "user-modify-playback-state",
        ],
    })


# ============================================================
# 音乐播放接口
# ============================================================
# 简单的进程级缓存：避免对同一首歌重复搜索
# 格式: {(title, artist): (timestamp, mp3_url)}
_play_url_cache: dict = {}
# 额外缓存：每个 song_id 对应的 session（带 cookie + authSecret 上下文）
# 让 stream 代理能用同一个 session 拉 mp3，避免 403
_play_url_sessions: dict = {}
_PLAY_URL_CACHE_TTL = 3600  # 1 小时
# 播放状态只缓存短时间；版权、地区和登录状态都可能变化。
_playability_cache: dict = {}
_PLAYABILITY_CACHE_TTL = 600


def _get_cached_play_url(title: str, artist: str):
    """兼容旧接口：查播放链接缓存，过期或不存在返回 None。"""
    info = _get_cached_play_info(title, artist)
    return info.get("mp3_url") if info else None


def _play_cache_key(title: str, artist: str, song_id=None):
    try:
        normalized_id = int(song_id or 0)
    except (TypeError, ValueError):
        normalized_id = 0
    return (title.strip(), artist.strip(), normalized_id)


def _get_cached_play_info(title: str, artist: str, song_id=None):
    """返回包含 URL、song_id 与试听状态的完整缓存信息。"""
    import time
    key = _play_cache_key(title, artist, song_id)
    entry = _play_url_cache.get(key)
    # 兼容更新前进程里可能存在的二元 key / (timestamp, url) 值。
    if not entry:
        entry = _play_url_cache.get((title.strip(), artist.strip()))
    if not entry:
        return None
    if isinstance(entry, dict):
        ts = entry.get("timestamp", 0)
        info = dict(entry)
    else:
        try:
            ts, url = entry
        except (TypeError, ValueError):
            return None
        info = {"timestamp": ts, "mp3_url": url, "song_id": song_id or ""}
    if time.time() - ts > _PLAY_URL_CACHE_TTL:
        _play_url_cache.pop(key, None)
        return None
    return info


@app.route("/api/songs/playability", methods=["POST"])
def api_songs_playability():
    """批量预检榜单歌曲当前是否可播，供前端准确筛选和标记。"""
    try:
        from flask import request
        import time
        body = request.get_json(silent=True) or {}
        songs = body.get("songs") or []
        if not isinstance(songs, list):
            return jsonify({"success": False, "error": "songs 必须是数组"}), 400

        entries = []
        seen = set()
        for song in songs[:250]:
            if not isinstance(song, dict):
                continue
            try:
                song_id = int(song.get("song_id") or song.get("id"))
            except (TypeError, ValueError):
                continue
            if song_id <= 0 or song_id in seen:
                continue
            seen.add(song_id)
            entries.append({"song_id": song_id, "fee": song.get("fee")})

        now = time.time()
        statuses = {}
        missing = []
        for entry in entries:
            cached = _playability_cache.get(entry["song_id"])
            if cached and now - cached[0] <= _PLAYABILITY_CACHE_TTL:
                statuses[entry["song_id"]] = dict(cached[1])
            else:
                _playability_cache.pop(entry["song_id"], None)
                missing.append(entry)

        if missing:
            checked = _scraper.check_song_playability(missing)
            for status in checked:
                song_id = status.get("song_id")
                if not song_id:
                    continue
                statuses[song_id] = status
                if status.get("reason") != "service_unavailable":
                    _playability_cache[song_id] = (now, dict(status))

        return jsonify({
            "success": True,
            "results": [statuses[entry["song_id"]] for entry in entries if entry["song_id"] in statuses],
        })
    except Exception as e:
        logger.error("批量检查播放状态失败: %s", e, exc_info=True)
        return jsonify({"success": False, "error": "播放状态检查失败"}), 500


@app.route("/api/song/lyric", methods=["POST"])
def api_song_lyric():
    """获取歌曲的 LRC 歌词

    优先从网易云搜索接口拿到 song_id，然后调 lyric 接口拿 LRC 文本。
    """
    try:
        from flask import request
        body = request.get_json(silent=True) or {}
        title = (body.get("title") or "").strip()
        artist = (body.get("artist") or "").strip()
        if not title or not artist:
            return jsonify({"success": False, "error": "缺少 title 或 artist"}), 400

        # 用现有 scraper session 拉取。
        try:
            session = _scraper._build_session()
        except Exception:
            session = requests.Session()

        # 1) 搜歌拿到 song_id。歌词不要求歌曲本身可完整播放，避免先请求播放权限。
        song_id = _scraper.search_song_id(title, artist)

        if not song_id:
            return jsonify({"success": False, "error": "未找到该歌曲 song_id"}), 404

        # 2) 调 lyric 接口
        lyric_url = f"https://music.163.com/api/song/lyric?id={song_id}&lv=1&tv=1&kv=1"
        try:
            r = session.get(lyric_url, headers={"Referer": "https://music.163.com/"}, timeout=8)
            # 网易云 v3+ API 加密：非 JSON 响应（HTML/二进制）一律视为不可用
            ct = (r.headers.get("Content-Type") or "").lower()
            if "json" not in ct and "javascript" not in ct:
                return jsonify({
                    "success": False,
                    "error": "网易云歌词接口已加密（API 响应非 JSON）",
                    "encrypted": True,
                }), 200
            try:
                j = r.json()
            except Exception:
                return jsonify({
                    "success": False,
                    "error": "歌词接口响应不是有效 JSON（可能被加密）",
                    "encrypted": True,
                }), 200
        except Exception as e:
            return jsonify({"success": False, "error": f"歌词接口请求失败: {e}"}), 502

        if j.get("code") != 200:
            return jsonify({"success": False, "error": "歌词接口返回错误", "code": j.get("code")}), 502

        lyric_text = ((j.get("lrc") or {}).get("lyric")) or ""
        tlyric_text = ((j.get("tlyric") or {}).get("lyric")) or ""

        return jsonify({
            "success": True,
            "song_id": song_id,
            "lyric": lyric_text,
            "tlyric": tlyric_text,
        })
    except Exception as e:
        logger.error("获取歌词失败: %s", e, exc_info=True)
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/song/play_url", methods=["POST"])
def api_song_play_url():
    """根据歌名+歌手返回可播放的 mp3 URL

    网易云直链经常变，且带防盗链。本接口在后端调用网易云搜索/播放接口，
    拿到 mp3 URL 后，前端应该通过 /api/song/stream 代理请求以避免 403。
    """
    try:
        from flask import request
        body = request.get_json(silent=True) or {}
        title = (body.get("title") or "").strip()
        artist = (body.get("artist") or "").strip()
        requested_song_id = body.get("song_id")
        requested_fee = body.get("fee")
        if not title or not artist:
            return jsonify({"success": False, "error": "缺少 title 或 artist"})

        # 命中缓存直接返回
        cached = _get_cached_play_info(title, artist, requested_song_id)
        if cached:
            return jsonify({
                "success": True,
                "mp3_url": cached["mp3_url"],
                "song_id": cached.get("song_id") or requested_song_id or "",
                "bitrate": cached.get("bitrate"),
                "is_trial": cached.get("is_trial", False),
                "cached": True,
            })

        # 详细解析优先使用榜单自带 song_id，并明确区分 VIP、付费与版权限制。
        # 不尝试绕过平台的会员、地区或访问控制。
        if hasattr(_scraper, "resolve_play_url_detailed"):
            info = _scraper.resolve_play_url_detailed(
                title,
                artist,
                song_id=requested_song_id,
                fee=requested_fee,
            )
        else:
            legacy = _scraper.resolve_play_url_streamable(title, artist)
            info = {"success": bool(legacy), **(legacy or {})}
        if not info.get("success"):
            return jsonify({key: value for key, value in info.items() if key != "_session"})

        import time

        mp3_url = info["mp3_url"]
        # 把 session 暂存到全局，让 stream 接口复用
        if info.get("_session") is not None:
            _play_url_sessions[info["song_id"]] = info["_session"]
        cache_info = {
            "timestamp": time.time(),
            "mp3_url": mp3_url,
            "song_id": info["song_id"],
            "bitrate": info.get("bitrate"),
            "is_trial": info.get("is_trial", False),
        }
        _play_url_cache[_play_cache_key(title, artist, requested_song_id)] = cache_info
        _play_url_cache[_play_cache_key(title, artist, info["song_id"])] = cache_info
        _play_url_cache[_play_cache_key(title, artist)] = cache_info
        return jsonify({
            "success": True,
            "mp3_url": mp3_url,
            "song_id": info["song_id"],
            "bitrate": info.get("bitrate"),
            "is_trial": info.get("is_trial", False),
            "matched_title": info.get("matched_title", title),
            "matched_artist": info.get("matched_artist", artist),
            "cached": False,
        })
    except Exception as e:
        logger.error("获取播放链接失败: %s", e, exc_info=True)
        return jsonify({"success": False, "error": str(e)})


@app.route("/api/song/stream")
def api_song_stream():
    """代理转发 mp3 音频流（解决网易云防盗链 403）

    前端 <audio src="/api/song/stream?url=..."> 这样调用。
    后端：
    1. 用 _scraper 的 session（自动带 VIP cookie + UA + 浏览器指纹）
    2. 先访问首页建立完整会话（拿到衍生 cookie）
    3. 再带 Referer 拉 mp3（避免 403）
    """
    try:
        from flask import request
        from urllib.parse import unquote, urlparse
        mp3_url = unquote(request.args.get("url", ""))
        song_id_param = request.args.get("song_id", "")
        parsed_url = urlparse(mp3_url)
        hostname = (parsed_url.hostname or "").lower()
        trusted_host = (
            hostname in {"music.163.com", "music.126.net"}
            or hostname.endswith(".music.163.com")
            or hostname.endswith(".music.126.net")
        )
        if parsed_url.scheme not in {"http", "https"} or not trusted_host:
            return jsonify({"success": False, "error": "无效 URL"}), 400

        # 优先用 play_url 接口暂存的 session（带 cookie + 正确的 authSecret 上下文）
        session = None
        try:
            if song_id_param and int(song_id_param) in _play_url_sessions:
                session = _play_url_sessions[int(song_id_param)]
        except (ValueError, TypeError):
            pass
        if not session:
            session = _scraper._build_session()

        # 先访问首页建立完整会话（关键：拿到衍生 cookie）
        try:
            session.get("https://music.163.com/", timeout=10)
        except Exception:
            pass  # 首页拉不到也不影响后续

        # 透传 Range 请求（关键：拖动进度条时浏览器会发 Range=bytes=X-Y，
        # 不透传的话每次 seek 都重头下载，音频会跳回开头）
        forward_headers = {"Referer": "https://music.163.com/"}
        range_header = request.headers.get("Range")
        if range_header:
            forward_headers["Range"] = range_header

        # 拉 mp3
        upstream = session.get(
            mp3_url,
            headers=forward_headers,
            stream=True,
            timeout=20,
            allow_redirects=False,
        )

        if upstream.status_code not in (200, 206):
            logger.warning(
                "音频流转发失败: HTTP %s for %s",
                upstream.status_code,
                mp3_url[:80],
            )
            return (
                jsonify({"success": False, "error": f"上游 HTTP {upstream.status_code}"}),
                502,
            )

        # 透传关键响应头
        content_type = upstream.headers.get("Content-Type", "audio/mpeg")
        response_headers = {
            "Cache-Control": "public, max-age=3600",
            "Accept-Ranges": "bytes",
        }
        # 透传 content-length / content-range（206 场景下浏览器需要）
        content_length = upstream.headers.get("Content-Length")
        if content_length:
            response_headers["Content-Length"] = content_length
        content_range = upstream.headers.get("Content-Range")
        if content_range:
            response_headers["Content-Range"] = content_range

        # 下载模式：加 Content-Disposition 触发浏览器下载
        if request.args.get("download") == "1":
            # 文件名清洗：去掉非法字符
            from urllib.parse import unquote as _unquote
            raw_name = request.args.get("filename", "audio.mp3")
            safe_name = "".join(
                c for c in raw_name if c not in r'<>:"/\|?*'
            ).strip() or "audio.mp3"
            if not safe_name.lower().endswith(".mp3"):
                safe_name += ".mp3"
            # RFC 5987 编码（兼容中文/特殊字符）
            from urllib.parse import quote
            response_headers["Content-Disposition"] = (
                f"attachment; filename=\"audio.mp3\"; "
                f"filename*=UTF-8''{quote(safe_name)}"
            )
            # 下载用流式时禁用缓存，确保拿到完整文件
            response_headers["Cache-Control"] = "no-cache"

        return Response(
            upstream.iter_content(chunk_size=8192),
            status=upstream.status_code,
            content_type=content_type,
            headers=response_headers,
        )
    except Exception as e:
        logger.error("音频流代理失败: %s", e, exc_info=True)
        return jsonify({"success": False, "error": str(e)}), 500


# ============================================================
# Entry point
# ============================================================
def _on_scheduler_run(result) -> None:
    """调度器回调：爬取与保存已由 Scheduler 完成，这里只刷新内存热榜。"""
    global _scraped_data
    try:
        if not getattr(result, "success", False):
            return
        latest = _history_mgr.get_chart_snapshot("热歌榜") or []
        _scraped_data = [
            SongData(
                rank=item["rank"],
                title=item["title"],
                artist=item["artist"],
                song_id=item.get("song_id"),
                fee=item.get("fee"),
            )
            for item in latest
        ]
        logger.info("调度器自动爬取完成，内存热榜已刷新（%d 首）", len(_scraped_data))
    except Exception as e:
        logger.error("调度器回调异常: %s", e, exc_info=True)


if __name__ == "__main__":
    logger.info("=" * 60)
    logger.info("  Music Analytics Dashboard")
    logger.info("  NetEase Cloud Music Hot Songs")
    logger.info("=" * 60)
    logger.info("  Server: http://%s:%s", config.host, config.port)
    logger.info("  Stop:   Ctrl+C")
    logger.info("=" * 60)

    # 自动启动调度器
    if config.auto_refresh_on_start:
        try:
            s = _get_or_create_scheduler()
            s.add_callback(_on_scheduler_run)
            s.start()
            logger.info("定时调度器已自动启动（间隔 %s 秒）", config.auto_refresh_interval)
        except Exception as e:
            logger.warning("调度器启动失败（手动模式）: %s", e)

    pid_file = os.path.join(_PROJECT_ROOT, "flask.pid")
    try:
        with open(pid_file, "w", encoding="utf-8") as handle:
            handle.write(str(os.getpid()))
        app.run(host=config.host, port=config.port, debug=config.debug)
    finally:
        try:
            if os.path.exists(pid_file):
                with open(pid_file, "r", encoding="utf-8") as handle:
                    if handle.read().strip() == str(os.getpid()):
                        os.remove(pid_file)
        except OSError:
            pass
