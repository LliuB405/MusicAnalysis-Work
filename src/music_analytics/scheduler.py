# -*- coding: utf-8 -*-
"""
定时任务调度器 - 自动刷新模块
"""

import logging
import time
import threading
from datetime import datetime
from typing import Callable, Dict, List, Optional, Any
from dataclasses import dataclass, asdict

from .config import Config
from .scraper import MusicScraper
from .history import HistoryManager

logger = logging.getLogger(__name__)


@dataclass
class SchedulerConfig:
    """调度器配置"""
    interval: int = 600  # 刷新间隔（秒）
    enabled: bool = True  # 是否启用
    run_on_start: bool = True  # 是否启动时立即运行一次


class TaskResult:
    """任务执行结果"""

    def __init__(self, success: bool, message: str, data: Optional[Dict[str, Any]] = None):
        self.success = success
        self.message = message
        self.data = data or {}
        self.timestamp = datetime.now().isoformat()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "message": self.message,
            "data": self.data,
            "timestamp": self.timestamp
        }


class Scheduler:
    """定时任务调度器"""

    def __init__(self, config: Optional[Config] = None) -> None:
        self.config = config or Config()
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()

        # 初始化组件
        self.scraper = MusicScraper(self.config)
        self.history_manager = HistoryManager()

        # 回调函数
        self._callbacks: List[Callable[[TaskResult], None]] = []

        # 上次执行结果
        self._last_result: Optional[TaskResult] = None

    def add_callback(self, callback: Callable[[TaskResult], None]) -> None:
        """添加任务完成后的回调函数"""
        self._callbacks.append(callback)

    def _notify_callbacks(self, result: TaskResult) -> None:
        """通知所有回调函数"""
        for callback in self._callbacks:
            try:
                callback(result)
            except Exception as e:
                logger.warning(f"[调度器] 回调函数执行失败: {e}")

    def scrape_all_charts(self) -> TaskResult:
        """执行所有榜单的爬取任务"""
        try:
            logger.info("[调度器] 开始执行定时爬取任务...")

            # 爬取所有榜单
            all_data = self.scraper.scrape_all_charts()

            # 保存到历史记录
            saved_count = 0
            for chart_name, songs in all_data.items():
                chart_id = self.config.chart_ids.get(chart_name, "")
                self.history_manager.save_snapshot(chart_name, chart_id, songs)
                saved_count += 1

            logger.info(f"[调度器] 定时爬取完成，保存了 {saved_count} 个榜单")

            self._last_result = TaskResult(
                success=True,
                message=f"成功爬取 {saved_count} 个榜单",
                data={
                    "charts": list(all_data.keys()),
                    "chart_count": saved_count
                }
            )

            self._notify_callbacks(self._last_result)
            return self._last_result

        except Exception as e:
            logger.error(f"[调度器] 定时爬取失败: {e}", exc_info=True)

            self._last_result = TaskResult(
                success=False,
                message=f"爬取失败: {str(e)}",
                data={"error": str(e)}
            )

            self._notify_callbacks(self._last_result)
            return self._last_result

    def _run_loop(self) -> None:
        """运行调度循环"""
        interval = self.config.auto_refresh_interval
        logger.info(f"[调度器] 启动定时任务，刷新间隔: {interval} 秒")

        # 如果配置了启动时立即运行
        if self.config.auto_refresh_on_start:
            logger.info("[调度器] 启动时立即执行首次爬取...")
            self.scrape_all_charts()

        while not self._stop_event.is_set():
            # 等待指定时间或直到收到停止信号
            self._stop_event.wait(timeout=interval)

            if self._stop_event.is_set():
                break

            # 执行爬取
            self.scrape_all_charts()

        logger.info("[调度器] 定时任务已停止")

    def start(self) -> bool:
        """启动调度器"""
        if self._running:
            logger.warning("[调度器] 调度器已在运行中")
            return False

        self._running = True
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()

        logger.info("[调度器] 调度器已启动")
        return True

    def stop(self) -> bool:
        """停止调度器"""
        if not self._running:
            logger.warning("[调度器] 调度器未在运行")
            return False

        logger.info("[调度器] 正在停止调度器...")
        self._stop_event.set()

        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=5)

        self._running = False
        logger.info("[调度器] 调度器已停止")
        return True

    def get_status(self) -> Dict[str, Any]:
        """获取调度器状态"""
        return {
            "running": self._running,
            "interval": self.config.auto_refresh_interval,
            "last_result": self._last_result.to_dict() if self._last_result else None
        }

    def run_now(self) -> TaskResult:
        """立即执行一次爬取"""
        return self.scrape_all_charts()


# 全局调度器实例
_scheduler: Optional[Scheduler] = None


def get_scheduler(config: Optional[Config] = None) -> Scheduler:
    """获取全局调度器实例"""
    global _scheduler
    if _scheduler is None:
        _scheduler = Scheduler(config)
    return _scheduler
