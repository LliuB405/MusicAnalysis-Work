# -*- coding: utf-8 -*-
"""
爬虫模块 - 数据获取层
"""

import json
import time
import random
import logging
import re
import unicodedata
from difflib import SequenceMatcher
from typing import List, Optional, Dict, Any
from collections import Counter

import requests
from bs4 import BeautifulSoup

from .config import Config
from .models import SongData, ScrapeResult

logger = logging.getLogger(__name__)


class ScraperError(Exception):
    """爬虫基础异常"""
    pass


class NetworkError(ScraperError):
    """网络请求异常"""
    pass


class ParseError(ScraperError):
    """数据解析异常"""
    pass


class MusicScraper:
    """网易云音乐爬虫类"""

    def __init__(self, config: Optional[Config] = None) -> None:
        self.config: Config = config or Config()
        self._session: Optional[requests.Session] = None

    # ==================== 私有方法 ====================

    def _build_session(self) -> requests.Session:
        """构建带持久化 Cookie 的 Session

        如果 config.vip_music_u 不为空，会注入登录 cookie，
        这样可以播放 VIP 歌曲（fee=1）。
        """
        session = requests.Session()

        # 随机选择 User-Agent 和指纹
        ua = random.choice(self.config.user_agents)
        fp = random.choice(self.config.browser_fingerprints)

        session.headers.update({
            "User-Agent": ua,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            "Accept-Encoding": "gzip, deflate, br",
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "DNT": "1",
            "Upgrade-Insecure-Requests": "1",
            **fp,
        })

        # 注入 VIP cookie（如果有）
        if self.config.vip_music_u:
            session.cookies.set("MUSIC_U", self.config.vip_music_u, domain=".music.163.com")
        if self.config.vip_csrf:
            session.cookies.set("__csrf", self.config.vip_csrf, domain=".music.163.com")

        return session

    def _random_delay(self) -> None:
        """随机延时，模拟人类行为"""
        delay = random.uniform(self.config.min_delay, self.config.max_delay)
        time.sleep(delay)

    def _fetch_with_retry(
        self,
        url: str,
        method: str = "GET",
        max_retries: int = 3,
        **kwargs
    ) -> Optional[requests.Response]:
        """带重试的请求方法"""
        session = self._build_session()

        for attempt in range(1, max_retries + 1):
            try:
                if method.upper() == "POST":
                    resp = session.post(url, timeout=self.config.request_timeout, **kwargs)
                else:
                    resp = session.get(url, timeout=self.config.request_timeout, **kwargs)

                if resp.status_code == 200:
                    return resp
                else:
                    logger.warning(f"请求返回 {resp.status_code}: {url}")

            except requests.Timeout:
                logger.warning(f"请求超时 (尝试 {attempt}/{max_retries}): {url}")
            except requests.RequestException as e:
                logger.warning(f"请求异常 (尝试 {attempt}/{max_retries}): {e}")

            if attempt < max_retries:
                time.sleep(2 * attempt)  # 指数退避

        return None

    def _parse_tracks(self, tracks: List[Dict[str, Any]]) -> List[SongData]:
        """解析 API 返回的 tracks

        网易云 playlist/detail API 的实际字段结构：
        - 歌名: track["name"]
        - 歌手: track["ar"][i]["name"]  （数组，每个元素含 name/id）
        - 专辑: track["al"]["name"]  （可能影响歌手解析的兜底）
        兼容历史字段 artists / ar / singers。
        """
        songs: List[SongData] = []
        for idx, track in enumerate(tracks, 1):
            artist_list = track.get("ar") or track.get("artists") or track.get("singers") or []
            artist_names: List[str] = []
            for ar in artist_list:
                if isinstance(ar, dict):
                    name = ar.get("name") or ""
                    if name:
                        artist_names.append(name)
                elif isinstance(ar, str) and ar:
                    artist_names.append(ar)
            artists = " / ".join(artist_names) if artist_names else "未知歌手"

            songs.append(SongData(
                rank=idx,
                title=track.get("name") or "未知歌名",
                artist=artists,
                song_id=track.get("id"),
                fee=track.get("fee"),
            ))
        return songs

    def _parse_song_list(self, data_list: List[Dict[str, Any]]) -> List[SongData]:
        """解析歌曲列表数据"""
        songs = []
        for idx, item in enumerate(data_list, 1):
            # 兼容多种字段名
            artists = item.get("artists", item.get("ar", item.get("singers", [])))
            if isinstance(artists, list):
                artist_names = " / ".join([
                    a.get("name", "未知歌手") if isinstance(a, dict) else str(a)
                    for a in artists
                ])
            else:
                artist_names = str(artists) if artists else "未知歌手"

            title = item.get("name", item.get("title", item.get("songName", "未知歌名")))

            songs.append(SongData(
                rank=idx,
                title=title,
                artist=artist_names,
                song_id=item.get("id"),
                fee=item.get("fee"),
            ))
        return songs

    @staticmethod
    def _normalize_match_text(value: str) -> str:
        """统一全半角、大小写和标点，供歌曲候选匹配使用。"""
        normalized = unicodedata.normalize("NFKC", value or "").casefold()
        return re.sub(r"[^\w]+", "", normalized, flags=re.UNICODE)

    @staticmethod
    def _artist_names(song: Dict[str, Any]) -> List[str]:
        artists = song.get("artists") or song.get("ar") or song.get("singers") or []
        names: List[str] = []
        for artist in artists:
            if isinstance(artist, dict) and artist.get("name"):
                names.append(str(artist["name"]))
            elif isinstance(artist, str) and artist:
                names.append(artist)
        return names

    def _score_song_candidate(self, song: Dict[str, Any], title: str, artist: str) -> Dict[str, Any]:
        """为搜索结果打分，优先精确歌名与歌手，而不是盲取第一条。"""
        candidate = dict(song)
        wanted_title = self._normalize_match_text(title)
        found_title = self._normalize_match_text(str(song.get("name") or ""))
        title_similarity = SequenceMatcher(None, wanted_title, found_title).ratio() if found_title else 0.0
        if wanted_title and found_title and (wanted_title in found_title or found_title in wanted_title):
            title_similarity = max(title_similarity, 0.9)
        if wanted_title == found_title and wanted_title:
            title_similarity = 1.0

        wanted_artist = self._normalize_match_text(artist)
        found_artists = self._artist_names(song)
        found_artist = self._normalize_match_text("/".join(found_artists))
        if wanted_artist and found_artist:
            artist_similarity = SequenceMatcher(None, wanted_artist, found_artist).ratio()
            if wanted_artist in found_artist or found_artist in wanted_artist:
                artist_similarity = max(artist_similarity, 0.92)
        else:
            # 某些旧版搜索响应不带歌手字段，保留候选但不额外加分。
            artist_similarity = 0.0

        candidate["_title_similarity"] = title_similarity
        candidate["_artist_similarity"] = artist_similarity
        candidate["_match_score"] = title_similarity * 100 + artist_similarity * 45
        candidate["_artist_names"] = found_artists
        return candidate

    # ==================== 公共策略方法 ====================

    def scrape_via_api(self) -> Optional[List[SongData]]:
        """策略一：通过 API 接口获取数据"""
        logger.info("[策略一] 尝试通过 API 接口获取数据...")

        session = self._build_session()
        self._random_delay()

        # 先访问首页获取 Cookie
        session.get(self.config.homepage_url, timeout=self.config.request_timeout)
        self._random_delay()

        # 访问榜单页建立会话
        session.headers.update({"Referer": self.config.homepage_url})
        session.get(self.config.target_url, timeout=self.config.request_timeout)
        self._random_delay()

        # 尝试多个 API 端点
        for endpoint in self.config.api_endpoints:
            try:
                # POST 请求
                # 关键：Accept-Encoding: identity 强制服务器返回未压缩的明文 JSON，
                # 避免 gzip/brotli 压缩响应导致 JSON 解析失败
                session.headers.update({
                    "Referer": self.config.target_url,
                    "X-Requested-With": "XMLHttpRequest",
                    "Content-Type": "application/x-www-form-urlencoded",
                    "Accept-Encoding": "identity",
                })

                resp = session.post(
                    endpoint,
                    timeout=self.config.request_timeout,
                )

                if resp.status_code != 200:
                    continue

                data = resp.json()
                code = data.get("code", -1)

                if code == 200:
                    tracks = data.get("result", {}).get("tracks", [])
                    if tracks:
                        songs = self._parse_tracks(tracks)
                        logger.info(f"[策略一] 成功获取 {len(songs)} 首歌曲")
                        return songs
                elif code == 301:
                    logger.info("[策略一] 需要登录，切换端点重试")

            except (json.JSONDecodeError, ValueError):
                logger.error(f"[策略一] JSON 解析失败: {endpoint}")
            except requests.RequestException as e:
                logger.error(f"[策略一] 请求异常: {e}")

        return None

    def scrape_via_html(self) -> Optional[List[SongData]]:
        """策略二：通过 HTML 页面解析数据"""
        logger.info("[策略二] 尝试通过 HTML 页面解析数据...")

        session = self._build_session()
        self._random_delay()

        try:
            # 关键：禁用压缩，避免中文/特殊字符在解压时被破坏
            session.headers.update({
                "Referer": self.config.homepage_url,
                "Accept-Encoding": "identity",
            })
            resp = session.get(self.config.target_url, timeout=self.config.request_timeout)

            if resp.status_code != 200:
                logger.warning(f"[策略二] HTML 页面返回状态码: {resp.status_code}")
                return None

            soup = BeautifulSoup(resp.text, "html.parser")

            # 模式 A：从 textarea 提取
            textarea = soup.find("textarea", id="song-list-pre-data")
            if textarea and textarea.text.strip():
                try:
                    song_list = json.loads(textarea.text.strip())
                    songs = self._parse_song_list(song_list)
                    if songs:
                        logger.info(f"[策略二-A] 从 textarea 成功获取 {len(songs)} 首歌曲")
                        return songs
                except json.JSONDecodeError as e:
                    logger.error(f"[策略二-A] textarea 解析失败: {e}")

            # 模式 B：从 script 标签提取
            for script in soup.find_all("script"):
                script_text = script.string or ""
                for prefix in ["window.__NUXT__=", "window.__INITIAL_STATE__="]:
                    if prefix in script_text:
                        try:
                            json_str = script_text.split(prefix, 1)[1]
                            end = json_str.find(";</script>")
                            if end > 0:
                                json_str = json_str[:end]

                            data = json.loads(json_str)
                            songs = self._extract_songs_from_json(data)
                            if songs:
                                logger.info(f"[策略二-B] 从 script 成功获取 {len(songs)} 首歌曲")
                                return songs
                        except (json.JSONDecodeError, Exception) as e:
                            logger.error(f"[策略二-B] script 解析失败: {e}")

            logger.warning("[策略二] 未能从 HTML 中提取到有效数据")
            return None

        except requests.Timeout:
            logger.error("[策略二] 请求超时")
            return None
        except requests.RequestException as e:
            logger.error(f"[策略二] 异常: {e}")
            return None

    def _extract_songs_from_json(
        self,
        data: Any,
        depth: int = 0
    ) -> Optional[List[SongData]]:
        """递归提取 JSON 中的歌曲数据"""
        if depth > 10:
            return None

        if isinstance(data, list) and len(data) > 0:
            # 检查是否为歌曲数据
            if all(
                isinstance(item, dict) and ("name" in item)
                for item in data[:3]
            ):
                return self._parse_song_list(data)

        if isinstance(data, dict):
            for value in data.values():
                result = self._extract_songs_from_json(value, depth + 1)
                if result:
                    return result

        return None

    def get_fallback_data(self) -> List[SongData]:
        """策略三：备用数据兜底"""
        logger.info("[策略三] 使用备用数据兜底...")

        fallback = [
            {"rank": 1, "title": "晴天", "artist": "周杰伦"},
            {"rank": 2, "title": "七里香", "artist": "周杰伦"},
            {"rank": 3, "title": "夜曲", "artist": "周杰伦"},
            {"rank": 4, "title": "稻香", "artist": "周杰伦"},
            {"rank": 5, "title": "花海", "artist": "周杰伦"},
            {"rank": 6, "title": "十年", "artist": "陈奕迅"},
            {"rank": 7, "title": "富士山下", "artist": "陈奕迅"},
            {"rank": 8, "title": "好久���见", "artist": "陈奕迅"},
            {"rank": 9, "title": "浮夸", "artist": "陈奕迅"},
            {"rank": 10, "title": "红玫瑰", "artist": "陈奕迅"},
            # ... 更多数据
        ]

        return [SongData.from_dict(item) for item in fallback]

    # ==================== 播放链接 ====================

    def search_song_id(self, title: str, artist: str) -> Optional[int]:
        """根据歌名+歌手搜索 song id"""
        try:
            keyword = f"{title} {artist}".strip()
            session = self._build_session()
            session.headers.update({
                "Referer": self.config.target_url,
                "Accept-Encoding": "identity",
            })
            resp = session.post(
                self.config.search_url,
                data={"s": keyword, "limit": "1", "type": "1", "offset": "0"},
                timeout=self.config.request_timeout,
            )
            if resp.status_code != 200:
                return None
            data = resp.json()
            songs = (data.get("result") or {}).get("songs") or []
            if not songs:
                return None
            return int(songs[0].get("id", 0)) or None
        except (json.JSONDecodeError, requests.RequestException, ValueError, TypeError) as e:
            logger.warning(f"搜索歌曲失败 [{title}/{artist}]: {e}")
            return None

    def get_song_url(self, song_id: int) -> Optional[str]:
        """根据 song id 获取 mp3 直链

        网易云 enhance/player/url 接口对 ids 格式敏感：
        - ids 必须是 JSON 字符串，例如 "[123456]"
        - 直接传 list/str/csv 会被服务端拒绝（code=400）
        - 部分歌曲可能无版权（code=404, url=null），返回 None
        """
        try:
            import json as _json
            session = self._build_session()
            session.headers.update({
                "Referer": self.config.target_url,
                "Accept-Encoding": "identity",
            })
            resp = session.post(
                self.config.song_url_endpoint,
                data={"ids": _json.dumps([song_id]), "br": 320000},
                timeout=self.config.request_timeout,
            )
            if resp.status_code != 200:
                return None
            data = resp.json()
            items = data.get("data") or []
            if not items:
                return None
            url = items[0].get("url")
            if not url:
                # code=404 通常是版权问题或试听已下架
                logger.info(f"歌曲无版权或已下架 [id={song_id}]")
                return None
            return url
        except (json.JSONDecodeError, requests.RequestException, ValueError, TypeError, KeyError) as e:
            logger.warning(f"获取播放链接失败 [id={song_id}]: {e}")
            return None

    def resolve_play_url(self, title: str, artist: str) -> Optional[Dict[str, Any]]:
        """一键：歌名+歌手 → {song_id, mp3_url}"""
        song_id = self.search_song_id(title, artist)
        if not song_id:
            return None
        mp3_url = self.get_song_url(song_id)
        if not mp3_url:
            return None
        return {"song_id": song_id, "mp3_url": mp3_url}

    def search_song_candidates(
        self,
        title: str,
        artist: str,
        session: Optional[requests.Session] = None,
        limit: int = 8,
    ) -> List[Dict[str, Any]]:
        """搜索并按歌名/歌手相似度排序，返回可信候选版本。"""
        active_session = session or self._build_session()
        active_session.headers.update({
            "Referer": self.config.target_url,
            "Accept-Encoding": "identity",
        })
        response = active_session.post(
            self.config.search_url,
            data={"s": f"{title} {artist}".strip(), "limit": str(limit), "type": "1", "offset": "0"},
            timeout=self.config.request_timeout,
        )
        if response.status_code != 200:
            return []
        songs = (response.json().get("result") or {}).get("songs") or []
        scored = [self._score_song_candidate(song, title, artist) for song in songs if song.get("id")]
        scored.sort(key=lambda item: item.get("_match_score", 0), reverse=True)

        # 防止同名搜索结果完全偏题。若旧接口缺字段，至少保留第一条兼容结果。
        credible = [item for item in scored if item.get("_title_similarity", 0) >= 0.52]
        return (credible or scored[:1])[:limit]

    @staticmethod
    def _trial_info(item: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """只把真正可消费的官方试听信息标记为试听。"""
        direct = item.get("freeTrialInfo")
        if direct:
            return direct
        privilege = item.get("freeTrialPrivilege") or {}
        if privilege.get("userConsumable") or privilege.get("resConsumable"):
            return privilege
        timed = item.get("freeTimeTrialPrivilege") or {}
        if timed.get("type") or (timed.get("remainTime") or 0) > 0:
            return timed
        return None

    @staticmethod
    def _restriction_for(
        fee: Optional[int],
        item: Optional[Dict[str, Any]] = None,
        privilege: Optional[Dict[str, Any]] = None,
        service_responded: bool = True,
    ) -> Dict[str, str]:
        """把官方接口状态统一翻译成前端可理解的限制原因。"""
        item = item or {}
        privilege = privilege or {}
        try:
            normalized_fee = int(fee) if fee is not None else None
        except (TypeError, ValueError):
            normalized_fee = None
        item_code = item.get("code")

        if normalized_fee == 1 or item_code == -110:
            return {
                "reason": "vip_required",
                "error": "该歌曲需要网易云音乐 VIP，当前网页不能绕过会员限制播放",
            }
        if normalized_fee == 4:
            return {
                "reason": "purchase_required",
                "error": "该歌曲属于付费专辑，请在网易云音乐完成购买后播放",
            }
        if privilege.get("st", 0) < 0 or item_code == 404:
            return {
                "reason": "copyright_unavailable",
                "error": "该歌曲在当前账号、地区或版权状态下暂不可播放",
            }
        if not service_responded:
            return {
                "reason": "service_unavailable",
                "error": "音乐服务暂时无响应，请稍后重试",
            }
        return {
            "reason": "playback_unavailable",
            "error": "官方接口当前未提供可播放链接，可能受版权或账号权限限制",
        }

    def check_song_playability(self, songs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """批量预检歌曲当前是否可播放，不返回或缓存临时音频直链。"""
        normalized: List[Dict[str, Any]] = []
        seen = set()
        for song in songs[:250]:
            try:
                current_id = int(song.get("song_id") or song.get("id"))
            except (TypeError, ValueError):
                continue
            if current_id <= 0 or current_id in seen:
                continue
            seen.add(current_id)
            normalized.append({"song_id": current_id, "fee": song.get("fee")})
        if not normalized:
            return []

        session = self._build_session()
        session.headers.update({
            "Referer": self.config.target_url,
            "Accept-Encoding": "identity",
        })
        results: List[Dict[str, Any]] = []
        for start in range(0, len(normalized), 100):
            chunk = normalized[start:start + 100]
            ids = [entry["song_id"] for entry in chunk]
            try:
                response = session.post(
                    self.config.song_url_endpoint,
                    data={"ids": json.dumps(ids), "br": 128000},
                    timeout=self.config.request_timeout,
                )
                if response.status_code != 200:
                    raise requests.RequestException(f"HTTP {response.status_code}")
                items = {
                    int(item["id"]): item
                    for item in (response.json().get("data") or [])
                    if item.get("id") is not None
                }
                for entry in chunk:
                    item = items.get(entry["song_id"], {})
                    if item.get("url"):
                        trial_info = self._trial_info(item)
                        results.append({
                            "song_id": entry["song_id"],
                            "playable": True,
                            "is_trial": bool(trial_info),
                        })
                    else:
                        restriction = self._restriction_for(entry.get("fee"), item=item)
                        results.append({
                            "song_id": entry["song_id"],
                            "playable": False,
                            **restriction,
                        })
            except (json.JSONDecodeError, requests.RequestException, ValueError, TypeError) as exc:
                logger.warning("批量检查播放状态失败: %s", exc)
                results.extend({
                    "song_id": entry["song_id"],
                    "playable": False,
                    "reason": "service_unavailable",
                    "error": "播放状态检查暂时失败，请稍后重试",
                } for entry in chunk)
        return results

    def resolve_play_url_detailed(
        self,
        title: str,
        artist: str,
        song_id: Optional[int] = None,
        fee: Optional[int] = None,
    ) -> Dict[str, Any]:
        """解析歌曲播放地址，并区分 VIP、付费专辑、版权与搜索失败。

        该方法只请求官方接口实际允许的完整歌曲或官方试听，不绕过会员/付费限制。
        榜单已带 song_id 时会直接使用，避免同名歌曲误匹配；旧数据则搜索多个候选。
        """
        session = self._build_session()
        session.headers.update({
            "Referer": self.config.target_url,
            "Accept-Encoding": "identity",
        })

        try:
            if song_id:
                candidates = [{
                    "id": int(song_id),
                    "name": title,
                    "artists": [{"name": artist}],
                    "fee": fee,
                    "_match_score": 999.0,
                    "_title_similarity": 1.0,
                    "_artist_similarity": 1.0,
                    "_artist_names": [artist],
                }]
            else:
                candidates = self.search_song_candidates(title, artist, session=session, limit=8)

            if not candidates:
                return {
                    "success": False,
                    "reason": "not_found",
                    "error": "未找到匹配的歌曲版本",
                }

            candidate_ids = [int(item["id"]) for item in candidates[:6]]
            available: Dict[int, Dict[str, Any]] = {}
            last_items: Dict[int, Dict[str, Any]] = {}
            service_responded = False

            # 高码率不可用时自动降级到低码率；这是官方接口允许的质量降级，
            # 不会把 VIP/付费歌曲变成免费歌曲。
            for requested_bitrate in (320000, 192000, 128000, 96000):
                response = session.post(
                    self.config.song_url_endpoint,
                    data={"ids": json.dumps(candidate_ids), "br": requested_bitrate},
                    timeout=self.config.request_timeout,
                )
                if response.status_code != 200:
                    continue
                service_responded = True
                payload = response.json()
                for item in payload.get("data") or []:
                    try:
                        item_id = int(item.get("id"))
                    except (TypeError, ValueError):
                        continue
                    last_items[item_id] = item
                    if item.get("url") and item_id not in available:
                        available[item_id] = {
                            "item": item,
                            "requested_bitrate": requested_bitrate,
                        }

                # 最可信候选已经有合法 URL 时无需继续降低码率。
                if candidate_ids[0] in available:
                    break

            for candidate in candidates[:6]:
                candidate_id = int(candidate["id"])
                resolved = available.get(candidate_id)
                if not resolved:
                    continue
                item = resolved["item"]
                trial_info = self._trial_info(item)
                artist_names = candidate.get("_artist_names") or self._artist_names(candidate)
                return {
                    "success": True,
                    "song_id": candidate_id,
                    "mp3_url": item["url"],
                    "bitrate": item.get("br") or resolved["requested_bitrate"],
                    "is_trial": bool(trial_info),
                    "trial_info": trial_info,
                    "fee": candidate.get("fee"),
                    "matched_title": candidate.get("name") or title,
                    "matched_artist": " / ".join(artist_names) or artist,
                    "_session": session,
                }

            best = candidates[0]
            best_id = int(best["id"])
            best_fee = best.get("fee")
            privilege = best.get("privilege") or {}
            if best_fee is None:
                best_fee = privilege.get("fee")
            best_item = last_items.get(best_id) or {}
            official_url = f"https://music.163.com/song?id={best_id}"
            restriction = self._restriction_for(
                best_fee,
                item=best_item,
                privilege=privilege,
                service_responded=service_responded,
            )

            return {
                "success": False,
                **restriction,
                "song_id": best_id,
                "fee": best_fee,
                "official_url": official_url,
                "matched_title": best.get("name") or title,
                "matched_artist": " / ".join(best.get("_artist_names") or []) or artist,
            }
        except (json.JSONDecodeError, requests.RequestException, ValueError, TypeError) as exc:
            logger.warning("详细解析播放链接失败 [%s/%s]: %s", title, artist, exc)
            return {
                "success": False,
                "reason": "network_error",
                "error": "获取播放权限时网络异常，请稍后重试",
            }
        except Exception as exc:
            logger.warning("详细解析播放链接失败 [%s/%s]: %s", title, artist, exc)
            return {
                "success": False,
                "reason": "service_unavailable",
                "error": "音乐服务暂时不可用，请稍后重试",
            }

    def resolve_play_url_streamable(self, title: str, artist: str) -> Optional[Dict[str, Any]]:
        """一键：歌名+歌手 → {song_id, mp3_url, _session}

        与 resolve_play_url 不同的是，使用**同一个 session** 完成 search + get_url，
        这样 mp3 URL 的 authSecret 与后续 stream 拉取用的 session 一致，
        避免网易云 CDN 的 403。
        """
        info = self.resolve_play_url_detailed(title, artist)
        if not info.get("success"):
            return None
        return {
            "song_id": info["song_id"],
            "mp3_url": info["mp3_url"],
            "_session": info["_session"],
            "bitrate": info.get("bitrate"),
            "is_trial": info.get("is_trial", False),
        }

    # ==================== 多榜单爬取 ====================

    def scrape_chart(self, chart_id: str) -> Optional[List[SongData]]:
        """爬取指定榜单的数据"""
        logger.info(f"[多榜单] 正在爬取榜单 ID: {chart_id}")

        session = self._build_session()
        self._random_delay()

        # 先访问首页获取 Cookie
        try:
            session.get(self.config.homepage_url, timeout=self.config.request_timeout)
            self._random_delay()
        except Exception:
            pass

        # 构建榜单 URL
        chart_url = f"https://music.163.com/discover/toplist?id={chart_id}"

        # 尝试 API 方式
        api_url = f"https://music.163.com/api/playlist/detail?id={chart_id}"
        session.headers.update({
            "Referer": chart_url,
            "X-Requested-With": "XMLHttpRequest",
            "Content-Type": "application/x-www-form-urlencoded",
            "Accept-Encoding": "identity",
        })

        try:
            resp = session.post(api_url, timeout=self.config.request_timeout)
            if resp.status_code == 200:
                data = resp.json()
                code = data.get("code", -1)
                if code == 200:
                    tracks = data.get("result", {}).get("tracks", [])
                    if tracks:
                        songs = self._parse_tracks(tracks)
                        logger.info(f"[多榜单] 成功获取榜单 {chart_id} 的 {len(songs)} 首歌曲")
                        return songs
        except Exception as e:
            logger.warning(f"[多榜单] API 方式失败: {e}")

        # 尝试 HTML 方式作为备选
        session.headers.update({
            "Referer": self.config.homepage_url,
            "Accept-Encoding": "identity",
        })

        try:
            resp = session.get(chart_url, timeout=self.config.request_timeout)
            if resp.status_code == 200:
                soup = BeautifulSoup(resp.text, "html.parser")
                textarea = soup.find("textarea", id="song-list-pre-data")
                if textarea and textarea.text.strip():
                    song_list = json.loads(textarea.text.strip())
                    songs = self._parse_song_list(song_list)
                    if songs:
                        logger.info(f"[多榜单] HTML 方式获取榜单 {chart_id} 的 {len(songs)} 首歌曲")
                        return songs
        except Exception as e:
            logger.warning(f"[多榜单] HTML 方式失败: {e}")

        return None

    def scrape_all_charts(self) -> Dict[str, List[SongData]]:
        """爬取所有支持的榜单"""
        results = {}
        for chart_name, chart_id in self.config.chart_ids.items():
            songs = self.scrape_chart(chart_id)
            if songs:
                results[chart_name] = songs
            else:
                # 不把热歌榜备用数据伪装成其他榜单；保留数据库中的上一份有效快照。
                logger.warning(f"[多榜单] 榜单 {chart_name} 本次爬取失败，跳过保存")

        return results

    def scrape(self) -> ScrapeResult:
        """主爬取调度方法"""
        # 策略一：API
        data = self.scrape_via_api()
        if data:
            return ScrapeResult(
                success=True,
                method="API实时接口",
                data=data,
                online=True,
            )

        # 策略二：HTML
        data = self.scrape_via_html()
        if data:
            return ScrapeResult(
                success=True,
                method="HTML页面解析",
                data=data,
                online=True,
            )

        # 策略三：备用数据
        data = self.get_fallback_data()
        return ScrapeResult(
            success=True,
            method="备用数据（在线爬取受限）",
            data=data,
            online=False,
        )
