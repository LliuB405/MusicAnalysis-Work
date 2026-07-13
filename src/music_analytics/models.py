# -*- coding: utf-8 -*-
"""
数据模型 - 类型安全的数据结构
"""

from dataclasses import dataclass, field
from typing import List, Optional
from datetime import datetime


@dataclass
class SongData:
    """歌曲数据结构"""
    rank: int
    title: str
    artist: str
    # 榜单接口会直接返回歌曲 ID 与收费类型。保留这两个字段可以避免播放时
    # 再次只靠歌名搜索，从而误匹配到同名歌曲或错误版本。
    song_id: Optional[int] = None
    fee: Optional[int] = None

    def __post_init__(self) -> None:
        """数据验证"""
        if self.rank < 1:
            raise ValueError(f"排名必须 >= 1, 得到 {self.rank}")
        if not self.title:
            raise ValueError("歌曲名称不能为空")
        if not self.artist:
            self.artist = "未知歌手"

    def to_dict(self) -> dict:
        data = {"rank": self.rank, "title": self.title, "artist": self.artist}
        # 兼容旧调用：没有播放元数据时仍保持原来的三个字段。
        if self.song_id is not None:
            data["song_id"] = self.song_id
        if self.fee is not None:
            data["fee"] = self.fee
        return data

    @classmethod
    def from_dict(cls, data: dict) -> "SongData":
        return cls(
            rank=data.get("rank", 0),
            title=data.get("title", ""),
            artist=data.get("artist", "未知歌手"),
            song_id=data.get("song_id") or data.get("id"),
            fee=data.get("fee"),
        )


@dataclass
class ArtistStat:
    """歌手统计数据"""
    name: str
    count: int
    percentage: float = 0.0

    def __post_init__(self) -> None:
        if self.count < 0:
            raise ValueError(f"上榜次数必须 >= 0, 得到 {self.count}")

    def to_dict(self) -> dict:
        return {"name": self.name, "count": self.count, "percentage": self.percentage}


@dataclass
class ScrapeResult:
    """爬取结果"""
    success: bool
    method: str
    data: List[SongData] = field(default_factory=list)
    online: bool = True
    error: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.now)

    @property
    def count(self) -> int:
        return len(self.data)

    def to_dict(self) -> dict:
        return {
            "success": self.success,
            "method": self.method,
            "count": self.count,
            "online": self.online,
            "error": self.error,
            "timestamp": self.timestamp.isoformat(),
        }


@dataclass
class AnalysisResult:
    """分析结果"""
    top10: List[ArtistStat]
    total_artists: int
    total_songs: int

    def to_dict(self) -> dict:
        return {
            "top10": [stat.to_dict() for stat in self.top10],
            "total_artists": self.total_artists,
            "total_songs": self.total_songs,
        }
