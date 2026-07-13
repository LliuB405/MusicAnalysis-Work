# -*- coding: utf-8 -*-
"""
MusicScraper 补充测试 — 覆盖 mock 场景
"""

import pytest
from unittest.mock import MagicMock, patch
import json as _json

from music_analytics.scraper import MusicScraper, ScraperError, NetworkError, ParseError
from music_analytics.models import SongData
from music_analytics.config import Config


class TestBuildSession:
    """_build_session 测试"""

    def test_build_session_basic(self):
        """基本 session 构建"""
        scraper = MusicScraper(Config())
        session = scraper._build_session()
        assert session is not None
        assert "User-Agent" in session.headers

    def test_build_session_with_vip_cookie(self):
        """VIP cookie 注入"""
        config = Config()
        config.vip_music_u = "test_music_u_value"
        config.vip_csrf = "test_csrf_value"
        scraper = MusicScraper(config)
        session = scraper._build_session()
        # 验证 cookie 已设置
        music_u = session.cookies.get("MUSIC_U", domain=".music.163.com")
        assert music_u == "test_music_u_value"


class TestCustomExceptions:
    """异常类测试"""

    def test_scraper_error(self):
        """ScraperError 基本用法"""
        err = ScraperError("测试错误")
        assert str(err) == "测试错误"
        assert isinstance(err, Exception)

    def test_network_error(self):
        """NetworkError"""
        err = NetworkError("网络异常")
        assert str(err) == "网络异常"
        assert isinstance(err, ScraperError)

    def test_parse_error(self):
        """ParseError"""
        err = ParseError("解析失败")
        assert str(err) == "解析失败"
        assert isinstance(err, ScraperError)


class TestExtractSongsFromJson:
    """递归 JSON 提取测试"""

    def test_extract_list_of_songs(self):
        """直接从列表提取"""
        scraper = MusicScraper(Config())
        data = [
            {"name": "歌曲A", "ar": [{"name": "歌手A"}]},
            {"name": "歌曲B", "ar": [{"name": "歌手B"}]},
            {"name": "歌曲C", "ar": [{"name": "歌手C"}]},
        ]
        result = scraper._extract_songs_from_json(data)
        assert result is not None
        assert len(result) == 3
        assert result[0].title == "歌曲A"
        assert result[0].artist == "歌手A"

    def test_extract_nested(self):
        """嵌套 JSON 提取"""
        scraper = MusicScraper(Config())
        data = {
            "playlist": {
                "tracks": [
                    {"name": "歌曲X", "ar": [{"name": "歌手X"}]},
                    {"name": "歌曲Y", "ar": [{"name": "歌手Y"}]},
                ]
            }
        }
        result = scraper._extract_songs_from_json(data)
        assert result is not None
        assert len(result) == 2
        assert result[0].title == "歌曲X"

    def test_extract_empty(self):
        """空数据"""
        scraper = MusicScraper(Config())
        result = scraper._extract_songs_from_json({})
        assert result is None

    def test_extract_non_song_list(self):
        """非歌曲列表"""
        scraper = MusicScraper(Config())
        data = [{"id": 1}, {"id": 2}, {"id": 3}]  # 没有 name 字段
        result = scraper._extract_songs_from_json(data)
        assert result is None


class TestRandomDelay:
    """_random_delay 测试"""

    def test_random_delay_runs(self):
        """验证延时方法可以正常执行"""
        import time
        scraper = MusicScraper(Config())
        scraper.config.min_delay = 0.01
        scraper.config.max_delay = 0.05
        start = time.time()
        scraper._random_delay()
        elapsed = time.time() - start
        assert elapsed >= 0.01


class TestFetchWithRetry:
    """_fetch_with_retry 测试"""

    def test_fetch_success_first_try(self):
        """第一次就成功"""
        scraper = MusicScraper(Config())
        fake_resp = MagicMock()
        fake_resp.status_code = 200
        with patch.object(scraper, "_build_session") as mock_session:
            sess = MagicMock()
            sess.get.return_value = fake_resp
            mock_session.return_value = sess
            result = scraper._fetch_with_retry("http://test.local/")
        assert result is not None
        assert result.status_code == 200

    def test_fetch_with_retries(self):
        """前两次失败，第三次成功"""
        scraper = MusicScraper(Config())
        scraper.config.min_delay = 0.001
        scraper.config.max_delay = 0.01
        fail_resp = MagicMock()
        fail_resp.status_code = 500
        success_resp = MagicMock()
        success_resp.status_code = 200
        with patch.object(scraper, "_build_session") as mock_session:
            sess = MagicMock()
            sess.get.side_effect = [fail_resp, fail_resp, success_resp]
            mock_session.return_value = sess
            result = scraper._fetch_with_retry("http://test.local/", max_retries=3)
        assert result.status_code == 200

    def test_fetch_all_retries_exhausted(self):
        """所有重试都失败，返回 None"""
        import requests as real_requests
        scraper = MusicScraper(Config())
        scraper.config.min_delay = 0.001
        scraper.config.max_delay = 0.005
        with patch.object(scraper, "_build_session") as mock_session:
            sess = MagicMock()
            sess.get.side_effect = real_requests.ConnectionError("无网络")
            mock_session.return_value = sess
            result = scraper._fetch_with_retry("http://test.local/", max_retries=2)
        assert result is None


class TestParseTracks:
    """_parse_tracks 测试"""

    def test_parse_tracks_basic(self):
        """标准 tracks 解析"""
        scraper = MusicScraper(Config())
        tracks = [
            {"name": "晴天", "ar": [{"name": "周杰伦", "id": 6452}]},
            {"name": "十年", "ar": [{"name": "陈奕迅", "id": 2116}]},
        ]
        songs = scraper._parse_tracks(tracks)
        assert len(songs) == 2
        assert songs[0].title == "晴天"
        assert songs[0].artist == "周杰伦"
        assert songs[0].rank == 1

    def test_parse_tracks_unknown_artist(self):
        """未知歌手"""
        scraper = MusicScraper(Config())
        tracks = [{"name": "无歌手歌曲", "ar": []}]
        songs = scraper._parse_tracks(tracks)
        assert songs[0].artist == "未知歌手"

    def test_parse_tracks_multiple_artists(self):
        """合唱歌曲"""
        scraper = MusicScraper(Config())
        tracks = [{
            "name": "因为爱情",
            "ar": [{"name": "陈奕迅"}, {"name": "王菲"}]
        }]
        songs = scraper._parse_tracks(tracks)
        assert songs[0].artist == "陈奕迅 / 王菲"


class TestScrapeChartMock:
    """scrape_chart mock 测试"""

    def test_scrape_chart_api_success(self):
        """API 方式成功"""
        scraper = MusicScraper(Config())
        fake_api_resp = MagicMock()
        fake_api_resp.status_code = 200
        fake_api_resp.json.return_value = {
            "code": 200,
            "result": {
                "tracks": [
                    {"name": "测试歌", "ar": [{"name": "测试歌手"}]},
                ]
            }
        }
        with patch.object(scraper, "_build_session") as mock_session:
            sess = MagicMock()
            sess.get.return_value = MagicMock(status_code=200)  # 首页
            sess.post.return_value = fake_api_resp
            mock_session.return_value = sess
            songs = scraper.scrape_chart("3778678")
        assert songs is not None
        assert len(songs) == 1
        assert songs[0].title == "测试歌"

    def test_scrape_chart_api_code_not_200(self):
        """API 返回 code != 200，回退到 HTML"""
        scraper = MusicScraper(Config())
        fake_resp = MagicMock()
        fake_resp.status_code = 200
        fake_resp.json.return_value = {"code": 301}
        fake_html = MagicMock()
        fake_html.status_code = 200
        # 没有 textarea，返回 None
        fake_html.text = "<html></html>"
        with patch.object(scraper, "_build_session") as mock_session:
            sess = MagicMock()
            sess.get.return_value = fake_html
            sess.post.return_value = fake_resp
            mock_session.return_value = sess
            songs = scraper.scrape_chart("999999")
        assert songs is None or isinstance(songs, list)


class TestScrapeAllChartsMock:
    """scrape_all_charts mock 测试"""

    def test_scrape_all_charts(self):
        """全榜单爬取"""
        scraper = MusicScraper(Config())
        mock_songs = [
            SongData(rank=1, title="测试歌", artist="测试歌手"),
        ]
        with patch.object(scraper, "scrape_chart", return_value=mock_songs):
            results = scraper.scrape_all_charts()
        assert isinstance(results, dict)
        assert len(results) > 0
        # 所有榜单都应该有数据
        for name in scraper.config.chart_ids:
            assert name in results
            assert len(results[name]) == 1

    def test_scrape_all_charts_fallback(self):
        """部分榜单失败，使用备用数据"""
        scraper = MusicScraper(Config())
        def side_effect(chart_id):
            if chart_id == "3778678":
                return [SongData(rank=1, title="晴天", artist="周杰伦")]
            return None  # 其他榜单失败
        with patch.object(scraper, "scrape_chart", side_effect=side_effect):
            results = scraper.scrape_all_charts()
        assert "热歌榜" in results
        # 失败的榜单应使用备用数据
        for name, data in results.items():
            assert len(data) > 0


class TestResolvePlayUrlStreamable:
    """resolve_play_url_streamable mock 测试"""

    def test_resolve_streamable_success(self):
        """search + get_url 都成功，同一 session"""
        scraper = MusicScraper(Config())
        search_resp = MagicMock()
        search_resp.status_code = 200
        search_resp.json.return_value = {
            "result": {"songs": [{"id": 123456, "name": "晴天"}]}
        }
        url_resp = MagicMock()
        url_resp.status_code = 200
        url_resp.json.return_value = {
            "data": [{"id": 123456, "url": "http://music.163.com/stream.mp3"}]
        }
        with patch.object(scraper, "_build_session") as mock_session:
            sess = MagicMock()
            sess.post.side_effect = [search_resp, url_resp]
            mock_session.return_value = sess
            info = scraper.resolve_play_url_streamable("晴天", "周杰伦")
        assert info is not None
        assert info["song_id"] == 123456
        assert info["mp3_url"] == "http://music.163.com/stream.mp3"
        assert "_session" in info

    def test_resolve_streamable_search_fail(self):
        """搜索无结果"""
        scraper = MusicScraper(Config())
        search_resp = MagicMock()
        search_resp.status_code = 200
        search_resp.json.return_value = {"result": {"songs": []}}
        with patch.object(scraper, "_build_session") as mock_session:
            sess = MagicMock()
            sess.post.return_value = search_resp
            mock_session.return_value = sess
            info = scraper.resolve_play_url_streamable("不存在", "无此人")
        assert info is None

    def test_resolve_streamable_no_url(self):
        """歌曲搜索成功但无播放链接"""
        scraper = MusicScraper(Config())
        search_resp = MagicMock()
        search_resp.status_code = 200
        search_resp.json.return_value = {
            "result": {"songs": [{"id": 123456, "name": "VIP歌"}]}
        }
        url_resp = MagicMock()
        url_resp.status_code = 200
        url_resp.json.return_value = {"data": [{"id": 123456, "url": None}]}
        with patch.object(scraper, "_build_session") as mock_session:
            sess = MagicMock()
            sess.post.side_effect = [search_resp, url_resp]
            mock_session.return_value = sess
            info = scraper.resolve_play_url_streamable("VIP歌", "VIP歌手")
        assert info is None

    def test_detailed_uses_chart_id_and_falls_back_bitrate(self):
        """榜单 song_id 直接解析，320k 不可用时降级到 192k。"""
        scraper = MusicScraper(Config())
        no_url = MagicMock()
        no_url.status_code = 200
        no_url.json.return_value = {"data": [{"id": 456, "url": None, "code": 200}]}
        lower_url = MagicMock()
        lower_url.status_code = 200
        lower_url.json.return_value = {
            "data": [{"id": 456, "url": "https://m10.music.126.net/test.mp3", "br": 192000}]
        }
        with patch.object(scraper, "_build_session") as mock_session:
            session = MagicMock()
            session.post.side_effect = [no_url, lower_url]
            mock_session.return_value = session
            info = scraper.resolve_play_url_detailed("测试歌", "测试歌手", song_id=456, fee=8)

        assert info["success"] is True
        assert info["song_id"] == 456
        assert info["bitrate"] == 192000
        assert session.post.call_count == 2

    def test_detailed_reports_vip_restriction(self):
        """VIP 歌曲没有官方 URL 时返回明确原因。"""
        scraper = MusicScraper(Config())
        no_url = MagicMock()
        no_url.status_code = 200
        no_url.json.return_value = {"data": [{"id": 789, "url": None, "code": -110}]}
        with patch.object(scraper, "_build_session") as mock_session:
            session = MagicMock()
            session.post.return_value = no_url
            mock_session.return_value = session
            info = scraper.resolve_play_url_detailed("VIP歌", "VIP歌手", song_id=789, fee=1)

        assert info["success"] is False
        assert info["reason"] == "vip_required"
        assert info["song_id"] == 789

    def test_batch_playability_mixes_playable_and_vip(self):
        """批量预检应同时返回可播放与 VIP 限制状态。"""
        scraper = MusicScraper(Config())
        response = MagicMock()
        response.status_code = 200
        response.json.return_value = {
            "data": [
                {"id": 1, "url": "https://m10.music.126.net/ok.mp3", "code": 200},
                {"id": 2, "url": None, "code": -110},
            ]
        }
        with patch.object(scraper, "_build_session") as mock_session:
            session = MagicMock()
            session.post.return_value = response
            mock_session.return_value = session
            results = scraper.check_song_playability([
                {"song_id": 1, "fee": 8},
                {"song_id": 2, "fee": 1},
            ])

        by_id = {item["song_id"]: item for item in results}
        assert by_id[1]["playable"] is True
        assert by_id[1]["is_trial"] is False
        assert by_id[2]["playable"] is False
        assert by_id[2]["reason"] == "vip_required"


class TestScrapeViaHtmlMock:
    """scrape_via_html mock 测试"""

    def test_scrape_html_textarea_found(self):
        """HTML 中找到 textarea"""
        import json as _json
        scraper = MusicScraper(Config())
        fake_html = f"""
        <html>
        <textarea id="song-list-pre-data">
        {_json.dumps([{"name": "歌曲AAA", "ar": [{"name": "歌手BBB"}]}, {"name": "歌曲CCC", "ar": [{"name": "歌手DDD"}]}])}
        </textarea>
        </html>
        """
        fake_resp = MagicMock()
        fake_resp.status_code = 200
        fake_resp.text = fake_html
        with patch.object(scraper, "_build_session") as mock_session:
            sess = MagicMock()
            sess.get.return_value = fake_resp
            mock_session.return_value = sess
            songs = scraper.scrape_via_html()
        assert songs is not None
        assert len(songs) == 2

    def test_scrape_html_empty(self):
        """HTML 无有效数据"""
        scraper = MusicScraper(Config())
        fake_resp = MagicMock()
        fake_resp.status_code = 200
        fake_resp.text = "<html><body>No data</body></html>"
        with patch.object(scraper, "_build_session") as mock_session:
            sess = MagicMock()
            sess.get.return_value = fake_resp
            mock_session.return_value = sess
            songs = scraper.scrape_via_html()
        assert songs is None

    def test_scrape_html_bad_status(self):
        """HTML 返回非 200"""
        scraper = MusicScraper(Config())
        fake_resp = MagicMock()
        fake_resp.status_code = 404
        with patch.object(scraper, "_build_session") as mock_session:
            sess = MagicMock()
            sess.get.return_value = fake_resp
            mock_session.return_value = sess
            songs = scraper.scrape_via_html()
        assert songs is None


class TestScrapeViaApiMock:
    """scrape_via_api mock 测试"""

    def test_scrape_api_success(self):
        """API 成功"""
        scraper = MusicScraper(Config())
        fake_resp = MagicMock()
        fake_resp.status_code = 200
        fake_resp.json.return_value = {
            "code": 200,
            "result": {
                "tracks": [
                    {"name": "API歌", "ar": [{"name": "API歌手"}]},
                ]
            }
        }
        with patch.object(scraper, "_build_session") as mock_session:
            sess = MagicMock()
            sess.get.return_value = MagicMock(status_code=200)
            sess.post.return_value = fake_resp
            mock_session.return_value = sess
            songs = scraper.scrape_via_api()
        assert songs is not None
        assert songs[0].title == "API歌"

    def test_scrape_api_code_301(self):
        """API code=301 返回 None"""
        scraper = MusicScraper(Config())
        fake_resp = MagicMock()
        fake_resp.status_code = 200
        fake_resp.json.return_value = {"code": 301}
        with patch.object(scraper, "_build_session") as mock_session:
            sess = MagicMock()
            sess.get.return_value = MagicMock(status_code=200)
            sess.post.return_value = fake_resp
            mock_session.return_value = sess
            songs = scraper.scrape_via_api()
        assert songs is None

    def test_scrape_api_json_error(self):
        """JSON 解析失败"""
        scraper = MusicScraper(Config())
        fake_resp = MagicMock()
        fake_resp.status_code = 200
        fake_resp.json.side_effect = ValueError("bad json")
        with patch.object(scraper, "_build_session") as mock_session:
            sess = MagicMock()
            sess.get.return_value = MagicMock(status_code=200)
            sess.post.return_value = fake_resp
            mock_session.return_value = sess
            songs = scraper.scrape_via_api()
        assert songs is None


class TestScrapeMain:
    """scrape() 主方法测试"""

    def test_scrape_via_api_success(self):
        """策略一成功"""
        scraper = MusicScraper(Config())
        fake_songs = [SongData(rank=1, title="晴天", artist="周杰伦")]
        with patch.object(scraper, "scrape_via_api", return_value=fake_songs):
            result = scraper.scrape()
        assert result.success is True
        assert result.method == "API实时接口"
        assert result.data == fake_songs
        assert result.online is True

    def test_scrape_fallback(self):
        """策略一和策略二都失败，使用备用数据"""
        scraper = MusicScraper(Config())
        with patch.object(scraper, "scrape_via_api", return_value=None):
            with patch.object(scraper, "scrape_via_html", return_value=None):
                result = scraper.scrape()
        assert result.success is True
        assert "备用" in result.method
        assert result.online is False
        assert len(result.data) > 0

    def test_scrape_via_html_success(self):
        """策略二成功"""
        scraper = MusicScraper(Config())
        fake_songs = [SongData(rank=1, title="七里香", artist="周杰伦")]
        with patch.object(scraper, "scrape_via_api", return_value=None):
            with patch.object(scraper, "scrape_via_html", return_value=fake_songs):
                result = scraper.scrape()
        assert result.success is True
        assert result.method == "HTML页面解析"
