/**
 * SpotifyOfficialPlayer
 * Official Spotify Web Playback SDK + OAuth Authorization Code with PKCE.
 * Tokens live in sessionStorage only. No password, cookie or client secret is used.
 */
(function () {
    'use strict';

    const TOKEN_KEY = 'pulse_spotify_token';
    const VERIFIER_KEY = 'pulse_spotify_verifier';
    const STATE_KEY = 'pulse_spotify_oauth_state';
    const RETURN_KEY = 'pulse_spotify_return_to';
    const AUTH_URL = 'https://accounts.spotify.com/authorize';
    const TOKEN_URL = 'https://accounts.spotify.com/api/token';
    const API_URL = 'https://api.spotify.com/v1';
    const SDK_URL = 'https://sdk.scdn.co/spotify-player.js';

    let config = null;
    let token = readJson(TOKEN_KEY);
    let player = null;
    let deviceId = '';
    let ready = false;
    let profile = null;
    let lastState = null;
    let initPromise = null;
    let shuffleEnabled = false;
    let repeatState = 'off';

    function readJson(key) {
        try { return JSON.parse(sessionStorage.getItem(key) || 'null'); }
        catch (_) { return null; }
    }

    function writeJson(key, value) {
        if (value == null) sessionStorage.removeItem(key);
        else sessionStorage.setItem(key, JSON.stringify(value));
    }

    function randomString(length) {
        const alphabet = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-._~';
        const values = crypto.getRandomValues(new Uint8Array(length));
        return Array.from(values, value => alphabet[value % alphabet.length]).join('');
    }

    async function codeChallenge(verifier) {
        const digest = await crypto.subtle.digest('SHA-256', new TextEncoder().encode(verifier));
        return btoa(String.fromCharCode(...new Uint8Array(digest)))
            .replace(/=/g, '').replace(/\+/g, '-').replace(/\//g, '_');
    }

    async function loadConfig() {
        if (config) return config;
        const response = await fetch('/api/spotify/config', { credentials: 'same-origin' });
        if (!response.ok) throw new Error('Spotify 配置读取失败');
        config = await response.json();
        return config;
    }

    async function login() {
        const cfg = await loadConfig();
        if (!cfg.configured) {
            showMessage('请先设置 SPOTIFY_CLIENT_ID，并在 Spotify Dashboard 添加回调地址：' + cfg.redirect_uri, true);
            return false;
        }
        const verifier = randomString(96);
        const oauthState = randomString(32);
        sessionStorage.setItem(VERIFIER_KEY, verifier);
        sessionStorage.setItem(STATE_KEY, oauthState);
        sessionStorage.setItem(RETURN_KEY, location.pathname);
        const params = new URLSearchParams({
            client_id: cfg.client_id,
            response_type: 'code',
            redirect_uri: cfg.redirect_uri,
            scope: cfg.scopes.join(' '),
            state: oauthState,
            code_challenge_method: 'S256',
            code_challenge: await codeChallenge(verifier)
        });
        location.assign(AUTH_URL + '?' + params.toString());
        return true;
    }

    async function handleCallback() {
        const params = new URLSearchParams(location.search);
        const code = params.get('code');
        const error = params.get('error');
        if (!code && !error) return false;

        const cleanUrl = location.pathname + location.hash;
        if (error) {
            history.replaceState({}, '', cleanUrl);
            showMessage('Spotify 登录未完成：' + error, true);
            return false;
        }

        const expectedState = sessionStorage.getItem(STATE_KEY);
        const returnedState = params.get('state');
        const verifier = sessionStorage.getItem(VERIFIER_KEY);
        if (!expectedState || expectedState !== returnedState || !verifier) {
            history.replaceState({}, '', cleanUrl);
            throw new Error('Spotify 登录状态校验失败，请重新登录');
        }

        const cfg = await loadConfig();
        const response = await fetch(TOKEN_URL, {
            method: 'POST',
            headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
            body: new URLSearchParams({
                client_id: cfg.client_id,
                grant_type: 'authorization_code',
                code,
                redirect_uri: cfg.redirect_uri,
                code_verifier: verifier
            })
        });
        const body = await response.json();
        if (!response.ok || !body.access_token) throw new Error(body.error_description || 'Spotify 令牌交换失败');
        token = {
            access_token: body.access_token,
            refresh_token: body.refresh_token || '',
            expires_at: Date.now() + Math.max(60, body.expires_in || 3600) * 1000
        };
        writeJson(TOKEN_KEY, token);
        sessionStorage.removeItem(VERIFIER_KEY);
        sessionStorage.removeItem(STATE_KEY);
        history.replaceState({}, '', cleanUrl);
        showMessage('Spotify 登录成功，正在连接官方播放器');
        return true;
    }

    async function refreshToken() {
        if (!token?.refresh_token) return false;
        const cfg = await loadConfig();
        const response = await fetch(TOKEN_URL, {
            method: 'POST',
            headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
            body: new URLSearchParams({
                grant_type: 'refresh_token',
                refresh_token: token.refresh_token,
                client_id: cfg.client_id
            })
        });
        const body = await response.json();
        if (!response.ok || !body.access_token) return false;
        token = {
            access_token: body.access_token,
            refresh_token: body.refresh_token || token.refresh_token,
            expires_at: Date.now() + Math.max(60, body.expires_in || 3600) * 1000
        };
        writeJson(TOKEN_KEY, token);
        return true;
    }

    async function accessToken() {
        if (!token?.access_token) return '';
        if (Date.now() >= (token.expires_at || 0) - 60000) {
            const refreshed = await refreshToken();
            if (!refreshed) logout(false);
        }
        return token?.access_token || '';
    }

    async function spotifyApi(path, options = {}) {
        const bearer = await accessToken();
        if (!bearer) throw new Error('请先登录 Spotify');
        const response = await fetch(path.startsWith('http') ? path : API_URL + path, {
            ...options,
            headers: {
                Authorization: 'Bearer ' + bearer,
                ...(options.body ? { 'Content-Type': 'application/json' } : {}),
                ...(options.headers || {})
            }
        });
        if (response.status === 401 && await refreshToken()) return spotifyApi(path, options);
        if (!response.ok && response.status !== 204) {
            let message = 'Spotify 请求失败 (' + response.status + ')';
            try { message = (await response.json()).error?.message || message; } catch (_) {}
            throw new Error(message);
        }
        if (response.status === 204) return null;
        return response.json();
    }

    function loadSdk() {
        if (window.Spotify?.Player) return Promise.resolve();
        return new Promise((resolve, reject) => {
            const previous = window.onSpotifyWebPlaybackSDKReady;
            window.onSpotifyWebPlaybackSDKReady = () => {
                if (typeof previous === 'function') previous();
                resolve();
            };
            const existing = document.querySelector('script[data-spotify-sdk]');
            if (existing) return;
            const script = document.createElement('script');
            script.src = SDK_URL;
            script.async = true;
            script.dataset.spotifySdk = 'true';
            script.onerror = () => reject(new Error('Spotify 播放 SDK 加载失败'));
            document.head.appendChild(script);
        });
    }

    function dispatchState(sdkState) {
        if (sdkState) {
            lastState = sdkState;
            if (typeof sdkState.shuffle === 'boolean') shuffleEnabled = sdkState.shuffle;
            if (Number.isInteger(sdkState.repeat_mode)) {
                repeatState = sdkState.repeat_mode === 2 ? 'track' : sdkState.repeat_mode === 1 ? 'context' : 'off';
            }
        }
        const track = lastState?.track_window?.current_track;
        const detail = {
            provider: 'spotify',
            ready,
            connected: Boolean(token?.access_token),
            deviceId,
            isPlaying: Boolean(lastState && !lastState.paused),
            title: track?.name || '',
            artist: track?.artists?.map(item => item.name).join(' / ') || '',
            cover: track?.album?.images?.[0]?.url || '',
            position: lastState?.position || 0,
            duration: lastState?.duration || 0,
            shuffle: shuffleEnabled,
            repeat: repeatState,
            repeatMode: shuffleEnabled ? 'shuffle' : repeatState === 'track' ? 'one' : 'sequence',
            profile: profile ? { display_name: profile.display_name, product: profile.product } : null
        };
        window.dispatchEvent(new CustomEvent('spotify-official-state', { detail }));
        paintConnectButtons(detail);
    }

    async function connectPlayer() {
        if (!token?.access_token) return false;
        await loadSdk();
        if (player) return ready;
        player = new Spotify.Player({
            name: 'Pulse Music Analytics',
            getOAuthToken: async callback => callback(await accessToken()),
            volume: 0.8
        });
        player.addListener('ready', ({ device_id }) => {
            deviceId = device_id;
            ready = true;
            dispatchState();
            showMessage('Spotify 官方播放器已连接');
        });
        player.addListener('not_ready', () => { ready = false; dispatchState(); });
        player.addListener('player_state_changed', dispatchState);
        player.addListener('authentication_error', ({ message }) => { showMessage('Spotify 登录失效：' + message, true); logout(false); });
        player.addListener('account_error', () => showMessage('完整播放需要当前登录账号拥有 Spotify Premium', true));
        player.addListener('playback_error', ({ message }) => showMessage('Spotify 播放失败：' + message, true));
        return player.connect();
    }

    async function initialize() {
        if (initPromise) return initPromise;
        initPromise = (async () => {
            await loadConfig();
            await handleCallback();
            renderConnectUi();
            if (!token?.access_token) return false;
            try {
                profile = await spotifyApi('/me');
                if (profile.product !== 'premium') {
                    showMessage('当前 Spotify 账号不是 Premium，官方 SDK 无法完整播放', true);
                    dispatchState();
                    return false;
                }
                return connectPlayer();
            } catch (error) {
                showMessage(error.message, true);
                return false;
            }
        })();
        return initPromise;
    }

    async function searchAndPlay(title, artist) {
        if (!ready || !deviceId) throw new Error('请先连接 Spotify 官方播放器');
        const query = `track:${title} artist:${artist}`;
        const result = await spotifyApi('/search?' + new URLSearchParams({ q: query, type: 'track', limit: '8' }));
        const tracks = result?.tracks?.items || [];
        const track = tracks.find(item => item.is_playable !== false) || tracks[0];
        if (!track) throw new Error('Spotify 曲库中未找到匹配歌曲');
        await spotifyApi('/me/player', {
            method: 'PUT',
            body: JSON.stringify({ device_ids: [deviceId], play: false })
        });
        await new Promise(resolve => setTimeout(resolve, 220));
        await spotifyApi('/me/player/play?device_id=' + encodeURIComponent(deviceId), {
            method: 'PUT',
            body: JSON.stringify({ uris: [track.uri] })
        });
        return track;
    }

    function requireReadyPlayer() {
        if (!ready || !player) throw new Error('Spotify 官方播放器仍在连接，请稍候');
        return player;
    }

    async function togglePlay() { await requireReadyPlayer().togglePlay(); }
    async function previousTrack() { await requireReadyPlayer().previousTrack(); }
    async function nextTrack() { await requireReadyPlayer().nextTrack(); }
    async function seek(milliseconds) { await requireReadyPlayer().seek(Math.max(0, milliseconds)); }
    async function setVolume(value) { await requireReadyPlayer().setVolume(Math.max(0, Math.min(1, value))); }
    async function setShuffle(enabled) {
        if (!ready || !deviceId) throw new Error('Spotify 官方播放器仍在连接，请稍候');
        const nextValue = Boolean(enabled);
        await spotifyApi('/me/player/shuffle?state=' + String(nextValue) + '&device_id=' + encodeURIComponent(deviceId), { method: 'PUT' });
        shuffleEnabled = nextValue;
        dispatchState();
    }
    async function setRepeat(mode) {
        if (!ready || !deviceId) throw new Error('Spotify 官方播放器仍在连接，请稍候');
        const nextValue = ['off', 'context', 'track'].includes(mode) ? mode : 'off';
        await spotifyApi('/me/player/repeat?state=' + encodeURIComponent(nextValue) + '&device_id=' + encodeURIComponent(deviceId), { method: 'PUT' });
        repeatState = nextValue;
        dispatchState();
    }

    async function setPlaybackMode(mode) {
        const normalized = ['sequence', 'shuffle', 'one'].includes(mode) ? mode : 'sequence';
        await setShuffle(normalized === 'shuffle');
        await setRepeat(normalized === 'one' ? 'track' : 'off');
        dispatchState();
    }

    function logout(notify = true) {
        player?.disconnect();
        player = null; deviceId = ''; ready = false; profile = null; lastState = null; token = null;
        shuffleEnabled = false; repeatState = 'off';
        writeJson(TOKEN_KEY, null);
        if (notify) showMessage('已退出 Spotify（仅清除本浏览器会话）');
        dispatchState();
    }

    function showMessage(message, isError = false) {
        if (typeof window.toast === 'function') return window.toast(message, isError ? 'error' : 'success');
        if (typeof window.showToast === 'function') return window.showToast(message, isError);
        let node = document.getElementById('spotify-official-toast');
        if (!node) {
            node = document.createElement('div');
            node.id = 'spotify-official-toast';
            document.body.appendChild(node);
        }
        node.textContent = message;
        node.className = isError ? 'spotify-toast error show' : 'spotify-toast show';
        clearTimeout(node._timer);
        node._timer = setTimeout(() => node.classList.remove('show'), 4200);
    }

    function renderConnectUi() {
        if (document.getElementById('spotify-connect-button')) return;
        const button = document.createElement('button');
        button.id = 'spotify-connect-button';
        button.type = 'button';
        button.className = 'spotify-connect-button';
        button.addEventListener('click', () => token?.access_token ? logout() : login());
        const target = document.querySelector('.topbar-actions') || document.querySelector('.am-local-actions') || document.querySelector('.sp-right') || document.body;
        target.prepend(button);
        paintConnectButtons({ connected: Boolean(token?.access_token), ready, profile });
    }

    function paintConnectButtons(detail) {
        const button = document.getElementById('spotify-connect-button');
        if (!button) return;
        button.classList.toggle('connected', Boolean(detail.connected));
        button.classList.toggle('ready', Boolean(detail.ready));
        const label = detail.connected ? '断开 Spotify' : '连接 Spotify';
        button.innerHTML = '<span class="spotify-dot"></span><span>' + label.replace(/[&<>"']/g, '') + '</span>';
        const account = detail.profile?.display_name ? '（' + detail.profile.display_name + '）' : '';
        button.title = detail.ready
            ? 'Spotify 已连接' + account + '，点击断开'
            : detail.connected ? 'Spotify 正在连接，点击可断开' : '使用 Spotify OAuth PKCE 登录';
    }

    function installStyles() {
        if (document.getElementById('spotify-official-styles')) return;
        const style = document.createElement('style');
        style.id = 'spotify-official-styles';
        style.textContent = `
          .spotify-connect-button{display:inline-flex;align-items:center;gap:7px;min-height:34px;padding:7px 12px;border:1px solid rgba(255,255,255,.16);border-radius:999px;background:#181818;color:#fff;font:700 12px inherit;white-space:nowrap;cursor:pointer;transition:.18s ease}
          .spotify-connect-button:hover{transform:scale(1.03);border-color:#fff}.spotify-connect-button.connected{border-color:rgba(30,215,96,.46)}.spotify-connect-button.ready{background:#1ed760;color:#000;border-color:#1ed760}
          .spotify-dot{width:8px;height:8px;border-radius:50%;background:#777}.spotify-connect-button.connected .spotify-dot{background:#f5b942}.spotify-connect-button.ready .spotify-dot{background:#000;box-shadow:0 0 0 3px rgba(0,0,0,.12)}
          .spotify-toast{position:fixed;right:22px;bottom:112px;z-index:10050;max-width:min(420px,calc(100vw - 32px));padding:12px 16px;border-radius:8px;background:#1ed760;color:#07130b;font:700 13px/1.45 inherit;box-shadow:0 18px 46px rgba(0,0,0,.4);opacity:0;transform:translateY(12px);pointer-events:none;transition:.2s ease}.spotify-toast.error{background:#e91429;color:#fff}.spotify-toast.show{opacity:1;transform:none}
          body:not(:has(.sp-right))>.spotify-connect-button{position:fixed;right:22px;top:90px;z-index:9100}
          @media(max-width:720px){.spotify-connect-button{min-height:32px;padding:6px 9px;font-size:11px}.spotify-toast{right:16px;bottom:148px}}
        `;
        document.head.appendChild(style);
    }

    function interceptExistingControls() {
        const run = handler => Promise.resolve().then(handler).catch(error => showMessage(error.message, true));
        const claimOfficialEvent = event => {
            if (!token?.access_token) return false;
            event.preventDefault();
            event.stopImmediatePropagation();
            if (!ready) {
                showMessage('Spotify 官方播放器仍在连接，请稍候', true);
                return false;
            }
            return true;
        };
        const bind = (selector, handler) => {
            document.querySelector(selector)?.addEventListener('click', event => {
                if (!claimOfficialEvent(event)) return;
                run(() => handler(event));
            }, true);
        };
        bind('#playPauseBtn', togglePlay);
        bind('#sp-play', togglePlay);
        bind('#prevBtn', previousTrack);
        bind('#sp-prev', previousTrack);
        bind('#nextBtn', nextTrack);
        bind('#sp-next', nextTrack);
        bind('#sp-shuffle', () => setShuffle(!shuffleEnabled));
        bind('#sp-repeat', () => setRepeat(repeatState === 'track' ? 'off' : 'track'));
        bind('#repeatBtn', () => {
            const current = shuffleEnabled ? 'shuffle' : repeatState === 'track' ? 'one' : 'sequence';
            const modes = ['sequence', 'shuffle', 'one'];
            return setPlaybackMode(modes[(modes.indexOf(current) + 1) % modes.length]);
        });
        const volume = document.querySelector('#volSlider') || document.querySelector('#sp-volume');
        volume?.addEventListener('input', event => {
            if (!claimOfficialEvent(event)) return;
            run(() => setVolume(Number(event.target.value) / 100));
        }, true);
        const progress = document.querySelector('#progressBar') || document.querySelector('#sp-progress');
        progress?.addEventListener('input', event => {
            if (!claimOfficialEvent(event)) return;
            if (!lastState?.duration) return;
            const ratio = progress.max === '100'
                ? Number(event.target.value) / 100
                : Number(event.target.value) / Number(progress.max || lastState.duration);
            run(() => seek(lastState.duration * Math.max(0, Math.min(1, ratio))));
        }, true);
    }

    window.SpotifyOfficial = {
        initialize, login, logout, searchAndPlay, togglePlay, previousTrack, nextTrack,
        seek, setVolume, setShuffle, setRepeat, setPlaybackMode,
        isReady: () => ready,
        isConnected: () => Boolean(token?.access_token),
        getState: () => ({ ready, deviceId, profile, sdkState: lastState })
    };

    installStyles();
    document.addEventListener('DOMContentLoaded', () => {
        renderConnectUi();
        interceptExistingControls();
        initialize().catch(error => showMessage(error.message, true));
    });
})();
