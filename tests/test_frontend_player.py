"""Static regression checks for the music player template."""

from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
PLAYER_TEMPLATE = PROJECT_ROOT / "templates" / "music_player.html"
DASHBOARD_TEMPLATE = PROJECT_ROOT / "templates" / "index.html"
SPOTIFY_PLAYER = PROJECT_ROOT / "static" / "spotify-official-player.js"


def _template_source() -> str:
    return PLAYER_TEMPLATE.read_text(encoding="utf-8")


def test_song_actions_use_safe_event_delegation() -> None:
    source = _template_source()

    assert "onclick=" not in source
    assert "songList.addEventListener('click'" in source
    assert 'data-song-action="play"' in source
    assert 'data-song-action="favorite"' in source
    assert 'data-song-action="detail"' in source


def test_async_search_and_chart_render_only_latest_request() -> None:
    source = _template_source()

    assert "requestVersion !== searchRequestVersion" in source
    assert "requestVersion === chartRequestVersion" in source
    assert "chartRequestController === controller" in source
    assert "new AbortController()" in source


def test_spotify_official_player_is_wired_into_both_pages() -> None:
    player_source = _template_source()
    dashboard_source = DASHBOARD_TEMPLATE.read_text(encoding="utf-8")

    for source in (player_source, dashboard_source):
        assert '<script src="/static/spotify-official-player.js"></script>' in source
        assert "SpotifyOfficial.searchAndPlay" in source
        assert "SpotifyOfficial?.isConnected?.()" in source


def test_spotify_oauth_uses_pkce_and_browser_session_only() -> None:
    source = SPOTIFY_PLAYER.read_text(encoding="utf-8")

    assert "code_challenge_method: 'S256'" in source
    assert "https://sdk.scdn.co/spotify-player.js" in source
    assert "sessionStorage" in source
    assert "localStorage" not in source
    assert "client_secret" not in source.lower()
    assert "window.SpotifyOfficial" in source
