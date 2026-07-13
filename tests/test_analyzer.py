# -*- coding: utf-8 -*-
"""
ArtistAnalyzer 单元测试
"""

import pytest
from music_analytics.models import SongData
from music_analytics.analyzer import ArtistAnalyzer


class TestArtistAnalyzer:
    """测试歌手分析器"""

    @pytest.fixture
    def sample_songs(self):
        """示例歌曲数据"""
        return [
            SongData(rank=1, title="晴天", artist="周杰伦"),
            SongData(rank=2, title="七里香", artist="周杰伦"),
            SongData(rank=3, title="十年", artist="陈奕迅"),
            SongData(rank=4, title="浮夸", artist="陈奕迅"),
        ]

    @pytest.fixture
    def mixed_songs(self):
        """含合唱/多分隔符的歌曲数据"""
        return [
            SongData(rank=1, title="因为爱情", artist="陈奕迅 / 王菲"),
            SongData(rank=2, title="可一可再", artist="陈奕迅、王菲"),
            SongData(rank=3, title="孤勇者", artist="陈奕迅"),
        ]

    def test_total_songs(self, sample_songs):
        """测试歌曲总数"""
        analyzer = ArtistAnalyzer(sample_songs)
        assert analyzer.total_songs == 4

    def test_total_songs_empty(self):
        """测试空数据集的总数"""
        analyzer = ArtistAnalyzer([])
        assert analyzer.total_songs == 0

    def test_get_all_artists(self, sample_songs):
        """测试获取所有歌手"""
        analyzer = ArtistAnalyzer(sample_songs)
        artists = analyzer.get_all_artists()
        assert artists.count("周杰伦") == 2
        assert artists.count("陈奕迅") == 2
        assert len(artists) == 4

    def test_get_all_artists_handles_collaborations(self, mixed_songs):
        """测试合唱歌曲的歌手拆分"""
        analyzer = ArtistAnalyzer(mixed_songs)
        artists = analyzer.get_all_artists()
        # 第一个歌：陈奕迅、王菲；第二个歌：陈奕迅、王菲；第三个：陈奕迅
        assert artists.count("陈奕迅") == 3
        assert artists.count("王菲") == 2

    def test_count_artist_frequency(self, sample_songs):
        """测试歌手频次统计"""
        analyzer = ArtistAnalyzer(sample_songs)
        counter = analyzer.count_artist_frequency()
        assert counter["周杰伦"] == 2
        assert counter["陈奕迅"] == 2
        assert len(counter) == 2

    def test_get_top_artists(self, sample_songs):
        """测试获取 TOP 歌手"""
        analyzer = ArtistAnalyzer(sample_songs)
        top2 = analyzer.get_top_artists(2)
        assert len(top2) == 2
        # 排名 1 和 2 都是 2 次
        assert all(stat.count == 2 for stat in top2)

    def test_get_top_artists_n_larger_than_unique(self, sample_songs):
        """当 n 超过唯一个数时，返回所有"""
        analyzer = ArtistAnalyzer(sample_songs)
        top100 = analyzer.get_top_artists(100)
        assert len(top100) == 2  # 实际只有2个歌手

    def test_get_top_artists_percentage(self, sample_songs):
        """测试百分比计算"""
        analyzer = ArtistAnalyzer(sample_songs)
        top2 = analyzer.get_top_artists(2)
        # 总共4次上榜，每个歌手2次，50%
        for stat in top2:
            assert stat.percentage == 50.0

    def test_get_top_artists_empty(self):
        """测试空数据"""
        analyzer = ArtistAnalyzer([])
        top = analyzer.get_top_artists(10)
        assert top == []

    def test_get_unique_artists(self, mixed_songs):
        """测试去重歌手集合"""
        analyzer = ArtistAnalyzer(mixed_songs)
        unique = analyzer.get_unique_artists()
        assert unique == {"陈奕迅", "王菲"}

    def test_analyze(self, sample_songs):
        """测试完整分析"""
        analyzer = ArtistAnalyzer(sample_songs)
        result = analyzer.analyze()
        assert result.total_songs == 4
        assert result.total_artists == 2
        assert len(result.top10) == 2

    def test_analyze_empty(self):
        """空数据时 analyze"""
        analyzer = ArtistAnalyzer([])
        result = analyzer.analyze()
        assert result.total_songs == 0
        assert result.total_artists == 0
        assert result.top10 == []

    def test_get_artist_dict(self, sample_songs):
        """测试歌手字典（用于词云）"""
        analyzer = ArtistAnalyzer(sample_songs)
        d = analyzer.get_artist_dict()
        assert isinstance(d, dict)
        assert d == {"周杰伦": 2, "陈奕迅": 2}
