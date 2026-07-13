# -*- coding: utf-8 -*-
"""
ChartGenerator 单元测试
"""

import os
import base64
import tempfile
import pytest

from music_analytics.models import SongData, ArtistStat
from music_analytics.visualizer import ChartGenerator


class TestChartGenerator:
    """测试图表生成器"""

    @pytest.fixture
    def top10(self):
        """示例 TOP10 数据"""
        return [
            ArtistStat(name="周杰伦", count=15, percentage=15.0),
            ArtistStat(name="陈奕迅", count=12, percentage=12.0),
            ArtistStat(name="薛之谦", count=10, percentage=10.0),
            ArtistStat(name="林俊杰", count=8, percentage=8.0),
            ArtistStat(name="邓紫棋", count=7, percentage=7.0),
            ArtistStat(name="毛不易", count=6, percentage=6.0),
            ArtistStat(name="李荣浩", count=5, percentage=5.0),
            ArtistStat(name="周深", count=4, percentage=4.0),
            ArtistStat(name="华晨宇", count=3, percentage=3.0),
            ArtistStat(name="许嵩", count=2, percentage=2.0),
        ]

    @pytest.fixture
    def sample_songs(self):
        """示例歌曲数据"""
        return [
            SongData(rank=1, title="晴天", artist="周杰伦"),
            SongData(rank=2, title="七里香", artist="周杰伦"),
            SongData(rank=3, title="十年", artist="陈奕迅"),
        ]

    @pytest.fixture
    def artist_counter(self):
        """歌手频次字典"""
        return {
            "周杰伦": 15,
            "陈奕迅": 12,
            "薛之谦": 10,
            "林俊杰": 8,
        }

    def test_generate_bar_chart_success(self, top10):
        """测试柱状图生成成功"""
        gen = ChartGenerator()
        result = gen.generate_bar_chart(top10)
        assert result is not None
        # 验证是 base64 字符串
        try:
            decoded = base64.b64decode(result)
            # PNG 文件头: \x89PNG
            assert decoded.startswith(b"\x89PNG")
        except Exception:
            pytest.fail("生成的图像不是有效的 base64 PNG")

    def test_generate_bar_chart_empty(self):
        """测试空数据"""
        gen = ChartGenerator()
        result = gen.generate_bar_chart([])
        assert result is None

    def test_generate_wordcloud_success(self, artist_counter):
        """测试词云图生成成功"""
        gen = ChartGenerator()
        result = gen.generate_wordcloud(artist_counter)
        assert result is not None
        decoded = base64.b64decode(result)
        assert decoded.startswith(b"\x89PNG")

    def test_generate_wordcloud_empty(self):
        """测试空数据"""
        gen = ChartGenerator()
        result = gen.generate_wordcloud({})
        assert result is None

    def test_generate_csv_success(self, sample_songs):
        """测试 CSV 生成"""
        gen = ChartGenerator()
        result = gen.generate_csv(sample_songs)
        assert result is not None
        # 检查 BOM 头
        assert result.startswith("\ufeff")
        # 检查表头
        assert "排名" in result
        assert "歌曲名称" in result
        assert "歌手名称" in result
        # 检查数据
        assert "晴天" in result
        assert "周杰伦" in result

    def test_generate_csv_custom_headers(self, sample_songs):
        """测试自定义表头"""
        gen = ChartGenerator()
        result = gen.generate_csv(sample_songs, headers=["#", "Title", "Artist"])
        assert "#" in result
        assert "Title" in result
        assert "Artist" in result

    def test_generate_csv_empty(self):
        """测试空数据"""
        gen = ChartGenerator()
        result = gen.generate_csv([])
        assert result is None

    def test_save_bar_chart(self, top10):
        """测试保存柱状图到文件"""
        gen = ChartGenerator()
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "test_bar.png")
            ok = gen.save_bar_chart(top10, path)
            assert ok is True
            assert os.path.exists(path)
            # 文件大小 > 0
            assert os.path.getsize(path) > 0

    def test_save_bar_chart_empty(self):
        """空数据时保存失败"""
        gen = ChartGenerator()
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "test_empty.png")
            ok = gen.save_bar_chart([], path)
            assert ok is False
            assert not os.path.exists(path)

    def test_save_wordcloud(self, artist_counter):
        """测试保存词云图到文件"""
        gen = ChartGenerator()
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "test_wc.png")
            ok = gen.save_wordcloud(artist_counter, path)
            assert ok is True
            assert os.path.exists(path)
            assert os.path.getsize(path) > 0

    def test_find_chinese_font_cached(self):
        """测试字体路径缓存"""
        gen = ChartGenerator()
        path1 = gen._find_chinese_font()
        path2 = gen._find_chinese_font()
        # 第二次调用应该走缓存
        assert path1 == path2
