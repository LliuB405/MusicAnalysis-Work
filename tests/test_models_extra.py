# -*- coding: utf-8 -*-
"""
SongData / ArtistStat / ScrapeResult 边界测试
"""

import pytest
from datetime import datetime

from music_analytics.models import SongData, ArtistStat, ScrapeResult, AnalysisResult


class TestSongDataEdge:
    """SongData 边界测试"""

    def test_empty_artist_defaults(self):
        """空歌手时使用默认值"""
        song = SongData(rank=1, title="test", artist="")
        assert song.artist == "未知歌手"

    def test_from_dict_missing_fields_raises(self):
        """from_dict 缺失 rank 字段时，rank=0 触发校验"""
        with pytest.raises(ValueError):
            SongData.from_dict({})

    def test_from_dict_partial(self):
        """from_dict 至少提供 rank"""
        song = SongData.from_dict({"rank": 1, "title": "test"})
        assert song.rank == 1
        assert song.artist == "未知歌手"

    def test_to_dict_keys(self):
        """to_dict 返回的 key 完整"""
        song = SongData(rank=1, title="晴天", artist="周杰伦")
        d = song.to_dict()
        assert set(d.keys()) == {"rank", "title", "artist"}


class TestArtistStatEdge:
    """ArtistStat 边界测试"""

    def test_negative_count_raises(self):
        """负数 count 抛错"""
        with pytest.raises(ValueError):
            ArtistStat(name="test", count=-1)

    def test_default_percentage(self):
        """默认 percentage=0"""
        stat = ArtistStat(name="test", count=5)
        assert stat.percentage == 0.0


class TestScrapeResultEdge:
    """ScrapeResult 边界测试"""

    def test_count_is_zero_when_no_data(self):
        """空数据时 count=0"""
        result = ScrapeResult(success=True, method="test")
        assert result.count == 0

    def test_to_dict_has_timestamp(self):
        """to_dict 包含 timestamp"""
        result = ScrapeResult(success=True, method="API", data=[])
        d = result.to_dict()
        assert "timestamp" in d
        # 验证可被解析为 ISO 格式
        datetime.fromisoformat(d["timestamp"])

    def test_default_online(self):
        """默认 online=True"""
        result = ScrapeResult(success=True, method="x")
        assert result.online is True

    def test_error_field(self):
        """error 字段可被设置"""
        result = ScrapeResult(success=False, method="x", error="网络错误")
        assert result.error == "网络错误"
        assert result.success is False


class TestAnalysisResultEdge:
    """AnalysisResult 边界测试"""

    def test_to_dict_with_empty_top10(self):
        """空 top10"""
        result = AnalysisResult(top10=[], total_artists=0, total_songs=0)
        d = result.to_dict()
        assert d["top10"] == []
        assert d["total_artists"] == 0
        assert d["total_songs"] == 0
