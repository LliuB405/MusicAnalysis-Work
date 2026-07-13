# -*- coding: utf-8 -*-
"""
数据分析模块 - 业务逻辑层
"""

import re
import logging
from typing import List, Dict, Set
from collections import Counter

from .models import SongData, ArtistStat, AnalysisResult

logger = logging.getLogger(__name__)

# 歌手分隔符正则：/、, & 中英文逗号
_ARTIST_DELIMITER_RE = re.compile(r'[/、,&，]')


class ArtistAnalyzer:
    """歌手数据分析类"""

    def __init__(self, songs: List[SongData]) -> None:
        self.songs: List[SongData] = songs

    @property
    def total_songs(self) -> int:
        return len(self.songs)

    def get_all_artists(self) -> List[str]:
        """获取所有歌手列表（拆分为独立歌手）"""
        all_artists: List[str] = []
        for song in self.songs:
            parts: List[str] = _ARTIST_DELIMITER_RE.split(song.artist)
            for part in parts:
                part = part.strip()
                if part:
                    all_artists.append(part)
        return all_artists

    def count_artist_frequency(self) -> Counter:
        """统计歌手上榜频次"""
        all_artists: List[str] = self.get_all_artists()
        return Counter(all_artists)

    def get_top_artists(self, n: int = 10) -> List[ArtistStat]:
        """获取 TOP N 歌手"""
        counter: Counter = self.count_artist_frequency()
        total: int = len(self.get_all_artists())

        top_n = counter.most_common(n)
        results: List[ArtistStat] = []

        for name, count in top_n:
            percentage: float = (count / total * 100) if total > 0 else 0.0
            results.append(ArtistStat(
                name=name,
                count=count,
                percentage=round(percentage, 1),
            ))

        return results

    def get_unique_artists(self) -> Set[str]:
        """获取去重后的歌手集合"""
        unique: Set[str] = set()
        for song in self.songs:
            for a in _ARTIST_DELIMITER_RE.split(song.artist):
                artist: str = a.strip()
                if artist:
                    unique.add(artist)
        return unique

    def analyze(self) -> AnalysisResult:
        """执行完整分析"""
        top10: List[ArtistStat] = self.get_top_artists(10)
        unique_artists: Set[str] = self.get_unique_artists()

        return AnalysisResult(
            top10=top10,
            total_artists=len(unique_artists),
            total_songs=self.total_songs,
        )

    def get_artist_dict(self) -> Dict[str, int]:
        """获取歌手频次字典（用于词云）"""
        return dict(self.count_artist_frequency())