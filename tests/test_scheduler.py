# -*- coding: utf-8 -*-
"""
测试模块 - 调度器测试
"""

import pytest
import time
import tempfile
import os
from music_analytics.scheduler import Scheduler, TaskResult, SchedulerConfig
from music_analytics.config import Config
from music_analytics.models import SongData


class TestTaskResult:
    """测试任务结果"""

    def test_create_success(self):
        """测试创建成功结果"""
        result = TaskResult(
            success=True,
            message="测试成功",
            data={"count": 10}
        )
        assert result.success is True
        assert result.message == "测试成功"
        assert result.data["count"] == 10
        assert result.timestamp is not None

    def test_create_failure(self):
        """测试创建失败结果"""
        result = TaskResult(
            success=False,
            message="测试失败",
            data={"error": "错误信息"}
        )
        assert result.success is False
        assert result.message == "测试失败"

    def test_to_dict(self):
        """测试转换为字典"""
        result = TaskResult(success=True, message="测试")
        d = result.to_dict()
        assert isinstance(d, dict)
        assert "success" in d
        assert "message" in d
        assert "timestamp" in d


class TestScheduler:
    """测试调度器"""

    @pytest.fixture
    def scheduler(self):
        """创建调度器实例"""
        config = Config()
        config.auto_refresh_interval = 1  # 1秒用于测试
        config.auto_refresh_on_start = False
        return Scheduler(config)

    def test_init(self, scheduler):
        """测试初始化"""
        assert scheduler is not None
        assert scheduler._running is False

    def test_get_status(self, scheduler):
        """测试获取状态"""
        status = scheduler.get_status()
        assert isinstance(status, dict)
        assert "running" in status
        assert "interval" in status
        assert status["running"] is False

    def test_add_callback(self, scheduler):
        """测试添加回调"""
        callback_called = []

        def test_callback(result):
            callback_called.append(result)

        scheduler.add_callback(test_callback)
        assert len(scheduler._callbacks) == 1

    def test_run_now(self, scheduler, monkeypatch):
        """测试立即运行"""
        expected = TaskResult(success=True, message="mocked refresh")
        monkeypatch.setattr(scheduler, "scrape_all_charts", lambda: expected)

        result = scheduler.run_now()

        assert isinstance(result, TaskResult)
        assert result is expected

    def test_start_stop(self, scheduler):
        """测试启动和停止"""
        # 启动
        result = scheduler.start()
        assert result is True
        assert scheduler._running is True

        # 停止
        result = scheduler.stop()
        assert result is True
        assert scheduler._running is False

    def test_double_start(self, scheduler):
        """测试重复启动"""
        scheduler.start()
        result = scheduler.start()
        assert result is False
        scheduler.stop()

    def test_double_stop(self, scheduler):
        """测试重复停止"""
        scheduler.start()
        scheduler.stop()
        result = scheduler.stop()
        assert result is False

    def test_start_stop_timing(self, scheduler):
        """测试启动和停止时序"""
        scheduler.config.auto_refresh_interval = 2
        scheduler.start()

        # 确保线程已启动
        time.sleep(0.5)
        assert scheduler._thread is not None
        assert scheduler._thread.is_alive()

        scheduler.stop()

        # 等待线程结束
        time.sleep(1)
        assert scheduler._running is False
