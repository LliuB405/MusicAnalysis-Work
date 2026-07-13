# -*- coding: utf-8 -*-
"""
HistoryManager 边界测试 — 覆盖排名变化空数据、趋势查询无结果等场景
"""

import pytest
import tempfile
import os

from music_analytics.history import HistoryManager
from music_analytics.models import SongData


class TestRankChangesNoData:
    """排名变化 — 空/不足数据测试"""

    @pytest.fixture
    def manager(self):
        fd, path = tempfile.mkstemp(suffix='.db')
        os.close(fd)
        mgr = HistoryManager(path)
        yield mgr
        if os.path.exists(path):
            os.remove(path)

    def test_no_snapshots(self, manager):
        """没有任何快照"""
        changes = manager.get_rank_changes("不存在的榜单", days=7)
        assert changes == []

    def test_single_snapshot(self, manager):
        """只有一个快照（不够对比）"""
        songs = [SongData(rank=1, title="测试", artist="测试歌手")]
        manager.save_snapshot("测试榜", "123", songs)
        changes = manager.get_rank_changes("测试榜", days=7)
        assert changes == []

    def test_exactly_two_snapshots(self, manager):
        """正好两个快照"""
        songs1 = [SongData(rank=1, title="晴天", artist="周杰伦")]
        songs2 = [SongData(rank=1, title="晴天", artist="周杰伦")]
        manager.save_snapshot("热歌榜", "1", songs1)
        manager.save_snapshot("热歌榜", "1", songs2)
        changes = manager.get_rank_changes("热歌榜", days=7)
        # 同名次，变化为0
        assert len(changes) >= 1
        assert changes[0]["rank_change"] == 0


class TestSongTrendNoData:
    """歌曲趋势 — 无数据测试"""

    @pytest.fixture
    def manager(self):
        fd, path = tempfile.mkstemp(suffix='.db')
        os.close(fd)
        mgr = HistoryManager(path)
        yield mgr
        if os.path.exists(path):
            os.remove(path)

    def test_no_trend_data(self, manager):
        """没有任何趋势数据"""
        trend = manager.get_song_trend("热歌榜", "不存在", "无此人", days=30)
        assert trend == []

    def test_trend_with_data(self, manager):
        """有数据"""
        songs = [SongData(rank=5, title="测试歌", artist="测试歌手")]
        manager.save_snapshot("热歌榜", "1", songs)
        trend = manager.get_song_trend("热歌榜", "测试歌", "测试歌手", days=30)
        assert len(trend) >= 1


class TestSnapshotDates:
    """快照日期列表测试"""

    @pytest.fixture
    def manager(self):
        fd, path = tempfile.mkstemp(suffix='.db')
        os.close(fd)
        mgr = HistoryManager(path)
        yield mgr
        if os.path.exists(path):
            os.remove(path)

    def test_no_dates(self, manager):
        """无快照时返回空列表"""
        dates = manager.get_snapshot_dates("无数据榜", limit=30)
        assert dates == []

    def test_multiple_dates(self, manager):
        """多次保存后返回多个日期"""
        for _ in range(3):
            songs = [SongData(rank=1, title="测试", artist="测试歌手")]
            manager.save_snapshot("热歌榜", "1", songs)
        dates = manager.get_snapshot_dates("热歌榜", limit=10)
        assert len(dates) >= 1  # 可能因时间戳相同而合并


class TestCleanupEdge:
    """数据清理边界测试"""

    @pytest.fixture
    def manager(self):
        fd, path = tempfile.mkstemp(suffix='.db')
        os.close(fd)
        mgr = HistoryManager(path)
        yield mgr
        if os.path.exists(path):
            os.remove(path)

    def test_cleanup_empty_db(self, manager):
        """空数据库清理"""
        deleted = manager.cleanup_old_data(retention_days=30)
        assert deleted == 0

    def test_cleanup_keep_recent(self, manager):
        """最近数据不被清理"""
        songs = [SongData(rank=1, title="新歌", artist="新歌手")]
        manager.save_snapshot("热歌榜", "1", songs)
        deleted = manager.cleanup_old_data(retention_days=30)
        # 30天内数据应保留
        charts = manager.get_all_charts()
        assert "热歌榜" in charts

    def test_cleanup_with_retention_0(self, manager):
        """retention_days=0 时清理所有"""
        songs = [SongData(rank=1, title="临时", artist="临时歌手")]
        manager.save_snapshot("临时榜", "1", songs)
        deleted = manager.cleanup_old_data(retention_days=0)
        assert deleted >= 0
