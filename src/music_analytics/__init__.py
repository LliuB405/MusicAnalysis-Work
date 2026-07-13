# -*- coding: utf-8 -*-
"""
音乐分析核心模块
"""

__version__ = "1.0.0"
__author__ = "Music Analytics Team"

from .config import Config
from .models import SongData, ArtistStat
from .scraper import MusicScraper
from .analyzer import ArtistAnalyzer
from .visualizer import ChartGenerator

__all__ = [
    "Config",
    "SongData",
    "ArtistStat",
    "MusicScraper",
    "ArtistAnalyzer",
    "ChartGenerator",
]