# -*- coding: utf-8 -*-
"""
测试模块 - 历史数据管理测试
"""

import pytest
import tempfile
import os
from datetime import datetime, timedelta
from music_analytics.history import HistoryManager
from music_analytics.models import SongData


class TestHistoryManager:
    """测试历史数据管理器"""

    @pytest.fixture
    def temp_db(self):
        """创建临时数据库"""
        fd, path = tempfile.mkstemp(suffix='.db')
        os.close(fd)
        yield path
        if os.path.exists(path):
            os.remove(path)

    @pytest.fixture
    def history_manager(self, temp_db):
        """创建历史管理器实例"""
        return HistoryManager(temp_db)

    @pytest.fixture
    def sample_songs(self):
        """示例歌曲数据"""
        return [
            SongData(rank=1, title="晴天", artist="周杰伦"),
            SongData(rank=2, title="七里香", artist="周杰伦"),
            SongData(rank=3, title="十年", artist="陈奕迅"),
            SongData(rank=4, title="浮夸", artist="陈奕迅"),
            SongData(rank=5, title="海阔天空", artist="Beyond"),
        ]

    def test_init_db(self, temp_db):
        """测试数据库初始化"""
        manager = HistoryManager(temp_db)
        assert os.path.exists(temp_db)

    def test_save_snapshot(self, history_manager, sample_songs):
        """测试保存快照"""
        snapshot_id = history_manager.save_snapshot(
            chart_name="热歌榜",
            chart_id="3778678",
            songs=sample_songs
        )
        assert snapshot_id > 0

    def test_get_chart_snapshot(self, history_manager, sample_songs):
        """测试获取榜单快照"""
        history_manager.save_snapshot(
            chart_name="热歌榜",
            chart_id="3778678",
            songs=sample_songs
        )

        snapshot = history_manager.get_chart_snapshot("热歌榜")
        assert snapshot is not None
        assert len(snapshot) == 5

    def test_latest_snapshot_only_and_playback_metadata(self, history_manager):
        """最新榜单不能混入旧快照，并应保留 song_id / fee。"""
        history_manager.save_snapshot(
            "测试榜",
            "1",
            [
                SongData(rank=1, title="旧歌一", artist="歌手", song_id=11, fee=8),
                SongData(rank=2, title="旧歌二", artist="歌手", song_id=12, fee=1),
            ],
        )
        history_manager.save_snapshot(
            "测试榜",
            "1",
            [SongData(rank=1, title="新歌", artist="新歌手", song_id=21, fee=0)],
        )

        snapshot = history_manager.get_chart_snapshot("测试榜")
        assert snapshot is not None
        assert len(snapshot) == 1
        assert snapshot[0]["title"] == "新歌"
        assert snapshot[0]["song_id"] == 21
        assert snapshot[0]["fee"] == 0

    def test_get_song_trend(self, history_manager, sample_songs):
        """测试获取歌曲趋势"""
        # 保存多个时间点的数据
        for _ in range(3):
            history_manager.save_snapshot(
                chart_name="热歌榜",
                chart_id="3778678",
                songs=sample_songs
            )

        trend = history_manager.get_song_trend(
            chart_name="热歌榜",
            song_title="晴天",
            artist="周杰伦",
            days=30
        )
        assert len(trend) >= 3

    def test_get_rank_changes(self, history_manager):
        """测试获取排名变化"""
        # 保存两个时间点的数据
        songs1 = [
            SongData(rank=1, title="晴天", artist="周杰伦"),
            SongData(rank=2, title="七里香", artist="周杰伦"),
        ]
        songs2 = [
            SongData(rank=1, title="七里香", artist="周杰伦"),
            SongData(rank=2, title="晴天", artist="周杰伦"),
        ]

        history_manager.save_snapshot("热歌榜", "3778678", songs1)
        history_manager.save_snapshot("热歌榜", "3778678", songs2)

        changes = history_manager.get_rank_changes("热歌榜", days=7)
        assert len(changes) > 0

    def test_cleanup_old_data(self, history_manager, sample_songs):
        """测试清理过期数据"""
        # 保存数据
        history_manager.save_snapshot("热歌榜", "3778678", sample_songs)

        # 清理30天前的数据（应该不删除）
        deleted = history_manager.cleanup_old_data(retention_days=30)
        assert deleted >= 0

    def test_get_all_charts(self, history_manager, sample_songs):
        """测试获取所有榜单"""
        history_manager.save_snapshot("热歌榜", "3778678", sample_songs)
        history_manager.save_snapshot("新歌榜", "3779629", sample_songs[:3])

        charts = history_manager.get_all_charts()
        assert "热歌榜" in charts
        assert "新歌榜" in charts

    def test_get_snapshot_dates(self, history_manager, sample_songs):
        """测试获取快照日期列表"""
        history_manager.save_snapshot("热歌榜", "3778678", sample_songs)

        dates = history_manager.get_snapshot_dates("热歌榜", limit=10)
        assert len(dates) >= 1
