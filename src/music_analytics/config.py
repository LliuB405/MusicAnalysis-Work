# -*- coding: utf-8 -*-
"""
配置管理模块 - 集中管理所有配置
"""

import os
import secrets
from dataclasses import dataclass, field
from typing import List, Dict


@dataclass
class Config:
    """应用配置类"""

    # 网易云音乐相关配置
    base_url: str = "https://music.163.com"
    top_list_id: str = "3778678"
    target_url: str = field(default="https://music.163.com/discover/toplist?id=3778678")
    homepage_url: str = field(default="https://music.163.com/")
    # 搜索接口（用于获取歌曲播放链接）
    search_url: str = "https://music.163.com/api/search/get"
    # 歌曲直链接口
    song_url_endpoint: str = "https://music.163.com/api/song/enhance/player/url"
    # 接口响应里 mp3 的 host（用于拼完整 URL）
    mp3_host: str = "http://music.163.com"

    # API 端点列表（按优先级）
    api_endpoints: List[str] = field(default_factory=lambda: [
        "https://music.163.com/api/playlist/detail?id=3778678",
        "https://music.163.com/api/v6/playlist/detail?id=3778678",
    ])

    # 用户代理池
    user_agents: List[str] = field(default_factory=lambda: [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36 Edg/130.0.0.0",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:133.0) Gecko/20100101 Firefox/133.0",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    ])

    # 浏览器指纹
    browser_fingerprints: List[Dict[str, str]] = field(default_factory=lambda: [
        {
            "Sec-Ch-Ua": '"Not/A)Brand";v="8", "Chromium";v="131", "Google Chrome";v="131"',
            "Sec-Ch-Ua-Mobile": "?0",
            "Sec-Ch-Ua-Platform": '"Windows"',
        },
        {
            "Sec-Ch-Ua": '"Not/A)Brand";v="8", "Chromium";v="130", "Microsoft Edge";v="130"',
            "Sec-Ch-Ua-Mobile": "?0",
            "Sec-Ch-Ua-Platform": '"Windows"',
        },
    ])

    # 爬虫配置
    request_timeout: int = 15
    max_retries: int = 3
    min_delay: float = 0.3
    max_delay: float = 1.0

    # VIP 认证 - 网易云 MUSIC_U cookie
    # 留空 = 未登录模式（仅能听 fee=0/8 的歌曲，VIP 歌曲会 code=-110）
    # 设置后 = 登录模式（可听 VIP 歌曲）
    # 获取方式：浏览器登录 music.163.com → F12 → Application → Cookies → 复制 MUSIC_U 和 __csrf 的值
    vip_music_u: str = ""   # 例: "00b06bcd1a9..."
    vip_csrf: str = ""      # 例: "abc123def456..."

    # Flask 配置
    secret_key: str = field(
        default_factory=lambda: os.environ.get("MUSIC_ANALYSIS_SECRET_KEY")
        or secrets.token_urlsafe(32)
    )
    host: str = "127.0.0.1"
    port: int = 5000
    # 默认关闭 debug：避免 reloader 子进程被异常杀掉导致连接被拒
    # 需要调试时临时改成 True 即可
    debug: bool = False

    # 路径配置
    @property
    def base_dir(self) -> str:
        return os.path.dirname(os.path.abspath(__file__))

    @property
    def static_dir(self) -> str:
        return os.path.join(self.base_dir, "static")

    # 多榜单配置
    @property
    def chart_ids(self) -> Dict[str, str]:
        """支持的榜单 ID 映射"""
        return {
            "热歌榜": "3778678",
            "飙升榜": "19723756",
            "新歌榜": "3779629",
            "原创榜": "2884035",
            "网易云古典榜": "71384707",
            "网易云电音榜": "1978921795",
            "网易云中文说唱榜": "991319590",
            "网易云ACG榜": "71385702",
            "网易云韩语榜": "745956260",
            "网易云欧美热歌榜": "2809513713",
            "网易云欧美新歌榜": "2809577409",
            "网易云日语榜": "5059644681",
        }

    @property
    def chart_urls(self) -> Dict[str, str]:
        """榜单 ID 到 URL 的映射"""
        return {
            chart_id: f"https://music.163.com/discover/toplist?id={chart_id}"
            for chart_id in self.chart_ids.values()
        }

    # 定时任务配置
    auto_refresh_interval: int = 600  # 自动刷新间隔（秒），默认 10 分钟
    auto_refresh_on_start: bool = True  # 启动时是否立即执行一次
    history_retention_days: int = 30   # 历史数据保留天数

    @property
    def font_paths(self) -> List[str]:
        """跨平台字体路径"""
        import platform
        system = platform.system()

        if system == "Windows":
            return [
                "C:/Windows/Fonts/simhei.ttf",
                "C:/Windows/Fonts/msyh.ttc",
                "C:/Windows/Fonts/simsun.ttc",
            ]
        elif system == "Darwin":
            return [
                "/System/Library/Fonts/PingFang.ttc",
                "/Library/Fonts/Arial Unicode.ttf",
            ]
        else:
            return [
                "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc",
                "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
            ]


# 全局配置实例
config = Config()
