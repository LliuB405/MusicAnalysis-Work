/**
 * SongDetailModal — 歌曲详情弹窗
 * ============================================================
 * 用法：
 *   SongDetailModal.open(song)  // song: { title, artist, chart?, rank? }
 *   SongDetailModal.close()
 */
(function () {
    'use strict';
    let modalEl = null;
    let backdropEl = null;

    function build() {
        if (modalEl) return;
        // Inject styles
        const style = document.createElement('style');
        style.textContent = `
.sdm-backdrop {
    position: fixed; inset: 0; z-index: 10000;
    background: rgba(0,0,0,0.6);
    backdrop-filter: blur(8px);
    -webkit-backdrop-filter: blur(8px);
    opacity: 0; pointer-events: none;
    transition: opacity 0.25s ease;
    display: flex; align-items: center; justify-content: center;
    padding: 20px;
}
.sdm-backdrop.show { opacity: 1; pointer-events: auto; }
.sdm-modal {
    width: 100%; max-width: 480px;
    background: var(--bg-1, #0b0d13);
    border: 1px solid var(--glass-border, rgba(255,255,255,0.1));
    border-radius: 20px;
    box-shadow: 0 24px 80px rgba(0,0,0,0.5);
    overflow: hidden;
    transform: scale(0.92) translateY(20px);
    transition: transform 0.3s cubic-bezier(0.34,1.56,0.64,1);
    position: relative;
}
.sdm-backdrop.show .sdm-modal { transform: scale(1) translateY(0); }
.sdm-cover {
    width: 100%; aspect-ratio: 16/9;
    background: linear-gradient(135deg, #1a1a2e 0%, #16213e 40%, #0f3460 100%);
    position: relative; overflow: hidden;
    display: flex; align-items: center; justify-content: center;
}
.sdm-cover::before {
    content: '';
    position: absolute; inset: 0;
    background: radial-gradient(circle at 30% 30%, rgba(255,107,107,0.3), transparent 50%),
                radial-gradient(circle at 70% 70%, rgba(124,92,255,0.3), transparent 50%);
}
.sdm-cover-disc {
    width: 120px; height: 120px; border-radius: 50%;
    background: linear-gradient(135deg, #2a2a3e, #1a1a2e);
    box-shadow: 0 8px 32px rgba(0,0,0,0.4);
    position: relative; z-index: 1;
    animation: sdmSpin 8s linear infinite paused;
}
.sdm-cover-disc.playing { animation-play-state: running; }
.sdm-cover-disc::before {
    content: '';
    position: absolute; inset: 8px;
    border-radius: 50%;
    background: conic-gradient(from 0deg, #1a1a2e, #2a2a3e, #1a1a2e, #2a2a3e, #1a1a2e);
}
.sdm-cover-disc::after {
    content: '♪';
    position: absolute; top: 50%; left: 50%;
    transform: translate(-50%,-50%);
    width: 32px; height: 32px;
    background: linear-gradient(135deg, #ff6b6b, #ee5a24);
    border-radius: 50%;
    display: flex; align-items: center; justify-content: center;
    color: #fff; font-size: 16px;
}
@keyframes sdmSpin { to { transform: rotate(360deg); } }
.sdm-rank-badge {
    position: absolute; top: 16px; left: 16px;
    padding: 6px 14px; border-radius: 14px;
    background: rgba(255,255,255,0.15);
    backdrop-filter: blur(10px);
    font-size: 12px; font-weight: 700; color: #fff;
    letter-spacing: 0.05em;
    z-index: 2;
}
.sdm-chart-badge {
    position: absolute; top: 16px; right: 16px;
    padding: 6px 14px; border-radius: 14px;
    background: rgba(124,92,255,0.3);
    backdrop-filter: blur(10px);
    font-size: 12px; font-weight: 600; color: #fff;
    z-index: 2;
}
.sdm-body { padding: 22px 24px; }
.sdm-title {
    font-size: 20px; font-weight: 700; color: var(--text-1, #e6edf3);
    margin-bottom: 6px; line-height: 1.3;
    overflow: hidden; text-overflow: ellipsis;
}
.sdm-artist {
    font-size: 14px; color: var(--text-3, #8b8f9b);
    margin-bottom: 18px;
}
.sdm-actions {
    display: flex; gap: 10px; margin-bottom: 18px;
}
.sdm-btn {
    flex: 1; padding: 10px;
    border-radius: 12px; border: none;
    font-size: 13px; font-weight: 600; cursor: pointer;
    display: flex; align-items: center; justify-content: center; gap: 6px;
    transition: all 0.2s;
    font-family: inherit;
}
.sdm-btn.primary {
    background: linear-gradient(135deg, #ff6b6b, #ee5a24);
    color: #fff;
    box-shadow: 0 4px 16px rgba(255,107,107,0.3);
}
.sdm-btn.primary:hover { transform: translateY(-1px); box-shadow: 0 6px 20px rgba(255,107,107,0.45); }
.sdm-btn.ghost {
    background: var(--glass-2, rgba(255,255,255,0.06));
    color: var(--text-2, #c2c5d0);
    border: 1px solid var(--glass-border, rgba(255,255,255,0.08));
}
.sdm-btn.ghost:hover { background: var(--glass-3, rgba(255,255,255,0.1)); }
.sdm-section {
    border-top: 1px solid var(--glass-border, rgba(255,255,255,0.08));
    padding-top: 16px; margin-top: 4px;
}
.sdm-section-title {
    font-size: 11px; font-weight: 600; color: var(--text-4, #565a66);
    text-transform: uppercase; letter-spacing: 0.1em;
    margin-bottom: 10px;
}
.sdm-lyric {
    max-height: 200px; overflow-y: auto;
    font-size: 13px; line-height: 1.7;
    color: var(--text-2, #c2c5d0);
    padding: 8px 0;
    white-space: pre-wrap;
    word-break: break-word;
}
.sdm-lyric .lyric-line {
    display: block; padding: 2px 6px; border-radius: 4px;
    transition: all 0.2s;
}
.sdm-lyric .lyric-line.active {
    background: rgba(255,107,107,0.15);
    color: #ff6b6b; font-weight: 600;
    transform: translateX(4px);
}
.sdm-lyric .lyric-time { display: none; }
.sdm-lyric-empty {
    text-align: center; color: var(--text-4, #565a66);
    font-size: 12px; padding: 20px 0;
}
.sdm-loading {
    text-align: center; color: var(--text-3, #8b8f9b);
    font-size: 12px; padding: 16px 0;
}
.sdm-loading::after {
    content: '...';
    display: inline-block;
    animation: sdmDots 1.4s steps(4) infinite;
}
@keyframes sdmDots {
    0%   { content: ''; }
    25%  { content: '.'; }
    50%  { content: '..'; }
    75%  { content: '...'; }
}
.sdm-trend-list {
    max-height: 200px; overflow-y: auto;
    font-size: 12px;
    color: var(--text-2, #c2c5d0);
}
.sdm-trend-row {
    display: flex; justify-content: space-between;
    padding: 6px 0;
    border-bottom: 1px dashed var(--glass-border, rgba(255,255,255,0.06));
}
.sdm-trend-row:last-child { border-bottom: none; }
.sdm-trend-time { color: var(--text-4, #565a66); font-family: var(--font-mono, monospace); font-size: 11px; }
.sdm-trend-rank { color: var(--brand-2, #00d4ff); font-weight: 700; }
.sdm-trend-empty {
    text-align: center; color: var(--text-4, #565a66);
    font-size: 12px; padding: 16px 0;
}
.sdm-close {
    position: absolute; top: 12px; right: 12px;
    width: 32px; height: 32px; border-radius: 50%;
    border: none; background: rgba(0,0,0,0.4);
    color: #fff; font-size: 14px; cursor: pointer;
    z-index: 3;
    display: flex; align-items: center; justify-content: center;
    transition: background 0.2s;
}
.sdm-close:hover { background: rgba(0,0,0,0.7); }
        `;
        document.head.appendChild(style);

        backdropEl = document.createElement('div');
        backdropEl.className = 'sdm-backdrop';
        backdropEl.innerHTML = `
            <div class="sdm-modal" role="dialog">
                <button class="sdm-close" title="关闭">✕</button>
                <div class="sdm-cover">
                    <div class="sdm-cover-disc"></div>
                    <div class="sdm-rank-badge" style="display:none">—</div>
                    <div class="sdm-chart-badge" style="display:none">—</div>
                </div>
                <div class="sdm-body">
                    <div class="sdm-title">—</div>
                    <div class="sdm-artist">—</div>
                    <div class="sdm-actions">
                        <button class="sdm-btn primary" data-action="play">▶ 立即播放</button>
                        <button class="sdm-btn ghost" data-action="fav">☆ 收藏</button>
                    </div>
                    <div class="sdm-section">
                        <div class="sdm-section-title">📊 历史排名趋势</div>
                        <div class="sdm-trend-list" data-trend><div class="sdm-trend-empty">加载中...</div></div>
                    </div>
                    <div class="sdm-section">
                        <div class="sdm-section-title">🎤 歌词</div>
                        <div class="sdm-lyric" data-lyric><div class="sdm-lyric-empty">点击展开歌词</div></div>
                    </div>
                </div>
            </div>
        `;
        document.body.appendChild(backdropEl);

        backdropEl.addEventListener('click', (e) => {
            if (e.target === backdropEl) close();
        });
        backdropEl.querySelector('.sdm-close').addEventListener('click', close);
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape' && backdropEl.classList.contains('show')) close();
        });
    }

    // 解析 LRC 格式
    function parseLRC(lrcText) {
        if (!lrcText) return [];
        const lines = lrcText.split('\n');
        const result = [];
        const timeRe = /\[(\d+):(\d+)(?:\.(\d+))?\]/g;
        for (const line of lines) {
            const text = line.replace(timeRe, '').trim();
            if (!text) continue;
            const matches = [...line.matchAll(/\[(\d+):(\d+)(?:\.(\d+))?\]/g)];
            for (const m of matches) {
                const min = parseInt(m[1]);
                const sec = parseInt(m[2]);
                const ms = m[3] ? parseInt(m[3].padEnd(3, '0').slice(0, 3)) : 0;
                result.push({
                    time: min * 60 + sec + ms / 1000,
                    text,
                });
            }
        }
        return result.sort((a, b) => a.time - b.time);
    }

    let _lyricLines = [];
    let _lyricUpdateInterval = null;
    let _currentSongKey = null;
    let _lyricLoaded = false;

    function updateLyricHighlight() {
        const a = GlobalPlayer.getState().audioElement;
        if (!a || !_lyricLines.length) return;
        const cur = a.currentTime;
        // 找到当前应该高亮的行
        let activeIdx = -1;
        for (let i = 0; i < _lyricLines.length; i++) {
            if (_lyricLines[i].time <= cur) activeIdx = i;
            else break;
        }
        const cont = backdropEl.querySelector('[data-lyric]');
        if (!cont) return;
        const lineEls = cont.querySelectorAll('.lyric-line');
        lineEls.forEach((el, i) => {
            el.classList.toggle('active', i === activeIdx);
        });
        // 自动滚动到可视区
        if (activeIdx >= 0 && lineEls[activeIdx]) {
            lineEls[activeIdx].scrollIntoView({ block: 'center', behavior: 'smooth' });
        }
    }

    function startLyricSync() {
        stopLyricSync();
        _lyricUpdateInterval = setInterval(updateLyricHighlight, 200);
    }
    function stopLyricSync() {
        if (_lyricUpdateInterval) { clearInterval(_lyricUpdateInterval); _lyricUpdateInterval = null; }
    }

    async function open(song) {
        build();
        if (!song || !song.title) return;
        const safeTitle = String(song.title).replace(/[<>"']/g, c => ({'<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
        const safeArtist = String(song.artist || '').replace(/[<>"']/g, c => ({'<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));

        // Set basic info
        backdropEl.querySelector('.sdm-title').textContent = song.title;
        backdropEl.querySelector('.sdm-artist').textContent = song.artist || '—';

        // Rank badge
        const rankBadge = backdropEl.querySelector('.sdm-rank-badge');
        if (song.rank) {
            rankBadge.style.display = '';
            rankBadge.textContent = 'No.' + song.rank;
        } else {
            rankBadge.style.display = 'none';
        }

        // Chart badge
        const chartBadge = backdropEl.querySelector('.sdm-chart-badge');
        if (song.chart) {
            chartBadge.style.display = '';
            chartBadge.textContent = song.chart;
        } else {
            chartBadge.style.display = 'none';
        }

        // Spin disc
        const disc = backdropEl.querySelector('.sdm-cover-disc');
        const gs = GlobalPlayer.getState();
        const isCurrent = gs.title === song.title && gs.artist === song.artist;
        disc.classList.toggle('playing', isCurrent && gs.isPlaying);

        // Reset state
        _lyricLines = [];
        _lyricLoaded = false;
        _currentSongKey = song.title + '|' + song.artist;
        stopLyricSync();
        backdropEl.querySelector('[data-lyric]').innerHTML = '<div class="sdm-lyric-empty">点击展开歌词</div>';
        backdropEl.querySelector('[data-trend]').innerHTML = '<div class="sdm-trend-empty">加载中...</div>';

        // Show
        backdropEl.classList.add('show');

        // Bind actions
        const playBtn = backdropEl.querySelector('[data-action="play"]');
        playBtn.onclick = () => {
            if (window._playSong) {
                window._playSong(song.title, song.artist, song.chart || '', null);
                disc.classList.add('playing');
            }
        };
        const favBtn = backdropEl.querySelector('[data-action="fav"]');
        const updateFavBtn = () => {
            const isFav = window.isFav ? window.isFav(song.title, song.artist) : false;
            favBtn.innerHTML = isFav ? '★ 已收藏' : '☆ 收藏';
        };
        updateFavBtn();
        favBtn.onclick = () => {
            if (window._toggleFav) {
                window._toggleFav(song.title, song.artist, song.chart || '', null);
                setTimeout(updateFavBtn, 50);
            }
        };

        // Load trend (historical ranks)
        if (song.chart) {
            fetch('/api/history/trend?chart_name=' + encodeURIComponent(song.chart)
                + '&song_title=' + encodeURIComponent(song.title)
                + '&artist=' + encodeURIComponent(song.artist) + '&days=30')
                .then(r => r.json())
                .then(j => {
                    if (!j.success || !j.trend || !j.trend.length) {
                        backdropEl.querySelector('[data-trend]').innerHTML = '<div class="sdm-trend-empty">暂无历史排名</div>';
                        return;
                    }
                    backdropEl.querySelector('[data-trend]').innerHTML = j.trend.slice(-15).map(t => {
                        const d = new Date(t.timestamp);
                        const dateStr = d.toLocaleDateString('zh-CN') + ' ' + d.toTimeString().slice(0, 5);
                        return `<div class="sdm-trend-row">
                            <span class="sdm-trend-time">${dateStr}</span>
                            <span class="sdm-trend-rank">No.${t.rank}</span>
                        </div>`;
                    }).join('');
                })
                .catch(() => {
                    backdropEl.querySelector('[data-trend]').innerHTML = '<div class="sdm-trend-empty">加载失败</div>';
                });
        } else {
            backdropEl.querySelector('[data-trend]').innerHTML = '<div class="sdm-trend-empty">需指定榜单</div>';
        }

        // Load lyric
        backdropEl.querySelector('[data-lyric]').onclick = loadLyric;
    }

    async function loadLyric() {
        if (_lyricLoaded) {
            // Toggle collapse
            const cont = backdropEl.querySelector('[data-lyric]');
            if (cont.style.maxHeight === '32px') {
                cont.style.maxHeight = '200px';
            } else {
                cont.style.maxHeight = '32px';
            }
            return;
        }
        const song = parseCurrentSong();
        if (!song) return;

        const cont = backdropEl.querySelector('[data-lyric]');
        cont.innerHTML = '<div class="sdm-loading">加载歌词</div>';

        try {
            const r = await fetch('/api/song/lyric', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ title: song.title, artist: song.artist }),
            });
            const j = await r.json();
            if (!j.success || !j.lyric) {
                if (j.encrypted) {
                    cont.innerHTML = '<div class="sdm-lyric-empty">🔒 网易云歌词接口已加密<br><span style="font-size:11px;opacity:0.7">接口已实现，加密需前端 JS 解密或服务端证书</span></div>';
                } else {
                    cont.innerHTML = '<div class="sdm-lyric-empty">暂无可显示歌词<br><span style="font-size:11px;opacity:0.7">' + (j.error || '') + '</span></div>';
                }
                return;
            }
            _lyricLines = parseLRC(j.lyric);
            if (!_lyricLines.length) {
                cont.innerHTML = '<div class="sdm-lyric-empty">歌词解析失败</div>';
                return;
            }
            _lyricLoaded = true;
            cont.innerHTML = _lyricLines.map(l => `<span class="lyric-line">${escapeHtml(l.text)}</span>`).join('');
            cont.style.maxHeight = '200px';
            // 开始同步高亮
            startLyricSync();
            updateLyricHighlight();
        } catch (e) {
            cont.innerHTML = '<div class="sdm-lyric-empty">歌词加载失败</div>';
        }
    }

    function parseCurrentSong() {
        if (!_currentSongKey) return null;
        const [title, artist] = _currentSongKey.split('|');
        return { title, artist };
    }

    function close() {
        if (!backdropEl) return;
        backdropEl.classList.remove('show');
        stopLyricSync();
    }

    function escapeHtml(s) {
        return String(s).replace(/[<>&"]/g, c => ({'<':'&lt;','>':'&gt;','&':'&amp;','"':'&quot;'}[c]));
    }

    window.SongDetailModal = { open, close };
})();
