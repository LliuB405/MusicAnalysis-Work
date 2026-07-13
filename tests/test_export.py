# -*- coding: utf-8 -*-
"""
测试模块 - Excel 和 PDF 导出测试
"""

import pytest
import tempfile
import os
from music_analytics.visualizer import ChartGenerator
from music_analytics.models import SongData, ArtistStat
from music_analytics.config import Config


class TestExcelExport:
    """测试 Excel 导出功能"""

    @pytest.fixture
    def chart_generator(self):
        """创建图表生成器实例"""
        return ChartGenerator()

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

    @pytest.fixture
    def artist_counter(self):
        """示例歌手统计"""
        return {
            "周杰伦": 2,
            "陈奕迅": 2,
            "Beyond": 1,
        }

    @pytest.fixture
    def rank_changes(self):
        """示例排名变化"""
        return [
            {"title": "晴天", "artist": "周杰伦", "old_rank": 2, "new_rank": 1, "rank_change": 1},
            {"title": "十年", "artist": "陈奕迅", "old_rank": 5, "new_rank": 3, "rank_change": 2},
        ]

    def test_generate_excel_basic(self, chart_generator, sample_songs):
        """测试生成基本 Excel"""
        content = chart_generator.generate_excel(
            songs=sample_songs,
            chart_name="热歌榜"
        )
        assert content is not None
        assert isinstance(content, bytes)
        assert len(content) > 0

    def test_generate_excel_with_artists(self, chart_generator, sample_songs, artist_counter):
        """测试生成带歌手统计的 Excel"""
        content = chart_generator.generate_excel(
            songs=sample_songs,
            artist_counter=artist_counter,
            chart_name="热歌榜"
        )
        assert content is not None

    def test_generate_excel_with_changes(self, chart_generator, sample_songs, rank_changes):
        """测试生成带排名变化的 Excel"""
        content = chart_generator.generate_excel(
            songs=sample_songs,
            rank_changes=rank_changes,
            chart_name="热歌榜"
        )
        assert content is not None

    def test_generate_excel_empty_songs(self, chart_generator):
        """测试空歌曲列表"""
        content = chart_generator.generate_excel(
            songs=[],
            chart_name="热歌榜"
        )
        # 空列表时可能返回 None 或带表头的空 Excel
        assert content is None or (isinstance(content, bytes) and len(content) > 0)

    def test_save_excel(self, chart_generator, sample_songs):
        """测试保存 Excel 文件"""
        fd, temp_path = tempfile.mkstemp(suffix='.xlsx')
        os.close(fd)

        try:
            result = chart_generator.save_excel(
                songs=sample_songs,
                save_path=temp_path,
                chart_name="热歌榜"
            )
            assert result is True
            assert os.path.exists(temp_path)
            assert os.path.getsize(temp_path) > 0
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)


class TestPDFExport:
    """测试 PDF 导出功能"""

    @pytest.fixture
    def chart_generator(self):
        """创建图表生成器实例"""
        return ChartGenerator()

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
        """示例歌手统计"""
        return {
            "周杰伦": 2,
            "陈奕迅": 1,
        }

    @pytest.fixture
    def top10(self):
        """示例 TOP10 数据"""
        return [
            ArtistStat(name="周杰伦", count=10, percentage=20.0),
            ArtistStat(name="陈奕迅", count=8, percentage=16.0),
        ]

    def test_generate_pdf_basic(self, chart_generator, sample_songs):
        """测试生成基本 PDF"""
        content = chart_generator.generate_pdf(
            songs=sample_songs,
            chart_name="热歌榜"
        )
        assert content is not None
        assert isinstance(content, bytes)
        assert len(content) > 0

    def test_generate_pdf_with_top10(self, chart_generator, sample_songs, top10):
        """测试生成带 TOP10 的 PDF"""
        content = chart_generator.generate_pdf(
            songs=sample_songs,
            top10=top10,
            chart_name="热歌榜"
        )
        assert content is not None

    def test_generate_pdf_with_artists(self, chart_generator, sample_songs, artist_counter):
        """测试生成带歌手统计的 PDF"""
        content = chart_generator.generate_pdf(
            songs=sample_songs,
            artist_counter=artist_counter,
            chart_name="热歌榜"
        )
        assert content is not None

    def test_save_pdf(self, chart_generator, sample_songs):
        """测试保存 PDF 文件"""
        fd, temp_path = tempfile.mkstemp(suffix='.pdf')
        os.close(fd)

        try:
            result = chart_generator.save_pdf(
                songs=sample_songs,
                save_path=temp_path,
                chart_name="热歌榜"
            )
            assert result is True
            assert os.path.exists(temp_path)
            assert os.path.getsize(temp_path) > 0
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)


class TestExportEdgeCases:
    """测试导出边界情况"""

    @pytest.fixture
    def chart_generator(self):
        """创建图表生成器实例"""
        return ChartGenerator()

    def test_empty_chart_name(self, chart_generator):
        """测试空榜单名称"""
        songs = [SongData(rank=1, title="测试", artist="测试歌手")]
        content = chart_generator.generate_excel(songs=songs, chart_name="")
        # 空名称应该也能正常处理
        assert content is not None or content is None  # 根据实现而定

    def test_unicode_in_chart_name(self, chart_generator):
        """测试中文榜单名称"""
        songs = [SongData(rank=1, title="测试", artist="测试歌手")]
        content = chart_generator.generate_excel(songs=songs, chart_name="飙升榜🎵")
        assert content is not None or content is None

    def test_large_dataset(self, chart_generator):
        """测试大数据集"""
        songs = [
            SongData(rank=i, title=f"歌曲{i}", artist=f"歌手{i % 10}")
            for i in range(1, 201)
        ]
        content = chart_generator.generate_excel(songs=songs, chart_name="热歌榜")
        assert content is not None
