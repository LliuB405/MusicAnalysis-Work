# -*- coding: utf-8 -*-
"""
历史数据管理模块 - 数据持久化层
"""

import json
import os
import sqlite3
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any
from threading import Lock
from dataclasses import asdict

from .models import SongData

logger = logging.getLogger(__name__)


class HistoryManager:
    """历史数据管理器"""

    def __init__(self, db_path: Optional[str] = None) -> None:
        if db_path is None:
            db_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "history.db")

        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self.db_path = db_path
        self._lock = Lock()

        # 初始化数据库
        self._init_db()

    def _init_db(self) -> None:
        """初始化数据库表"""
        with self._lock:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # 榜单快照表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS chart_snapshots (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    chart_name TEXT NOT NULL,
                    chart_id TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # 歌曲排名表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS song_ranks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    snapshot_id INTEGER NOT NULL,
                    song_title TEXT NOT NULL,
                    artist TEXT NOT NULL,
                    rank INTEGER NOT NULL,
                    song_id INTEGER,
                    fee INTEGER,
                    FOREIGN KEY (snapshot_id) REFERENCES chart_snapshots(id),
                    UNIQUE(snapshot_id, song_title, artist)
                )
            """)

            # 对旧数据库做无损增量迁移，不需要删除已有的历史快照。
            cursor.execute("PRAGMA table_info(song_ranks)")
            rank_columns = {row[1] for row in cursor.fetchall()}
            if "song_id" not in rank_columns:
                cursor.execute("ALTER TABLE song_ranks ADD COLUMN song_id INTEGER")
            if "fee" not in rank_columns:
                cursor.execute("ALTER TABLE song_ranks ADD COLUMN fee INTEGER")

            # 歌曲趋势表（记录单首歌的历史排名变化）
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS song_trends (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    chart_name TEXT NOT NULL,
                    song_title TEXT NOT NULL,
                    artist TEXT NOT NULL,
                    rank INTEGER NOT NULL,
                    timestamp TEXT NOT NULL,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(chart_name, song_title, artist, timestamp)
                )
            """)

            # 创建索引
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_snapshots_chart ON chart_snapshots(chart_name)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_snapshots_time ON chart_snapshots(timestamp)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_trends_song ON song_trends(chart_name, song_title, artist)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_trends_time ON song_trends(timestamp)")

            conn.commit()
            conn.close()

    def save_snapshot(self, chart_name: str, chart_id: str, songs: List[SongData]) -> int:
        """保存榜单快照"""
        with self._lock:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            timestamp = datetime.now().isoformat()

            # 插入快照记录
            cursor.execute(
                "INSERT INTO chart_snapshots (chart_name, chart_id, timestamp) VALUES (?, ?, ?)",
                (chart_name, chart_id, timestamp)
            )
            snapshot_id = cursor.lastrowid

            # 插入歌曲排名
            for song in songs:
                try:
                    cursor.execute(
                        """INSERT INTO song_ranks
                           (snapshot_id, song_title, artist, rank, song_id, fee)
                           VALUES (?, ?, ?, ?, ?, ?)""",
                        (snapshot_id, song.title, song.artist, song.rank, song.song_id, song.fee)
                    )
                except sqlite3.IntegrityError:
                    pass  # 忽略重复记录

                # 同时更新趋势表
                try:
                    cursor.execute(
                        """INSERT INTO song_trends (chart_name, song_title, artist, rank, timestamp)
                           VALUES (?, ?, ?, ?, ?)""",
                        (chart_name, song.title, song.artist, song.rank, timestamp)
                    )
                except sqlite3.IntegrityError:
                    # 已存在则更新排名
                    cursor.execute(
                        """UPDATE song_trends SET rank = ?, timestamp = ?
                           WHERE chart_name = ? AND song_title = ? AND artist = ? AND timestamp = ?""",
                        (song.rank, timestamp, chart_name, song.title, song.artist, timestamp)
                    )

            conn.commit()
            conn.close()

            logger.info(f"[历史] 保存榜单 {chart_name} 快照，包含 {len(songs)} 首歌曲")
            return snapshot_id

    def get_song_trend(self, chart_name: str, song_title: str, artist: str, days: int = 30) -> List[Dict[str, Any]]:
        """获取歌曲的历史排名趋势"""
        with self._lock:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            start_time = (datetime.now() - timedelta(days=days)).isoformat()

            cursor.execute(
                """SELECT rank, timestamp FROM song_trends
                   WHERE chart_name = ? AND song_title = ? AND artist = ? AND timestamp >= ?
                   ORDER BY timestamp ASC""",
                (chart_name, song_title, artist, start_time)
            )

            results = [
                {"rank": row[0], "timestamp": row[1]}
                for row in cursor.fetchall()
            ]

            conn.close()
            return results

    def get_chart_snapshot(self, chart_name: str, timestamp: Optional[str] = None) -> Optional[List[Dict[str, Any]]]:
        """获取指定榜单的历史快照"""
        with self._lock:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            if timestamp:
                cursor.execute(
                    """SELECT s.rank, s.song_title, s.artist, ss.timestamp
                       FROM song_ranks s
                       JOIN chart_snapshots ss ON s.snapshot_id = ss.id
                       WHERE ss.chart_name = ? AND ss.timestamp = ?
                       ORDER BY s.rank ASC""",
                    (chart_name, timestamp)
                )
            else:
                # 只读取最新的一份快照。旧实现仅按时间倒序 LIMIT 200，
                # 榜单不足 200 首时会把前几次快照混在一起。
                cursor.execute(
                    """SELECT s.rank, s.song_title, s.artist, ss.timestamp,
                              s.song_id, s.fee
                       FROM song_ranks s
                       JOIN chart_snapshots ss ON s.snapshot_id = ss.id
                       WHERE s.snapshot_id = (
                           SELECT id FROM chart_snapshots
                           WHERE chart_name = ?
                           ORDER BY timestamp DESC, id DESC
                           LIMIT 1
                       )
                       ORDER BY s.rank ASC""",
                    (chart_name,)
                )

            rows = cursor.fetchall()
            results = []
            for row in rows:
                item = {"rank": row[0], "title": row[1], "artist": row[2], "timestamp": row[3]}
                if len(row) > 4 and row[4] is not None:
                    item["song_id"] = row[4]
                if len(row) > 5 and row[5] is not None:
                    item["fee"] = row[5]
                results.append(item)

            conn.close()
            return results if results else None

    def get_rank_changes(self, chart_name: str, days: int = 7) -> List[Dict[str, Any]]:
        """获取排名变化情况"""
        with self._lock:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            end_time = datetime.now().isoformat()
            start_time = (datetime.now() - timedelta(days=days)).isoformat()

            # 获取最早和最新的快照进行对比
            cursor.execute(
                """SELECT DISTINCT timestamp FROM chart_snapshots
                   WHERE chart_name = ? AND timestamp >= ? AND timestamp <= ?
                   ORDER BY timestamp ASC""",
                (chart_name, start_time, end_time)
            )

            timestamps = [row[0] for row in cursor.fetchall()]

            if len(timestamps) < 2:
                conn.close()
                return []

            old_timestamp = timestamps[0]
            new_timestamp = timestamps[-1]

            # 获取旧排名
            cursor.execute(
                """SELECT s.song_title, s.artist, s.rank FROM song_ranks s
                   JOIN chart_snapshots ss ON s.snapshot_id = ss.id
                   WHERE ss.chart_name = ? AND ss.timestamp = ?""",
                (chart_name, old_timestamp)
            )
            old_ranks = {(row[0], row[1]): row[2] for row in cursor.fetchall()}

            # 获取新排名
            cursor.execute(
                """SELECT s.song_title, s.artist, s.rank FROM song_ranks s
                   JOIN chart_snapshots ss ON s.snapshot_id = ss.id
                   WHERE ss.chart_name = ? AND ss.timestamp = ?""",
                (chart_name, new_timestamp)
            )
            new_ranks = {(row[0], row[1]): row[2] for row in cursor.fetchall()}

            conn.close()

            # 计算排名变化
            changes = []
            for (title, artist), new_rank in new_ranks.items():
                old_rank = old_ranks.get((title, artist))
                if old_rank is not None:
                    rank_change = old_rank - new_rank  # 正数表示上升
                    changes.append({
                        "title": title,
                        "artist": artist,
                        "old_rank": old_rank,
                        "new_rank": new_rank,
                        "rank_change": rank_change
                    })

            # 按排名变化排序
            changes.sort(key=lambda x: x["rank_change"], reverse=True)
            return changes[:20]  # 返回前20个变化最大的

    def cleanup_old_data(self, retention_days: int = 30) -> int:
        """清理过期的历史数据"""
        with self._lock:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cutoff_time = (datetime.now() - timedelta(days=retention_days)).isoformat()

            # 删除旧的快照
            cursor.execute(
                "DELETE FROM chart_snapshots WHERE timestamp < ?",
                (cutoff_time,)
            )
            deleted_snapshots = cursor.rowcount

            # 删除孤立的历史排名（没有对应快照的）
            cursor.execute(
                """DELETE FROM song_ranks
                   WHERE snapshot_id NOT IN (SELECT id FROM chart_snapshots)"""
            )
            deleted_ranks = cursor.rowcount

            # 删除旧的趋势数据
            cursor.execute(
                "DELETE FROM song_trends WHERE timestamp < ?",
                (cutoff_time,)
            )
            deleted_trends = cursor.rowcount

            conn.commit()
            conn.close()

            total_deleted = deleted_snapshots + deleted_ranks + deleted_trends
            logger.info(f"[历史] 清理过期数据，删除 {total_deleted} 条记录")
            return total_deleted

    def get_all_charts(self) -> List[str]:
        """获取所有榜单名称"""
        with self._lock:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT DISTINCT chart_name FROM chart_snapshots")
            charts = [row[0] for row in cursor.fetchall()]
            conn.close()
            return charts

    def get_snapshot_dates(self, chart_name: str, limit: int = 30) -> List[str]:
        """获取榜单的快照日期列表"""
        with self._lock:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute(
                """SELECT DISTINCT timestamp FROM chart_snapshots
                   WHERE chart_name = ?
                   ORDER BY timestamp DESC
                   LIMIT ?""",
                (chart_name, limit)
            )
            dates = [row[0] for row in cursor.fetchall()]
            conn.close()
            return dates

    def get_chart_topn_trend(
        self, chart_name: str, top_n: int = 10, days: int = 7
    ) -> Dict[str, Any]:
        """获取榜单当前 TopN 歌曲在指定天数内的排名走势。

        返回:
            {
              "chart_name": ...,
              "top_n": N,
              "days": D,
              "dates": [...timestamps...],
              "songs": [
                  {
                    "title": ..., "artist": ...,
                    "trend": [{"timestamp":..., "rank":...}, ...]
                  }, ...
              ]
            }
        """
        with self._lock:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            start_time = (datetime.now() - timedelta(days=days)).isoformat()

            # 1) 取当前最新一份快照中 TopN 的歌曲
            cursor.execute(
                """SELECT s.song_title, s.artist
                   FROM song_ranks s
                   JOIN chart_snapshots ss ON s.snapshot_id = ss.id
                   WHERE ss.chart_name = ?
                   ORDER BY ss.timestamp DESC, s.rank ASC
                   LIMIT ?""",
                (chart_name, top_n * 2),  # 多取一些以防快照重叠
            )
            rows = cursor.fetchall()
            if not rows:
                conn.close()
                return {"chart_name": chart_name, "dates": [], "songs": []}

            # 去重（同一首歌只取一次）
            seen = set()
            topn_songs = []
            for title, artist in rows:
                key = (title, artist)
                if key not in seen:
                    seen.add(key)
                    topn_songs.append((title, artist))
                if len(topn_songs) >= top_n:
                    break

            # 2) 拿时间范围内所有快照日期
            cursor.execute(
                """SELECT DISTINCT timestamp FROM chart_snapshots
                   WHERE chart_name = ? AND timestamp >= ?
                   ORDER BY timestamp ASC""",
                (chart_name, start_time),
            )
            dates = [row[0] for row in cursor.fetchall()]

            # 3) 对每首歌，统计其每天最常见的排名（众数）
            songs_trend = []
            for title, artist in topn_songs:
                cursor.execute(
                    """SELECT s.rank, ss.timestamp
                       FROM song_ranks s
                       JOIN chart_snapshots ss ON s.snapshot_id = ss.id
                       WHERE ss.chart_name = ? AND s.song_title = ? AND s.artist = ?
                         AND ss.timestamp >= ?
                       ORDER BY ss.timestamp ASC""",
                    (chart_name, title, artist, start_time),
                )
                # 同一时间点可能多条，按 timestamp 分组取中位数
                from collections import defaultdict
                rank_by_date = defaultdict(list)
                for rank, ts in cursor.fetchall():
                    rank_by_date[ts].append(rank)

                trend = []
                for ts in dates:
                    ranks = rank_by_date.get(ts, [])
                    if ranks:
                        ranks_sorted = sorted(ranks)
                        trend.append({
                            "timestamp": ts,
                            "rank": ranks_sorted[len(ranks_sorted) // 2],
                        })
                    else:
                        # 该日未上榜，记为 None（在图表里可断线）
                        trend.append({"timestamp": ts, "rank": None})

                songs_trend.append({
                    "title": title,
                    "artist": artist,
                    "trend": trend,
                })

            conn.close()
            return {
                "chart_name": chart_name,
                "top_n": top_n,
                "days": days,
                "dates": dates,
                "songs": songs_trend,
            }
