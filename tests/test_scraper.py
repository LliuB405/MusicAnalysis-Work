# -*- coding: utf-8 -*-
"""
测试模块 - 单元测试和集成测试
"""

import pytest
from music_analytics.models import SongData, ArtistStat, ScrapeResult
from music_analytics.scraper import MusicScraper
from music_analytics.analyzer import ArtistAnalyzer
from music_analytics.config import Config


class TestSongData:
    """测试歌曲数据模型"""

    def test_create_song_data(self):
        """测试创建歌曲数据"""
        song = SongData(rank=1, title="晴天", artist="周杰伦")
        assert song.rank == 1
        assert song.title == "晴天"
        assert song.artist == "周杰伦"

    def test_to_dict(self):
        """测试转换为字典"""
        song = SongData(rank=1, title="晴天", artist="周杰伦")
        d = song.to_dict()
        assert d == {"rank": 1, "title": "晴天", "artist": "周杰伦"}

    def test_from_dict(self):
        """测试从字典创建"""
        data = {"rank": 1, "title": "晴天", "artist": "周杰伦"}
        song = SongData.from_dict(data)
        assert song.rank == 1

    def test_invalid_rank(self):
        """测试无效排名"""
        with pytest.raises(ValueError):
            SongData(rank=0, title="晴天", artist="周杰伦")

    def test_empty_title(self):
        """测试空标题"""
        with pytest.raises(ValueError):
            SongData(rank=1, title="", artist="周杰伦")


class TestArtistStat:
    """测试歌手统计数据"""

    def test_create_artist_stat(self):
        """测试创建歌手统计"""
        stat = ArtistStat(name="周杰伦", count=10, percentage=15.5)
        assert stat.name == "周杰伦"
        assert stat.count == 10

    def test_to_dict(self):
        """测试转换为字典"""
        stat = ArtistStat(name="周杰伦", count=10, percentage=15.5)
        d = stat.to_dict()
        assert d["name"] == "周杰伦"
        assert d["count"] == 10


class TestScrapeResult:
    """测试爬取结果"""

    def test_create_success(self):
        """测试创建成功结果"""
        songs = [SongData(rank=1, title="晴天", artist="周杰伦")]
        result = ScrapeResult(
            success=True,
            method="API",
            data=songs,
            online=True,
        )
        assert result.success is True
        assert result.count == 1

    def test_create_failure(self):
        """测试创建失败结果"""
        result = ScrapeResult(
            success=False,
            method="API",
            error="网络错误",
        )
        assert result.success is False
        assert result.count == 0


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

    def test_total_songs(self, sample_songs):
        """测试歌曲总数"""
        analyzer = ArtistAnalyzer(sample_songs)
        assert analyzer.total_songs == 4

    def test_get_all_artists(self, sample_songs):
        """测试获取所有歌手"""
        analyzer = ArtistAnalyzer(sample_songs)
        artists = analyzer.get_all_artists()
        assert "周杰伦" in artists
        assert "陈奕迅" in artists

    def test_get_top_artists(self, sample_songs):
        """测试获取 TOP 歌手"""
        analyzer = ArtistAnalyzer(sample_songs)
        top10 = analyzer.get_top_artists(2)
        assert len(top10) == 2
        assert top10[0].name == "周杰伦"  # 2次 > 陈奕迅 2次

    def test_analyze(self, sample_songs):
        """测试完整分析"""
        analyzer = ArtistAnalyzer(sample_songs)
        result = analyzer.analyze()
        assert result.total_songs == 4
        assert result.total_artists == 2


class TestConfig:
    """测试配置类"""

    def test_default_config(self):
        """测试默认配置"""
        config = Config()
        assert config.target_url is not None
        assert len(config.user_agents) > 0

    def test_font_paths(self):
        """测试字体路径"""
        config = Config()
        paths = config.font_paths
        assert isinstance(paths, list)

    def test_chart_ids(self):
        """测试榜单 ID 配置"""
        config = Config()
        chart_ids = config.chart_ids
        assert isinstance(chart_ids, dict)
        assert "热歌榜" in chart_ids
        assert "飙升榜" in chart_ids
        assert "新歌榜" in chart_ids
        assert "原创榜" in chart_ids

    def test_chart_urls(self):
        """测试榜单 URL 配置"""
        config = Config()
        chart_urls = config.chart_urls
        assert isinstance(chart_urls, dict)
        assert len(chart_urls) > 0

    def test_auto_refresh_config(self):
        """测试定时任务配置"""
        config = Config()
        assert config.auto_refresh_interval > 0
        assert config.history_retention_days > 0


class TestMultiChartScraping:
    """测试多榜单爬取功能"""

    @pytest.fixture
    def scraper(self):
        """创建爬虫实例"""
        return MusicScraper()

    def test_scrape_chart_method_exists(self, scraper):
        """测试 scrape_chart 方法存在"""
        assert hasattr(scraper, 'scrape_chart')
        assert callable(scraper.scrape_chart)

    def test_scrape_all_charts_method_exists(self, scraper):
        """测试 scrape_all_charts 方法存在"""
        assert hasattr(scraper, 'scrape_all_charts')
        assert callable(scraper.scrape_all_charts)

    def test_fallback_data(self, scraper):
        """测试备用数据"""
        fallback = scraper.get_fallback_data()
        assert isinstance(fallback, list)
        assert len(fallback) > 0
        assert all(hasattr(song, 'rank') for song in fallback)
        assert all(hasattr(song, 'title') for song in fallback)
        assert all(hasattr(song, 'artist') for song in fallback)


# 运行标记
if __name__ == "__main__":
    pytest.main([__file__, "-v"])