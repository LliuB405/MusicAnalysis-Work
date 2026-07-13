# -*- coding: utf-8 -*-
"""
MusicScraper 播放链接相关方法的单元测试
"""

import pytest
from unittest.mock import MagicMock, patch

from music_analytics.scraper import MusicScraper
from music_analytics.config import Config


def _mock_response(json_data, status=200):
    """构造一个 requests.Response 的 mock"""
    resp = MagicMock()
    resp.status_code = status
    resp.json.return_value = json_data
    return resp


class TestSearchSongId:
    """search_song_id 测试"""

    def test_search_song_id_success(self):
        """正常返回 song id"""
        scraper = MusicScraper(Config())
        fake = _mock_response({
            "result": {
                "songs": [{"id": 123456, "name": "测试歌曲"}]
            }
        })
        with patch.object(scraper, "_build_session") as mock_session:
            sess = MagicMock()
            sess.post.return_value = fake
            mock_session.return_value = sess
            sid = scraper.search_song_id("测试", "歌手")
        assert sid == 123456

    def test_search_song_id_no_result(self):
        """没有搜索结果"""
        scraper = MusicScraper(Config())
        fake = _mock_response({"result": {"songs": []}})
        with patch.object(scraper, "_build_session") as mock_session:
            sess = MagicMock()
            sess.post.return_value = fake
            mock_session.return_value = sess
            sid = scraper.search_song_id("不存在", "未知")
        assert sid is None

    def test_search_song_id_request_failure(self):
        """网络错误"""
        import requests as real_requests
        scraper = MusicScraper(Config())
        with patch.object(scraper, "_build_session") as mock_session:
            sess = MagicMock()
            sess.post.side_effect = real_requests.ConnectionError("boom")
            mock_session.return_value = sess
            sid = scraper.search_song_id("x", "y")
        assert sid is None

    def test_search_song_id_json_decode_error(self):
        """JSON 解析失败"""
        scraper = MusicScraper(Config())
        fake = MagicMock()
        fake.status_code = 200
        fake.json.side_effect = ValueError("not json")
        with patch.object(scraper, "_build_session") as mock_session:
            sess = MagicMock()
            sess.post.return_value = fake
            mock_session.return_value = sess
            sid = scraper.search_song_id("x", "y")
        assert sid is None


class TestGetSongUrl:
    """get_song_url 测试"""

    def test_get_song_url_success(self):
        """正常返回 mp3 url"""
        scraper = MusicScraper(Config())
        fake = _mock_response({
            "data": [{"id": 1, "url": "http://example.com/song.mp3", "code": 200}]
        })
        with patch.object(scraper, "_build_session") as mock_session:
            sess = MagicMock()
            sess.post.return_value = fake
            mock_session.return_value = sess
            url = scraper.get_song_url(1)
        assert url == "http://example.com/song.mp3"
        # 验证 ids 用了 JSON 字符串
        call_args = sess.post.call_args
        assert call_args[1]["data"]["ids"] == "[1]"

    def test_get_song_url_no_copyright(self):
        """code=404（无版权）"""
        scraper = MusicScraper(Config())
        fake = _mock_response({
            "data": [{"id": 1, "url": None, "code": 404}]
        })
        with patch.object(scraper, "_build_session") as mock_session:
            sess = MagicMock()
            sess.post.return_value = fake
            mock_session.return_value = sess
            url = scraper.get_song_url(1)
        assert url is None

    def test_get_song_url_empty_data(self):
        """data 为空"""
        scraper = MusicScraper(Config())
        fake = _mock_response({"data": []})
        with patch.object(scraper, "_build_session") as mock_session:
            sess = MagicMock()
            sess.post.return_value = fake
            mock_session.return_value = sess
            url = scraper.get_song_url(1)
        assert url is None

    def test_get_song_url_http_error(self):
        """HTTP 状态码非 200"""
        scraper = MusicScraper(Config())
        fake = _mock_response({}, status=500)
        with patch.object(scraper, "_build_session") as mock_session:
            sess = MagicMock()
            sess.post.return_value = fake
            mock_session.return_value = sess
            url = scraper.get_song_url(1)
        assert url is None


class TestResolvePlayUrl:
    """resolve_play_url 一键方法"""

    def test_resolve_success(self):
        """search + get_url 都成功"""
        scraper = MusicScraper(Config())
        with patch.object(scraper, "search_song_id", return_value=42):
            with patch.object(scraper, "get_song_url", return_value="http://x/y.mp3"):
                info = scraper.resolve_play_url("标题", "歌手")
        assert info == {"song_id": 42, "mp3_url": "http://x/y.mp3"}

    def test_resolve_no_search_result(self):
        """搜索失败"""
        scraper = MusicScraper(Config())
        with patch.object(scraper, "search_song_id", return_value=None):
            info = scraper.resolve_play_url("x", "y")
        assert info is None

    def test_resolve_no_url(self):
        """搜索成功但无 url"""
        scraper = MusicScraper(Config())
        with patch.object(scraper, "search_song_id", return_value=42):
            with patch.object(scraper, "get_song_url", return_value=None):
                info = scraper.resolve_play_url("x", "y")
        assert info is None
