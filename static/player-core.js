/**
 * GlobalPlayer v2 — 黑胶唱片迷你播放器 + 跨页面无缝播放
 * ============================================================
 * v2 新特性:
 *   - 黑胶唱片 UI：hover 展开进度环+控件，离开聚合为唱片
 *   - 可拖拽到屏幕任意位置（localStorage 记忆）
 *   - 保存音量 + 循环模式（单曲/列表/顺序）
 *   - IndexedDB 缓存音频 blob → 切页接近零延迟恢复
 *   - SVG 环形进度指示器
 *
 * 用法：
 *   GlobalPlayer.play({ title, artist, chart, mp3Url, songId, playlist, currentIndex })
 *   GlobalPlayer.pause() / resume() / stop() / next() / prev()
 *   GlobalPlayer.setVolume(0.5)
 *   GlobalPlayer.setRepeatMode('sequence'|'shuffle'|'one')
 */
(function () {
    'use strict';

    const STORAGE_KEY = '_gplayer_v2';
    const POSITION_SAVE_MS = 2000;
    const STATE_TTL = 7200000;
    const DB_NAME = 'GPlayerCache';
    const DB_VERSION = 1;
    const STORE_NAME = 'audioBlobs';

    // ═══════════════════════════════════════
    //  State
    // ═══════════════════════════════════════
    let audio = null;
    let state = {
        title: '', artist: '', chart: '',
        mp3Url: '', songId: '',
        playlist: [], currentIndex: -1,
        position: 0, isPlaying: false,
        volume: 0.8, repeatMode: 'sequence',  // 'sequence' | 'shuffle' | 'one'
        discX: null, discY: null,          // disc screen position (null = auto bottom-right)
        timestamp: 0
    };
    let positionTimer = null;
    let discEl = null;      // #_gp_disc
    let discRing = null;    // SVG progress ring
    let discIsDragging = false;
    let discDragStart = { x: 0, y: 0, elX: 0, elY: 0 };
    let discHoverTimer = null;
    let discExpanded = false;
    let shuffleHistory = [];
    let playbackRequestId = 0;
    let playbackFetchController = null;
    let navigationRequestId = 0;
    let playUrlFetchController = null;
    let streamRecoveryInFlight = false;
    let lastStreamErrorSrc = '';
    const streamFailedSongs = new Set();
    const unavailableSongs = new Map();
    const stableUnavailableReasons = new Set([
        'vip_required', 'purchase_required', 'copyright_unavailable', 'playback_unavailable'
    ]);

    function unavailableKey(song) {
        return `${song?.title || ''}\u0000${song?.artist || ''}`;
    }

    function notifyUnavailable(song, result) {
        window.dispatchEvent(new CustomEvent('globalplayer-unavailable', {
            detail: { song, result }
        }));
    }

    function abortError() {
        const error = new Error('Playback request superseded');
        error.name = 'AbortError';
        return error;
    }

    function invalidatePlaybackRequest() {
        playbackRequestId += 1;
        if (playbackFetchController) {
            playbackFetchController.abort();
            playbackFetchController = null;
        }
        return playbackRequestId;
    }

    function invalidateNavigationRequest() {
        navigationRequestId += 1;
        if (playUrlFetchController) {
            playUrlFetchController.abort();
            playUrlFetchController = null;
        }
        return navigationRequestId;
    }

    // ═══════════════════════════════════════
    //  IndexedDB — 音频缓存（消除切页卡顿）
    // ═══════════════════════════════════════
    function openDB() {
        return new Promise((resolve, reject) => {
            const req = indexedDB.open(DB_NAME, DB_VERSION);
            req.onupgradeneeded = () => {
                if (!req.result.objectStoreNames.contains(STORE_NAME)) {
                    req.result.createObjectStore(STORE_NAME);
                }
            };
            req.onsuccess = () => resolve(req.result);
            req.onerror = () => reject(req.error);
        });
    }

    async function cacheAudioBlob(url, blob) {
        try {
            const db = await openDB();
            const tx = db.transaction(STORE_NAME, 'readwrite');
            tx.objectStore(STORE_NAME).put(blob, url);
            await new Promise(r => { tx.oncomplete = r; });
            db.close();
        } catch (e) { /* ignore */ }
    }

    async function getCachedBlob(url) {
        try {
            const db = await openDB();
            const tx = db.transaction(STORE_NAME, 'readonly');
            const req = tx.objectStore(STORE_NAME).get(url);
            const blob = await new Promise((resolve, reject) => {
                req.onsuccess = () => resolve(req.result);
                req.onerror = () => reject(req.error);
            });
            db.close();
            return blob || null;
        } catch (e) { return null; }
    }

    async function fetchAndCacheAudio(proxyUrl, signal) {
        // 先查缓存
        const cached = await getCachedBlob(proxyUrl);
        if (signal?.aborted) throw abortError();
        if (cached) {
            return URL.createObjectURL(cached);
        }
        // 网络拉取
        const resp = await fetch(proxyUrl, { signal });
        if (!resp.ok) throw new Error('HTTP ' + resp.status);
        const blob = await resp.blob();
        if (signal?.aborted) throw abortError();
        // 异步缓存（不阻塞播放）
        cacheAudioBlob(proxyUrl, blob);
        return URL.createObjectURL(blob);
    }

    // ═══════════════════════════════════════
    //  State persistence
    // ═══════════════════════════════════════
    function saveState() {
        state.timestamp = Date.now();
        if (audio) state.position = audio.currentTime;
        try { localStorage.setItem(STORAGE_KEY, JSON.stringify(state)); } catch (e) { }
    }

    function normalizePlaybackMode(mode) {
        // Migrate persisted v2 values from the previous three-mode model.
        if (mode === 'one') return 'one';
        if (mode === 'shuffle') return 'shuffle';
        return 'sequence';
    }

    function loadState() {
        try {
            const raw = localStorage.getItem(STORAGE_KEY);
            if (!raw) return null;
            const s = JSON.parse(raw);
            if (Date.now() - s.timestamp > STATE_TTL) {
                localStorage.removeItem(STORAGE_KEY);
                return null;
            }
            s.repeatMode = normalizePlaybackMode(s.repeatMode);
            return s;
        } catch (e) { return null; }
    }

    function clearState() {
        invalidatePlaybackRequest();
        invalidateNavigationRequest();
        streamFailedSongs.clear();
        streamRecoveryInFlight = false;
        lastStreamErrorSrc = '';
        try { localStorage.removeItem(STORAGE_KEY); } catch (e) { }
        state = {
            title: '', artist: '', chart: '', mp3Url: '', songId: '',
            playlist: [], currentIndex: -1, position: 0,
            isPlaying: false, volume: 0.8, repeatMode: 'sequence',
            discX: null, discY: null, timestamp: 0
        };
        if (audio) { audio.pause(); audio.src = ''; }
        hideDisc();
        stopPositionTimer();
        dispatchState();
    }

    function dispatchState() {
        window.dispatchEvent(new CustomEvent('globalplayer-state', {
            detail: { ...state, audioElement: audio }
        }));
    }

    function startPositionTimer() {
        stopPositionTimer();
        positionTimer = setInterval(() => {
            if (audio && !audio.paused) {
                state.position = audio.currentTime;
                updateDiscRing();
                saveState();
            }
        }, POSITION_SAVE_MS);
    }

    function stopPositionTimer() {
        if (positionTimer) { clearInterval(positionTimer); positionTimer = null; }
    }

    // ═══════════════════════════════════════
    //  Audio element
    // ═══════════════════════════════════════
    function ensureAudio() {
        if (audio) return audio;
        audio = document.createElement('audio');
        audio.preload = 'auto';
        audio.volume = state.volume;
        audio.style.display = 'none';
        document.body.appendChild(audio);

        audio.addEventListener('loadedmetadata', () => updateDiscRing());
        audio.addEventListener('timeupdate', () => updateDiscRing());
        audio.addEventListener('play', () => {
            state.isPlaying = true;
            updateDiscPlayBtn();
            startPositionTimer();
            saveState();
            dispatchState();
        });
        audio.addEventListener('playing', () => {
            // 真正开始出声后，结束上一轮“坏流自动跳过”链路。
            streamFailedSongs.clear();
            lastStreamErrorSrc = '';
        });
        audio.addEventListener('pause', () => {
            state.isPlaying = false;
            updateDiscPlayBtn();
            stopPositionTimer();
            saveState();
            dispatchState();
        });
        audio.addEventListener('ended', () => {
            if (state.repeatMode === 'one') {
                audio.currentTime = 0;
                audio.play().catch(() => {});
            } else if (state.repeatMode === 'shuffle') {
                GlobalPlayer.next();
            } else {
                // Sequence playback stops after the final item.
                if (state.currentIndex >= state.playlist.length - 1) {
                    state.isPlaying = false;
                    updateDiscPlayBtn();
                    stopPositionTimer();
                    saveState();
                    dispatchState();
                } else {
                    GlobalPlayer.next();
                }
            }
        });
        audio.addEventListener('error', () => {
            const mediaErrorCode = audio.error?.code || 0;
            // MEDIA_ERR_ABORTED 通常由切歌/取消旧请求触发，不应当误跳下一首。
            if (mediaErrorCode === 1 || !state.title) return;
            const failedSrc = audio.currentSrc || audio.src || '';
            if (failedSrc && failedSrc === lastStreamErrorSrc) return;
            lastStreamErrorSrc = failedSrc;
            streamFailedSongs.add(unavailableKey(state));
            console.warn('[GlobalPlayer] 音频加载失败');
            state.isPlaying = false;
            updateDiscPlayBtn();
            stopPositionTimer();
            dispatchState();
            window.dispatchEvent(new CustomEvent('globalplayer-stream-error', {
                detail: { title: state.title, artist: state.artist, code: mediaErrorCode }
            }));

            if (streamRecoveryInFlight || state.playlist.length < 2 || state.currentIndex < 0) return;
            streamRecoveryInFlight = true;
            // 脱离 media error 回调栈后再切歌；失败集合会让 next 跳过本轮已坏的流，
            // 即便整张榜单都失败也只尝试一轮，不会无限循环。
            setTimeout(async () => {
                try {
                    await GlobalPlayer.next({ fromStreamError: true });
                } finally {
                    streamRecoveryInFlight = false;
                }
            }, 0);
        });
        return audio;
    }

    // ═══════════════════════════════════════
    //  黑胶唱片 UI — Disc widget
    // ═══════════════════════════════════════
    function fmtTime(sec) {
        if (isNaN(sec) || sec < 0 || sec === Infinity) return '00:00';
        const m = Math.floor(sec / 60);
        const s = Math.floor(sec % 60);
        return String(m).padStart(2, '0') + ':' + String(s).padStart(2, '0');
    }

    function buildDisc() {
        if (discEl) return;
        // Inject styles
        const style = document.createElement('style');
        style.textContent = /* css */ `
#_gp_disc {
    position: fixed; z-index: 9999;
    width: 72px; height: 72px;
    border-radius: 50%;
    cursor: grab;
    user-select: none;
    -webkit-user-select: none;
    transition: width 0.35s cubic-bezier(0.34,1.56,0.64,1),
                height 0.35s cubic-bezier(0.34,1.56,0.64,1),
                border-radius 0.35s cubic-bezier(0.34,1.56,0.64,1),
                box-shadow 0.35s ease;
    display: none;
    font-family: 'Microsoft YaHei','PingFang SC',-apple-system,sans-serif;
}
#_gp_disc.show { display: block; }
#_gp_disc.expanded {
    width: 200px; height: 200px;
    cursor: default;
    box-shadow: 0 8px 40px rgba(0,0,0,0.5), 0 0 0 1px rgba(255,255,255,0.06);
}
#_gp_disc.dragging {
    cursor: grabbing;
    transition: none !important;
}
/* ── 唱片盘面 ── */
#_gp_disc ._gp-face {
    position: absolute; inset: 4px;
    border-radius: 50%;
    background: linear-gradient(135deg, #1a1a2e 0%, #16213e 40%, #0f3460 100%);
    display: flex; align-items: center; justify-content: center;
    overflow: hidden;
}
#_gp_disc ._gp-face::before {
    content: '';
    position: absolute; inset: -20%;
    border-radius: 50%;
    background: conic-gradient(
        from 0deg,
        transparent 0deg, transparent 30deg, rgba(255,255,255,0.03) 30deg,
        rgba(255,255,255,0.03) 32deg, transparent 32deg, transparent 60deg,
        rgba(255,255,255,0.03) 60deg, rgba(255,255,255,0.03) 62deg, transparent 62deg,
        transparent 90deg, rgba(255,255,255,0.04) 90deg, rgba(255,255,255,0.04) 92deg, transparent 92deg,
        transparent 120deg, rgba(255,255,255,0.03) 120deg, rgba(255,255,255,0.03) 122deg, transparent 122deg,
        transparent 150deg, rgba(255,255,255,0.04) 150deg, rgba(255,255,255,0.04) 152deg, transparent 152deg,
        transparent 180deg, rgba(255,255,255,0.03) 180deg, rgba(255,255,255,0.03) 182deg, transparent 182deg,
        transparent 210deg, rgba(255,255,255,0.04) 210deg, rgba(255,255,255,0.04) 212deg, transparent 212deg,
        transparent 240deg, rgba(255,255,255,0.03) 240deg, rgba(255,255,255,0.03) 242deg, transparent 242deg,
        transparent 270deg, rgba(255,255,255,0.04) 270deg, rgba(255,255,255,0.04) 272deg, transparent 272deg,
        transparent 300deg, rgba(255,255,255,0.03) 300deg, rgba(255,255,255,0.03) 302deg, transparent 302deg,
        transparent 330deg, rgba(255,255,255,0.04) 330deg, rgba(255,255,255,0.04) 332deg, transparent 332deg,
        transparent 360deg
    );
    animation: _gpVinylSpin 20s linear infinite;
    pointer-events: none;
}
#_gp_disc.paused ._gp-face::before { animation-play-state: paused; }
@keyframes _gpVinylSpin { to { transform: rotate(360deg); } }
/* 中心标签 */
#_gp_disc ._gp-center {
    position: absolute; width: 28px; height: 28px; border-radius: 50%;
    background: linear-gradient(135deg, #ff6b6b, #ee5a24);
    z-index: 2; pointer-events: none;
    display: flex; align-items: center; justify-content: center;
    font-size: 12px; color: #fff;
}
/* 播放按钮（聚合态） */
#_gp_disc ._gp-collapsed-play {
    position: absolute; inset: 22px; z-index: 5;
    border-radius: 50%;
    background: rgba(0,0,0,0.5);
    border: none; color: #fff; font-size: 18px;
    cursor: pointer; display: flex; align-items: center; justify-content: center;
    opacity: 0; transition: opacity 0.2s;
}
#_gp_disc:hover ._gp-collapsed-play,
#_gp_disc.touch-active ._gp-collapsed-play { opacity: 1; }
#_gp_disc.expanded ._gp-collapsed-play { display: none; }

/* ── 展开态：SVG 进度环 ── */
#_gp_disc ._gp-ring-svg {
    position: absolute; inset: -8px; z-index: 1;
    pointer-events: none;
    opacity: 0; transition: opacity 0.3s;
}
#_gp_disc.expanded ._gp-ring-svg { opacity: 1; }
#_gp_disc ._gp-ring-bg {
    fill: none; stroke: rgba(255,255,255,0.08); stroke-width: 4;
}
#_gp_disc ._gp-ring-fg {
    fill: none; stroke: url(#_gpGrad); stroke-width: 4;
    stroke-linecap: round;
    transition: stroke-dashoffset 0.15s linear;
}

/* ── 展开态：控件面板 ── */
#_gp_disc ._gp-expanded-ui {
    position: absolute; inset: -60px -40px -60px -40px; z-index: 10;
    display: none; align-items: center; justify-content: center;
    pointer-events: none;
}
#_gp_disc.expanded ._gp-expanded-ui { display: flex; }
#_gp_disc ._gp-expanded-ui > * { pointer-events: auto; }
#_gp_disc ._gp-ectrls {
    display: flex; flex-direction: column; align-items: center; gap: 12px;
    position: absolute;
}

/* 歌曲信息 */
#_gp_disc ._gp-einfo {
    text-align: center; max-width: 180px;
    opacity: 0; transform: translateY(8px);
    transition: all 0.3s 0.1s;
}
#_gp_disc.expanded ._gp-einfo { opacity: 1; transform: translateY(0); }
#_gp_disc ._gp-etitle {
    font-size: 13px; font-weight: 700; color: #e6edf3;
    white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
}
#_gp_disc ._gp-eartist {
    font-size: 11px; color: rgba(255,255,255,0.5); margin-top: 2px;
}

/* 播放按钮行 */
#_gp_disc ._gp-ebtnrow {
    display: flex; align-items: center; gap: 16px;
    opacity: 0; transform: translateY(8px);
    transition: all 0.3s 0.2s;
}
#_gp_disc.expanded ._gp-ebtnrow { opacity: 1; transform: translateY(0); }
#_gp_disc ._gp-ebtn {
    width: 40px; height: 40px; border-radius: 50%;
    border: 1px solid rgba(255,255,255,0.12);
    background: rgba(255,255,255,0.06);
    color: #e6edf3; font-size: 15px; cursor: pointer;
    display: flex; align-items: center; justify-content: center;
    transition: all 0.2s;
}
#_gp_disc ._gp-ebtn:hover { background: rgba(255,255,255,0.12); }
#_gp_disc ._gp-ebtn._gp-play-main {
    width: 50px; height: 50px;
    background: linear-gradient(135deg, #ff6b6b, #ee5a24);
    border: none; color: #fff; font-size: 20px;
    box-shadow: 0 2px 16px rgba(255,107,107,0.35);
}
#_gp_disc ._gp-ebtn._gp-play-main:hover { transform: scale(1.08); }

/* 底部栏：时间 + 音量 + 循环 */
#_gp_disc ._gp-ebottom {
    display: flex; align-items: center; gap: 10px;
    font-size: 10px; color: rgba(255,255,255,0.45);
    font-variant-numeric: tabular-nums;
    opacity: 0; transform: translateY(8px);
    transition: all 0.3s 0.3s;
}
#_gp_disc.expanded ._gp-ebottom { opacity: 1; transform: translateY(0); }
#_gp_disc ._gp-evolume {
    display: flex; align-items: center; gap: 4px;
}
#_gp_disc ._gp-evol-slider {
    width: 50px; height: 3px; border-radius: 3px;
    background: rgba(255,255,255,0.1); cursor: pointer;
    -webkit-appearance: none; appearance: none; outline: none;
}
#_gp_disc ._gp-evol-slider::-webkit-slider-thumb {
    -webkit-appearance: none; width: 10px; height: 10px;
    border-radius: 50%; background: #ff6b6b; cursor: pointer;
}
#_gp_disc ._gp-erepeat {
    width: 28px; height: 28px; border-radius: 50%;
    border: 1px solid rgba(255,255,255,0.1);
    background: transparent; color: rgba(255,255,255,0.45);
    font-size: 12px; cursor: pointer; display: flex;
    align-items: center; justify-content: center;
    transition: all 0.2s;
}
#_gp_disc ._gp-erepeat:hover { background: rgba(255,255,255,0.08); }
#_gp_disc ._gp-erepeat.active { color: #ff6b6b; border-color: rgba(255,107,107,0.4); }

/* 关闭按钮 */
#_gp_disc ._gp-eclose {
    position: absolute; top: -52px; right: -36px;
    width: 24px; height: 24px; border-radius: 50%;
    border: none; background: rgba(255,255,255,0.06);
    color: rgba(255,255,255,0.4); font-size: 12px; cursor: pointer;
    display: none; align-items: center; justify-content: center;
    transition: all 0.2s;
}
#_gp_disc.expanded ._gp-eclose { display: flex; }
#_gp_disc ._gp-eclose:hover { background: rgba(231,76,60,0.3); color: #e74c3c; }

@media (max-width: 640px) {
    #_gp_disc.expanded { width: 180px; height: 180px; }
    #_gp_disc ._gp-expanded-ui { inset: -50px -30px -50px -30px; }
}
        `;
        document.head.appendChild(style);

        // SVG gradient defs (injected once into body)
        const svgDefs = document.createElement('div');
        svgDefs.style.cssText = 'position:absolute;width:0;height:0;overflow:hidden;';
        svgDefs.innerHTML = `
<svg xmlns="http://www.w3.org/2000/svg">
    <defs>
        <linearGradient id="_gpGrad" x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" stop-color="#ff6b6b"/>
            <stop offset="100%" stop-color="#ee5a24"/>
        </linearGradient>
    </defs>
</svg>`;
        document.body.appendChild(svgDefs);

        // Build disc DOM
        discEl = document.createElement('div');
        discEl.id = '_gp_disc';
        discEl.innerHTML = /* html */ `
<div class="_gp-face"></div>
<div class="_gp-center">🎵</div>
<button class="_gp-collapsed-play" title="播放/暂停">▶</button>
<svg class="_gp-ring-svg" viewBox="0 0 220 220">
    <circle class="_gp-ring-bg" cx="110" cy="110" r="104"/>
    <circle class="_gp-ring-fg" cx="110" cy="110" r="104"
        stroke-dasharray="653.45" stroke-dashoffset="653.45"/>
</svg>
<div class="_gp-expanded-ui">
    <div class="_gp-ectrls">
        <div class="_gp-einfo">
            <div class="_gp-etitle">—</div>
            <div class="_gp-eartist">—</div>
        </div>
        <div class="_gp-ebtnrow">
            <button class="_gp-ebtn" data-action="prev" title="上一首">⏮</button>
            <button class="_gp-ebtn _gp-play-main" data-action="play" title="播放/暂停">▶️</button>
            <button class="_gp-ebtn" data-action="next" title="下一首">⏭</button>
        </div>
        <div class="_gp-ebottom">
            <span class="_gp-etime">00:00 / 00:00</span>
            <div class="_gp-evolume">
                <span>🔊</span>
                <input type="range" class="_gp-evol-slider" min="0" max="100" value="80">
            </div>
            <button class="_gp-erepeat" data-action="repeat" title="循环模式">🔁</button>
        </div>
    </div>
    <button class="_gp-eclose" data-action="close" title="关闭">✕</button>
</div>`;
        document.body.appendChild(discEl);

        // Cache sub-elements
        discRing = discEl.querySelector('._gp-ring-fg');
        const collapsedPlay = discEl.querySelector('._gp-collapsed-play');
        const playMain = discEl.querySelector('._gp-ebtn._gp-play-main');
        const volSlider = discEl.querySelector('._gp-evol-slider');
        const repeatBtn = discEl.querySelector('._gp-erepeat');
        const timeEl = discEl.querySelector('._gp-etime');
        const titleEl = discEl.querySelector('._gp-etitle');
        const artistEl = discEl.querySelector('._gp-eartist');

        // ── Event: hover expand / collapse ──
        discEl.addEventListener('mouseenter', () => {
            clearTimeout(discHoverTimer);
            expandDisc();
        });
        discEl.addEventListener('mouseleave', () => {
            if (discIsDragging) return;
            discHoverTimer = setTimeout(collapseDisc, 400);
        });
        // Touch support
        discEl.addEventListener('touchstart', (e) => {
            if (e.target.closest('button') || e.target.closest('input')) return;
            discEl.classList.add('touch-active');
            clearTimeout(discHoverTimer);
            expandDisc();
        }, { passive: true });
        document.addEventListener('touchend', (e) => {
            if (!discEl.contains(e.target)) {
                discEl.classList.remove('touch-active');
                discHoverTimer = setTimeout(collapseDisc, 800);
            }
        });

        // ──  Collapsed play button ──
        collapsedPlay.addEventListener('click', (e) => {
            e.stopPropagation();
            if (state.isPlaying) GlobalPlayer.pause();
            else GlobalPlayer.resume();
        });

        // ── Expanded controls ──
        playMain.addEventListener('click', (e) => {
            e.stopPropagation();
            if (state.isPlaying) GlobalPlayer.pause();
            else GlobalPlayer.resume();
        });
        discEl.querySelector('[data-action="prev"]').addEventListener('click', (e) => {
            e.stopPropagation(); GlobalPlayer.prev();
        });
        discEl.querySelector('[data-action="next"]').addEventListener('click', (e) => {
            e.stopPropagation(); GlobalPlayer.next();
        });
        repeatBtn.addEventListener('click', (e) => {
            e.stopPropagation();
            const modes = ['sequence', 'shuffle', 'one'];
            const idx = modes.indexOf(state.repeatMode);
            const nextMode = modes[(idx + 1) % modes.length];
            GlobalPlayer.setRepeatMode(nextMode);
        });
        volSlider.addEventListener('input', (e) => {
            e.stopPropagation();
            GlobalPlayer.setVolume(parseInt(volSlider.value) / 100);
        });
        volSlider.addEventListener('click', (e) => e.stopPropagation());
        discEl.querySelector('[data-action="close"]').addEventListener('click', (e) => {
            e.stopPropagation(); GlobalPlayer.stop();
        });

        // ── Drag ──
        discEl.addEventListener('mousedown', (e) => {
            if (e.target.closest('button') || e.target.closest('input')) return;
            e.preventDefault();
            discIsDragging = true;
            const rect = discEl.getBoundingClientRect();
            discDragStart = { x: e.clientX, y: e.clientY, elX: rect.left, elY: rect.top };
            discEl.classList.add('dragging');
        });
        window.addEventListener('mousemove', (e) => {
            if (!discIsDragging) return;
            const dx = e.clientX - discDragStart.x;
            const dy = e.clientY - discDragStart.y;
            const newX = Math.max(0, Math.min(window.innerWidth - discEl.offsetWidth, discDragStart.elX + dx));
            const newY = Math.max(0, Math.min(window.innerHeight - discEl.offsetHeight, discDragStart.elY + dy));
            discEl.style.left = newX + 'px';
            discEl.style.top = newY + 'px';
            discEl.style.right = 'auto';
            discEl.style.bottom = 'auto';
        });
        window.addEventListener('mouseup', () => {
            if (discIsDragging) {
                discIsDragging = false;
                discEl.classList.remove('dragging');
                const rect = discEl.getBoundingClientRect();
                state.discX = rect.left;
                state.discY = rect.top;
                saveState();
            }
        });
        // Touch drag
        discEl.addEventListener('touchstart', (e) => {
            if (e.target.closest('button') || e.target.closest('input')) return;
            const touch = e.touches[0];
            discIsDragging = true;
            const rect = discEl.getBoundingClientRect();
            discDragStart = { x: touch.clientX, y: touch.clientY, elX: rect.left, elY: rect.top };
            discEl.classList.add('dragging');
        }, { passive: true });
        window.addEventListener('touchmove', (e) => {
            if (!discIsDragging) return;
            const touch = e.touches[0];
            const dx = touch.clientX - discDragStart.x;
            const dy = touch.clientY - discDragStart.y;
            const newX = Math.max(0, Math.min(window.innerWidth - discEl.offsetWidth, discDragStart.elX + dx));
            const newY = Math.max(0, Math.min(window.innerHeight - discEl.offsetHeight, discDragStart.elY + dy));
            discEl.style.left = newX + 'px';
            discEl.style.top = newY + 'px';
            discEl.style.right = 'auto';
            discEl.style.bottom = 'auto';
        }, { passive: true });
        window.addEventListener('touchend', () => {
            if (discIsDragging) {
                discIsDragging = false;
                discEl.classList.remove('dragging');
                const rect = discEl.getBoundingClientRect();
                state.discX = rect.left;
                state.discY = rect.top;
                saveState();
            }
        });

        // ── Update helpers (closure) ──
        discEl._updateInfo = () => {
            titleEl.textContent = state.title || '—';
            artistEl.textContent = state.artist || '—';
        };
        discEl._updateTime = () => {
            if (audio && !isNaN(audio.duration)) {
                timeEl.textContent = fmtTime(audio.currentTime) + ' / ' + fmtTime(audio.duration);
            }
        };
        discEl._updateVol = () => { volSlider.value = Math.round(state.volume * 100); };
        discEl._updateRepeat = () => {
            const icons = { sequence: '➡', shuffle: '⤨', one: 'ↂ' };
            const labels = { sequence: '顺序播放', shuffle: '随机播放', one: '单曲循环' };
            repeatBtn.textContent = icons[state.repeatMode] || '➡';
            repeatBtn.title = labels[state.repeatMode] || '顺序播放';
            repeatBtn.classList.toggle('active', state.repeatMode !== 'sequence');
        };
        discEl._updatePlayBtn = () => {
            const icon = state.isPlaying ? '⏸' : '▶️';
            collapsedPlay.textContent = state.isPlaying ? '⏸' : '▶';
            playMain.textContent = icon;
            discEl.classList.toggle('paused', !state.isPlaying);
        };
    }

    function expandDisc() {
        if (!discEl || discExpanded) return;
        discExpanded = true;
        discEl.classList.add('expanded');
    }

    function collapseDisc() {
        if (!discEl || !discExpanded) return;
        if (discIsDragging) return;
        discExpanded = false;
        discEl.classList.remove('expanded');
    }

    function showDisc() {
        if (window.location.pathname === '/player') return; // 听歌页不显示迷你唱片
        buildDisc();
        discEl.classList.add('show');
        discEl._updateInfo();
        discEl._updatePlayBtn();
        discEl._updateVol();
        discEl._updateRepeat();
        updateDiscRing();
        positionDisc();
    }

    function hideDisc() {
        if (discEl) discEl.classList.remove('show');
    }

    function positionDisc() {
        if (!discEl) return;
        if (state.discX !== null && state.discY !== null) {
            discEl.style.left = state.discX + 'px';
            discEl.style.top = state.discY + 'px';
            discEl.style.right = 'auto';
            discEl.style.bottom = 'auto';
        } else {
            // Default: bottom-right corner
            discEl.style.left = 'auto';
            discEl.style.top = 'auto';
            discEl.style.right = '20px';
            discEl.style.bottom = '20px';
        }
    }

    function updateDiscRing() {
        if (!discRing || !audio) return;
        const dur = audio.duration;
        if (isNaN(dur) || dur <= 0) {
            discRing.style.strokeDashoffset = '653.45';
            return;
        }
        const pct = audio.currentTime / dur;
        discRing.style.strokeDashoffset = (653.45 * (1 - pct)).toFixed(2);
        if (discEl && discEl._updateTime) discEl._updateTime();
    }

    function updateDiscPlayBtn() {
        if (discEl && discEl._updatePlayBtn) discEl._updatePlayBtn();
    }

    // ═══════════════════════════════════════
    //  Internal: switch to a song in playlist (self-contained)
    // ═══════════════════════════════════════
    async function _switchToSong(song, idx, requestId, options = {}) {
        // 自包含：自己获取 mp3 URL 并播放（不依赖外部 listener）
        // ⚠️ 不要在这里改 state.title/artist！否则 play() 里的 isNewSong 永远是 false
        const key = unavailableKey(song);
        if (requestId !== navigationRequestId) return false;
        if (options.fromStreamError && streamFailedSongs.has(key)) return false;
        if (unavailableSongs.has(key)) {
            notifyUnavailable(song, unavailableSongs.get(key));
            return false;
        }
        if (playUrlFetchController) playUrlFetchController.abort();
        const controller = new AbortController();
        playUrlFetchController = controller;
        try {
            const resp = await fetch('/api/song/play_url', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                signal: controller.signal,
                body: JSON.stringify({
                    title: song.title,
                    artist: song.artist,
                    song_id: song.song_id ?? null,
                    fee: song.fee ?? null
                })
            });
            if (requestId !== navigationRequestId || controller.signal.aborted) return false;
            if (!resp.ok) throw new Error('HTTP ' + resp.status);
            const result = await resp.json();
            if (requestId !== navigationRequestId || controller.signal.aborted) return false;
            if (result.success) {
                unavailableSongs.delete(key);
                const started = await GlobalPlayer.play({
                    title: song.title,
                    artist: song.artist,
                    chart: song.chart || state.chart,
                    mp3Url: result.mp3_url,
                    songId: result.song_id || '',
                    playlist: state.playlist,
                    currentIndex: idx
                }, { navigationId: requestId, fromStreamError: options.fromStreamError });
                return started !== false;
            } else {
                if (stableUnavailableReasons.has(result.reason)) unavailableSongs.set(key, result);
                notifyUnavailable(song, result);
                console.warn('[GlobalPlayer] 切歌失败:', result.error || result.reason || '无法获取播放链接');
                return false;
            }
        } catch (e) {
            if (e.name === 'AbortError' || requestId !== navigationRequestId) return false;
            console.warn('[GlobalPlayer] 切歌网络错误:', e.message);
            notifyUnavailable(song, { reason: 'network_error', error: '切换歌曲时网络异常' });
            return false;
        } finally {
            if (playUrlFetchController === controller) playUrlFetchController = null;
        }
    }

    // ═══════════════════════════════════════
    //  Public API
    // ═══════════════════════════════════════
    window.GlobalPlayer = {
        async play(song, internalOptions = {}) {
            if (internalOptions.navigationId === undefined) {
                invalidateNavigationRequest();
            } else if (internalOptions.navigationId !== navigationRequestId) {
                return false;
            }
            if (!internalOptions.fromStreamError) {
                streamFailedSongs.clear();
                lastStreamErrorSrc = '';
            }
            const requestId = invalidatePlaybackRequest();
            const a = ensureAudio();
            const isNewSong = state.title !== song.title || state.artist !== song.artist;
            if (isNewSong && !a.paused) a.pause();

            state.title = song.title || '';
            state.artist = song.artist || '';
            state.chart = song.chart || '';
            state.mp3Url = song.mp3Url || '';
            state.songId = song.songId || '';
            if (song.playlist) state.playlist = song.playlist;
            if (song.currentIndex !== undefined) state.currentIndex = song.currentIndex;
            state.position = 0;
            state.isPlaying = true;

            if ((isNewSong || !a.src) && song.mp3Url) {
                const proxyUrl = '/api/song/stream?url=' + encodeURIComponent(song.mp3Url) + '&song_id=' + (song.songId || '');
                const controller = new AbortController();
                playbackFetchController = controller;
                try {
                    const blobUrl = await fetchAndCacheAudio(proxyUrl, controller.signal);
                    if (requestId !== playbackRequestId || controller.signal.aborted) {
                        URL.revokeObjectURL(blobUrl);
                        return false;
                    }
                    a.src = blobUrl;
                    lastStreamErrorSrc = '';
                } catch (err) {
                    if (err.name === 'AbortError' || requestId !== playbackRequestId) return false;
                    // Fallback: 直接设置 proxy URL（浏览器会自己缓存）
                    a.src = proxyUrl;
                    lastStreamErrorSrc = '';
                } finally {
                    if (playbackFetchController === controller) playbackFetchController = null;
                }
            }

            if (requestId !== playbackRequestId) return false;

            a.volume = state.volume;
            saveState();
            showDisc();
            if (discEl) { discEl._updateInfo(); discEl._updatePlayBtn(); }
            dispatchState();

            a.play().catch(err => {
                if (requestId !== playbackRequestId) return;
                console.warn('[GlobalPlayer] 自动播放被阻止:', err.message);
                state.isPlaying = false;
                updateDiscPlayBtn();
                saveState();
                dispatchState();
            });
            return true;
        },

        pause() {
            invalidatePlaybackRequest();
            invalidateNavigationRequest();
            state.isPlaying = false;
            if (audio) audio.pause();
            updateDiscPlayBtn();
            stopPositionTimer();
            saveState();
            dispatchState();
        },

        resume() {
            if (!state.title) return;
            invalidateNavigationRequest();
            const requestId = invalidatePlaybackRequest();
            state.isPlaying = true;
            const a = ensureAudio();
            if (!a.src && state.mp3Url) {
                const proxyUrl = '/api/song/stream?url=' + encodeURIComponent(state.mp3Url) + '&song_id=' + (state.songId || '');
                // 尝试从缓存恢复
                getCachedBlob(proxyUrl).then(blob => {
                    if (requestId !== playbackRequestId) return;
                    if (blob) a.src = URL.createObjectURL(blob);
                    else a.src = proxyUrl;
                    lastStreamErrorSrc = '';
                    a.currentTime = state.position || 0;
                    showDisc();
                    updateDiscPlayBtn();
                    a.play().catch(() => {
                        if (requestId !== playbackRequestId) return;
                        state.isPlaying = false;
                        updateDiscPlayBtn();
                        saveState();
                    });
                });
            } else if (!a.src) {
                // 没有音频源，无法恢复播放
                state.isPlaying = false;
                updateDiscPlayBtn();
                saveState();
                dispatchState();
            } else {
                if (a.currentTime < 0.1 && state.position > 0.1) {
                    a.currentTime = state.position;
                }
                showDisc();
                updateDiscPlayBtn();
                a.play().catch(err => {
                    if (requestId !== playbackRequestId) return;
                    console.warn('[GlobalPlayer] 恢复播放失败:', err.message);
                    state.isPlaying = false;
                    updateDiscPlayBtn();
                    saveState();
                });
            }
        },

        stop() { clearState(); },

        async next(options = {}) {
            if (!state.playlist.length || state.currentIndex < 0) return false;
            if (state.playlist.length === 1) return false;
            const requestId = invalidateNavigationRequest();
            invalidatePlaybackRequest();
            if (!options.fromStreamError) {
                streamFailedSongs.clear();
                lastStreamErrorSrc = '';
            }
            const candidates = [];
            if (state.repeatMode === 'shuffle' && state.playlist.length > 1) {
                for (let idx = 0; idx < state.playlist.length; idx++) {
                    if (idx !== state.currentIndex) candidates.push(idx);
                }
                for (let i = candidates.length - 1; i > 0; i--) {
                    const j = Math.floor(Math.random() * (i + 1));
                    [candidates[i], candidates[j]] = [candidates[j], candidates[i]];
                }
            } else {
                for (let step = 1; step < state.playlist.length; step++) {
                    candidates.push((state.currentIndex + step) % state.playlist.length);
                }
            }
            const previousIndex = state.currentIndex;
            for (const idx of candidates) {
                if (requestId !== navigationRequestId) return false;
                const song = state.playlist[idx];
                if (song && await _switchToSong(song, idx, requestId, options)) {
                    if (requestId !== navigationRequestId) return false;
                    if (state.repeatMode === 'shuffle' && !options.fromStreamError) {
                        shuffleHistory.push(previousIndex);
                    }
                    return true;
                }
            }
            return false;
        },

        async prev() {
            if (!state.playlist.length || state.currentIndex < 0) return false;
            if (state.playlist.length === 1) return false;
            const requestId = invalidateNavigationRequest();
            invalidatePlaybackRequest();
            streamFailedSongs.clear();
            lastStreamErrorSrc = '';
            if (state.repeatMode === 'shuffle') {
                // 历史记录是栈：只弹出实际尝试的项。成功返回后更早的历史仍保留，
                // 因此可以连续多次“上一首”逐级返回。
                while (shuffleHistory.length) {
                    if (requestId !== navigationRequestId) return false;
                    const idx = shuffleHistory.pop();
                    if (idx === state.currentIndex || idx < 0 || idx >= state.playlist.length) continue;
                    const song = state.playlist[idx];
                    if (song && await _switchToSong(song, idx, requestId)) return true;
                }
                const candidates = [];
                for (let idx = 0; idx < state.playlist.length; idx++) {
                    if (idx !== state.currentIndex) candidates.push(idx);
                }
                for (let i = candidates.length - 1; i > 0; i--) {
                    const j = Math.floor(Math.random() * (i + 1));
                    [candidates[i], candidates[j]] = [candidates[j], candidates[i]];
                }
                for (const idx of candidates) {
                    if (requestId !== navigationRequestId) return false;
                    const song = state.playlist[idx];
                    if (song && await _switchToSong(song, idx, requestId)) return true;
                }
                return false;
            }

            const candidates = [];
            for (let step = 1; step < state.playlist.length; step++) {
                candidates.push((state.currentIndex - step + state.playlist.length) % state.playlist.length);
            }
            for (const idx of candidates) {
                if (requestId !== navigationRequestId) return false;
                const song = state.playlist[idx];
                if (song && await _switchToSong(song, idx, requestId)) return true;
            }
            return false;
        },

        markUnavailable(song, result = {}) {
            if (stableUnavailableReasons.has(result.reason)) {
                unavailableSongs.set(unavailableKey(song), result);
            }
        },

        setVolume(v) {
            state.volume = Math.max(0, Math.min(1, v));
            if (audio) audio.volume = state.volume;
            if (discEl && discEl._updateVol) discEl._updateVol();
            saveState();
        },

        setRepeatMode(mode) {
            state.repeatMode = normalizePlaybackMode(mode);
            shuffleHistory = [];
            if (discEl && discEl._updateRepeat) discEl._updateRepeat();
            saveState();
            dispatchState();
        },

        getState() { return { ...state, audioElement: audio }; },

        isActive() { return !!state.title; },

        refreshUI() {
            if (state.title) {
                showDisc();
                if (discEl) {
                    discEl._updateInfo();
                    discEl._updatePlayBtn();
                    discEl._updateVol();
                    discEl._updateRepeat();
                }
            }
        }
    };

    // ═══════════════════════════════════════
    //  Init — 页面加载时恢复（无 race condition）
    // ═══════════════════════════════════════
    async function init() {
        const saved = loadState();
        if (!saved || !saved.title || !saved.mp3Url) return;
        state = saved;
        const requestId = invalidatePlaybackRequest();

        if (window.location.pathname !== '/player') {
            showDisc();
            if (discEl) {
                discEl._updateInfo();
                discEl._updatePlayBtn();
                discEl._updateVol();
                discEl._updateRepeat();
            }
        }

        const a = ensureAudio();
        const proxyUrl = '/api/song/stream?url=' + encodeURIComponent(state.mp3Url) + '&song_id=' + (state.songId || '');

        // 单一 src 设置路径：先查 IndexedDB，有就用 blob；没有就用 proxyUrl
        const cachedBlob = await getCachedBlob(proxyUrl);
        if (requestId !== playbackRequestId) return;
        if (cachedBlob) {
            a.src = URL.createObjectURL(cachedBlob);
        } else {
            a.src = proxyUrl;
        }
        lastStreamErrorSrc = '';
        a.volume = state.volume;

        // 等 canplay 后再 seek（比 loadedmetadata 更可靠）
        const doSeekAndResume = () => {
            a.removeEventListener('canplay', doSeekAndResume);
            if (requestId !== playbackRequestId) return;
            if (state.position > 0.5) {
                a.currentTime = state.position;
            }
            if (state.isPlaying) {
                a.play().then(() => {
                    updateDiscRing();
                }).catch(() => {
                    state.isPlaying = false;
                    updateDiscPlayBtn();
                    saveState();
                });
            }
            dispatchState();
        };
        a.addEventListener('canplay', doSeekAndResume);

        // 兜底：如果 canplay 迟迟不触发（如已缓存），手动触发
        if (a.readyState >= 2) {
            doSeekAndResume();
        }
    }

    // ═══════════════════════════════════════
    //  Events — 可靠的切页/隐藏状态保存
    // ═══════════════════════════════════════
    function persistPosition() {
        if (audio && state.title) {
            state.position = audio.currentTime || state.position;
            saveState();
        }
    }

    // pagehide 比 beforeunload 更可靠（bfcache 兼容）
    window.addEventListener('pagehide', persistPosition);
    window.addEventListener('beforeunload', persistPosition);
    // visibilitychange 兜底：切 tab / 最小化也保存
    document.addEventListener('visibilitychange', () => {
        if (document.hidden) persistPosition();
    });

    // 全局键盘快捷键
    document.addEventListener('keydown', (e) => {
        const tag = e.target.tagName;
        if (tag === 'INPUT' || tag === 'TEXTAREA' || tag === 'SELECT') return;
        if (!state.title) return;
        switch (e.code) {
            case 'Space':
                e.preventDefault();
                if (state.isPlaying) GlobalPlayer.pause();
                else GlobalPlayer.resume();
                break;
            case 'ArrowRight':
                e.preventDefault();
                if (audio) audio.currentTime = Math.min(audio.duration || 0, audio.currentTime + 5);
                break;
            case 'ArrowLeft':
                e.preventDefault();
                if (audio) audio.currentTime = Math.max(0, audio.currentTime - 5);
                break;
        }
    });

    // 启动
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})();
