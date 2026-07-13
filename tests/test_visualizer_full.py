# -*- coding: utf-8 -*-
"""
ChartGenerator 全部图表方法测试（覆盖 pie/line/heatmap/trend/excel/pdf）
"""

import os
import base64
import tempfile
import pytest

from music_analytics.models import SongData, ArtistStat
from music_analytics.visualizer import ChartGenerator


class TestPieChart:
    """饼图测试"""

    @pytest.fixture
    def top10(self):
        return [
            ArtistStat(name="周杰伦", count=15, percentage=30.0),
            ArtistStat(name="陈奕迅", count=12, percentage=24.0),
            ArtistStat(name="薛之谦", count=10, percentage=20.0),
            ArtistStat(name="林俊杰", count=8, percentage=16.0),
            ArtistStat(name="邓紫棋", count=5, percentage=10.0),
        ]

    def test_generate_pie_chart_success(self, top10):
        """生成饼图成功"""
        gen = ChartGenerator()
        result = gen.generate_pie_chart(top10)
        assert result is not None
        decoded = base64.b64decode(result)
        assert decoded.startswith(b"\x89PNG")

    def test_generate_pie_chart_empty(self):
        """空数据返回 None"""
        gen = ChartGenerator()
        result = gen.generate_pie_chart([])
        assert result is None


class TestLineChart:
    """折线图测试"""

    @pytest.fixture
    def songs(self):
        return [
            SongData(rank=i, title=f"歌曲{i}", artist="周杰伦")
            for i in range(1, 21)
        ]

    def test_generate_line_chart_success(self, songs):
        """生成折线图成功"""
        gen = ChartGenerator()
        result = gen.generate_line_chart(songs)
        assert result is not None
        decoded = base64.b64decode(result)
        assert decoded.startswith(b"\x89PNG")

    def test_generate_line_chart_empty(self):
        """空数据"""
        gen = ChartGenerator()
        result = gen.generate_line_chart([])
        assert result is None


class TestHeatmap:
    """热力图测试"""

    @pytest.fixture
    def top_artists(self):
        return [
            ArtistStat(name="周杰伦", count=10, percentage=20.0),
            ArtistStat(name="陈奕迅", count=8, percentage=16.0),
            ArtistStat(name="薛之谦", count=6, percentage=12.0),
            ArtistStat(name="林俊杰", count=5, percentage=10.0),
        ]

    @pytest.fixture
    def songs(self):
        return [
            SongData(rank=1, title="晴天", artist="周杰伦"),
            SongData(rank=2, title="七里香", artist="周杰伦"),
            SongData(rank=3, title="十年", artist="陈奕迅"),
            SongData(rank=5, title="演员", artist="薛之谦"),
            SongData(rank=12, title="江南", artist="林俊杰"),
        ]

    def test_generate_heatmap_success(self, top_artists, songs):
        """生成热力图成功"""
        gen = ChartGenerator()
        result = gen.generate_heatmap(top_artists, songs)
        assert result is not None
        decoded = base64.b64decode(result)
        assert decoded.startswith(b"\x89PNG")

    def test_generate_heatmap_empty_artists(self, songs):
        """空歌手列表"""
        gen = ChartGenerator()
        result = gen.generate_heatmap([], songs)
        assert result is None

    def test_generate_heatmap_empty_songs(self):
        """空歌曲列表"""
        gen = ChartGenerator()
        top = [ArtistStat(name="周杰伦", count=10, percentage=20.0)]
        result = gen.generate_heatmap(top, [])
        assert result is None


class TestTrendChart:
    """趋势图测试"""

    def test_generate_trend_chart_success(self):
        """正常生成趋势图"""
        gen = ChartGenerator()
        trend_data = [
            {"rank": 5, "timestamp": "2025-01-01T12:00:00"},
            {"rank": 3, "timestamp": "2025-01-02T12:00:00"},
            {"rank": 1, "timestamp": "2025-01-03T12:00:00"},
            {"rank": 2, "timestamp": "2025-01-04T12:00:00"},
        ]
        result = gen.generate_trend_chart(trend_data, song_title="晴天", artist="周杰伦")
        assert result is not None
        decoded = base64.b64decode(result)
        assert decoded.startswith(b"\x89PNG")

    def test_generate_trend_chart_insufficient_data(self):
        """只有1个数据点不够"""
        gen = ChartGenerator()
        trend_data = [{"rank": 1, "timestamp": "2025-01-01T12:00:00"}]
        result = gen.generate_trend_chart(trend_data)
        assert result is None

    def test_generate_trend_chart_empty(self):
        """空数据"""
        gen = ChartGenerator()
        result = gen.generate_trend_chart([])
        assert result is None

    def test_generate_trend_chart_bad_timestamps(self):
        """错误时间戳仍能生成（过滤掉坏的）"""
        gen = ChartGenerator()
        trend_data = [
            {"rank": 5, "timestamp": "2025-01-01T12:00:00"},
            {"rank": 3, "timestamp": "invalid"},
            {"rank": 1, "timestamp": "2025-01-03T12:00:00"},
        ]
        result = gen.generate_trend_chart(trend_data, song_title="测试", artist="测试")
        # 只有2个有效点，可以生成
        assert result is not None


class TestCSVMultiSection:
    """CSV 多 section 测试"""

    @pytest.fixture
    def songs(self):
        return [
            SongData(rank=1, title="晴天", artist="周杰伦"),
            SongData(rank=2, title="七里香", artist="周杰伦"),
            SongData(rank=3, title="十年", artist="陈奕迅"),
        ]

    def test_csv_with_wordcloud_section(self, songs):
        """带词云 section"""
        gen = ChartGenerator()
        artist_counter = {"周杰伦": 2, "陈奕迅": 1}
        result = gen.generate_csv(songs, artist_counter=artist_counter)
        assert result is not None
        assert "歌手词云榜" in result
        assert "周杰伦" in result
        assert "占比%" in result

    def test_csv_with_heatmap_section(self, songs):
        """带热力 section"""
        gen = ChartGenerator()
        heatmap_data = {
            "周杰伦": [2, 0, 0, 0, 0, 0, 0],
            "陈奕迅": [1, 0, 0, 0, 0, 0, 0],
        }
        heatmap_labels = ['1-10', '11-25', '26-50', '51-75', '76-100', '101-150', '151-200']
        result = gen.generate_csv(
            songs,
            heatmap_data=heatmap_data,
            heatmap_labels=heatmap_labels,
        )
        assert result is not None
        assert "歌手-排名热力榜" in result
        assert "合计" in result

    def test_csv_all_empty(self):
        """所有参数为空"""
        gen = ChartGenerator()
        result = gen.generate_csv([])
        assert result is None


class TestExcelFull:
    """Excel 全场景测试"""

    @pytest.fixture
    def songs(self):
        return [
            SongData(rank=1, title="晴天", artist="周杰伦"),
            SongData(rank=2, title="十年", artist="陈奕迅"),
        ]

    def test_excel_with_trend_data(self, songs):
        """带趋势数据的 Excel"""
        gen = ChartGenerator()
        artist_counter = {"周杰伦": 1, "陈奕迅": 1}
        rank_changes = [
            {"title": "晴天", "artist": "周杰伦", "old_rank": 2, "new_rank": 1, "rank_change": 1},
        ]
        trend_data = {
            "晴天-周杰伦": [
                {"rank": 2, "timestamp": "2025-01-01T12:00:00"},
                {"rank": 1, "timestamp": "2025-01-02T12:00:00"},
            ]
        }
        content = gen.generate_excel(
            songs=songs,
            artist_counter=artist_counter,
            chart_name="热歌榜",
            rank_changes=rank_changes,
            trend_data=trend_data,
        )
        assert content is not None
        assert len(content) > 0

    def test_excel_empty_rank_changes(self, songs):
        """空排名变化"""
        gen = ChartGenerator()
        content = gen.generate_excel(songs=songs, rank_changes=[], chart_name="热歌榜")
        assert content is not None

    def test_save_excel_with_full_data(self, songs):
        """保存完整 Excel"""
        gen = ChartGenerator()
        artist_counter = {"周杰伦": 1, "陈奕迅": 1}
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "full.xlsx")
            ok = gen.save_excel(
                songs=songs,
                save_path=path,
                artist_counter=artist_counter,
                chart_name="热歌榜",
            )
            assert ok is True
            assert os.path.exists(path)
            assert os.path.getsize(path) > 0


class TestPDFFull:
    """PDF 全场景测试"""

    @pytest.fixture
    def songs(self):
        return [
            SongData(rank=1, title="晴天", artist="周杰伦"),
            SongData(rank=2, title="十年", artist="陈奕迅"),
        ]

    @pytest.fixture
    def top10(self):
        return [
            ArtistStat(name="周杰伦", count=10, percentage=30.0),
            ArtistStat(name="陈奕迅", count=8, percentage=24.0),
        ]

    def test_pdf_with_all_params(self, songs, top10):
        """全部参数"""
        gen = ChartGenerator()
        artist_counter = {"周杰伦": 1, "陈奕迅": 1}
        content = gen.generate_pdf(
            songs=songs,
            artist_counter=artist_counter,
            top10=top10,
            chart_name="飙升榜",
        )
        assert content is not None
        assert len(content) > 0

    def test_pdf_empty_top10(self, songs):
        """空 TOP10"""
        gen = ChartGenerator()
        content = gen.generate_pdf(songs=songs, top10=[], chart_name="热歌榜")
        assert content is not None

    def test_save_pdf_with_full_data(self, songs, top10):
        """保存完整 PDF"""
        gen = ChartGenerator()
        artist_counter = {"周杰伦": 1}
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "full.pdf")
            ok = gen.save_pdf(
                songs=songs,
                save_path=path,
                artist_counter=artist_counter,
                top10=top10,
                chart_name="热歌榜",
            )
            assert ok is True
            assert os.path.exists(path)
            assert os.path.getsize(path) > 0
