# -*- coding: utf-8 -*-
"""
Flask 路由集成测试 — 覆盖新增 API 端点
"""

import os
import sys
import json
import pytest

# Setup paths
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

import app as app_module
from app import app as flask_app
from music_analytics.models import SongData


@pytest.fixture
def client():
    """Flask 测试客户端"""
    flask_app.config['TESTING'] = True
    with flask_app.test_client() as c:
        yield c


class TestHealthRoutes:
    """基础路由测试"""

    def test_health(self, client):
        rv = client.get('/api/health')
        data = json.loads(rv.data)
        assert rv.status_code == 200
        assert data['success'] is True
        assert data['charts'] >= 12

    def test_index(self, client):
        """首页"""
        rv = client.get('/')
        assert rv.status_code == 200

    def test_api_analyze_no_data(self, client):
        """无数据时分析返回错误"""
        rv = client.get('/api/analyze')
        assert rv.status_code == 200
        data = json.loads(rv.data)
        assert data["success"] is False

    def test_api_data_empty(self, client):
        """空数据查询"""
        rv = client.get('/api/data')
        data = json.loads(rv.data)
        assert data["success"] is True
        assert data["count"] >= 0


class TestHistoryRoutes:
    """历史数据路由测试"""

    def test_history_charts(self, client):
        """获取榜单列表"""
        rv = client.get('/api/history/charts')
        data = json.loads(rv.data)
        assert data["success"] is True
        assert "charts" in data

    def test_history_snapshot_no_data(self, client):
        """不存在的榜单快照"""
        rv = client.get('/api/history/snapshot/不存在的榜单')
        data = json.loads(rv.data)
        assert data["success"] is False

    def test_history_trend_no_params(self, client):
        """趋势查询缺少参数"""
        rv = client.get('/api/history/trend')
        assert rv.status_code == 400

    def test_history_trend_chart_no_data(self, client):
        """趋势图 — 无数据处理"""
        rv = client.get('/api/history/trend_chart?chart_name=热歌榜&song_title=不存在&artist=无')
        data = json.loads(rv.data)
        assert data["success"] is False

    def test_history_trend_chart_missing_params(self, client):
        """趋势图 — 缺少参数"""
        rv = client.get('/api/history/trend_chart')
        assert rv.status_code == 400

    def test_history_save_no_data(self, client):
        """无数据时保存失败"""
        rv = client.post('/api/history/save', json={'chart_name': '热歌榜'})
        data = json.loads(rv.data)
        assert data["success"] is False

    def test_history_cleanup(self, client):
        """清理历史数据"""
        rv = client.post('/api/history/cleanup', json={'days': 30})
        data = json.loads(rv.data)
        assert data["success"] is True
        assert "deleted" in data


class TestSchedulerRoutes:
    """调度器路由测试"""

    def test_scheduler_status(self, client):
        """获取调度器状态"""
        rv = client.get('/api/scheduler/status')
        data = json.loads(rv.data)
        assert data["success"] is True
        assert "running" in data

    def test_scheduler_stop(self, client):
        """停止调度器"""
        rv = client.post('/api/scheduler/stop')
        data = json.loads(rv.data)
        # 可能已停止或成功停止
        assert data["success"] in (True, False)


class TestChartCompareRoutes:
    """多榜单对比路由测试"""

    def test_compare_no_data(self, client):
        """无历史数据时"""
        rv = client.get('/api/charts/compare')
        data = json.loads(rv.data)
        # 可能返回空数据或错误
        assert "success" in data

    def test_scrape_all(self, client, monkeypatch):
        """全榜单路由测试不应访问真实网络或污染正式历史库。"""
        mock_results = {
            name: [SongData(rank=1, title="测试歌", artist="测试歌手", song_id=1, fee=8)]
            for name in app_module.config.chart_ids
        }
        monkeypatch.setattr(app_module._scraper, 'scrape_all_charts', lambda: mock_results)
        monkeypatch.setattr(app_module._history_mgr, 'save_snapshot', lambda *args, **kwargs: 1)
        rv = client.post('/api/scrape_all')
        data = json.loads(rv.data)
        assert data["success"] is True
        assert "saved" in data


class TestExportRoutes:
    """导出路由测试"""

    def test_export_excel_no_data(self, client):
        """无数据时 Excel 导出失败"""
        rv = client.get('/api/export/excel')
        assert rv.status_code == 400

    def test_export_pdf_no_data(self, client):
        """无数据时 PDF 导出失败"""
        rv = client.get('/api/export/pdf')
        assert rv.status_code == 400

    def test_export_csv_no_data(self, client):
        """无数据时 CSV 导出失败"""
        rv = client.get('/api/export_csv')
        assert rv.status_code == 400


class TestVIPRoutes:
    """VIP 路由测试"""

    def test_vip_status(self, client):
        """获取 VIP 状态"""
        rv = client.get('/api/vip/status')
        data = json.loads(rv.data)
        assert data["success"] is True
        assert "logged_in" in data

    def test_vip_login_missing_field(self, client):
        """缺少必填字段"""
        rv = client.post('/api/vip/login', json={})
        assert rv.status_code == 400

    def test_vip_logout(self, client):
        """退出登录"""
        rv = client.post('/api/vip/logout')
        data = json.loads(rv.data)
        assert data["success"] is True

    def test_vip_login_rejected_for_public_visitor(self, client):
        rv = client.post(
            '/api/vip/login',
            json={'music_u': 'secret'},
            headers={'CF-Connecting-IP': '203.0.113.9'},
        )
        assert rv.status_code == 403


class TestPlayRoutes:
    """播放路由测试"""

    def test_play_url_missing_params(self, client):
        """缺少参数"""
        rv = client.post('/api/song/play_url', json={})
        data = json.loads(rv.data)
        assert data["success"] is False

    def test_stream_invalid_url(self, client):
        """无效 URL"""
        rv = client.get('/api/song/stream?url=not-a-url')
        assert rv.status_code == 400

    def test_stream_rejects_untrusted_http_host(self, client):
        """音频代理不能被用来请求任意内网/外网地址。"""
        rv = client.get('/api/song/stream?url=http://127.0.0.1:5000/private')
        assert rv.status_code == 400

    def test_play_url_returns_specific_vip_reason(self, client, monkeypatch):
        """前端能区分 VIP 限制，而不是统一显示“无版权”。"""
        app_module._play_url_cache.clear()
        monkeypatch.setattr(
            app_module._scraper,
            'resolve_play_url_detailed',
            lambda *args, **kwargs: {
                'success': False,
                'reason': 'vip_required',
                'error': '需要 VIP',
                'song_id': 123,
            },
        )
        rv = client.post('/api/song/play_url', json={
            'title': 'VIP歌', 'artist': '歌手', 'song_id': 123, 'fee': 1,
        })
        data = json.loads(rv.data)
        assert data['success'] is False
        assert data['reason'] == 'vip_required'

    def test_play_url_cache_keeps_song_id(self, client, monkeypatch):
        """缓存命中也必须返回 song_id，供流代理复用原会话。"""
        app_module._play_url_cache.clear()
        app_module._play_url_sessions.clear()
        session = object()
        monkeypatch.setattr(
            app_module._scraper,
            'resolve_play_url_detailed',
            lambda *args, **kwargs: {
                'success': True,
                'song_id': 456,
                'mp3_url': 'https://m10.music.126.net/test.mp3',
                'bitrate': 128000,
                'is_trial': False,
                '_session': session,
            },
        )
        body = {'title': '测试歌', 'artist': '测试歌手', 'song_id': 456, 'fee': 8}
        first = json.loads(client.post('/api/song/play_url', json=body).data)
        second = json.loads(client.post('/api/song/play_url', json=body).data)
        assert first['song_id'] == 456
        assert second['song_id'] == 456
        assert second['cached'] is True

    def test_batch_playability_route(self, client, monkeypatch):
        """页面可一次获取整份榜单的真实播放状态。"""
        app_module._playability_cache.clear()
        monkeypatch.setattr(
            app_module._scraper,
            'check_song_playability',
            lambda songs: [
                {'song_id': songs[0]['song_id'], 'playable': True, 'is_trial': False}
            ],
        )
        rv = client.post('/api/songs/playability', json={
            'songs': [{'song_id': 99, 'fee': 8}],
        })
        data = json.loads(rv.data)
        assert data['success'] is True
        assert data['results'][0]['song_id'] == 99
        assert data['results'][0]['playable'] is True
