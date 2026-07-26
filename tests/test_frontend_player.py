"""Static regression checks for the music player template."""

from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
PLAYER_TEMPLATE = PROJECT_ROOT / "templates" / "music_player.html"
DASHBOARD_TEMPLATE = PROJECT_ROOT / "templates" / "index.html"


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


def test_spotify_references_removed_from_both_pages() -> None:
    """Spotify official player has been removed from the project."""
    player_source = _template_source()
    dashboard_source = DASHBOARD_TEMPLATE.read_text(encoding="utf-8")

    for source in (player_source, dashboard_source):
        assert "spotify-official-player.js" not in source
        assert "SpotifyOfficial" not in source
        assert "officialPlayerActive" not in source


def test_dashboard_loads_theme_manager_before_inline_boot_code() -> None:
    """The dashboard must define ThemeManager before calling onChange()."""
    source = DASHBOARD_TEMPLATE.read_text(encoding="utf-8")

    dependency = '<script src="/static/theme-manager.js"></script>'
    assert dependency in source
    assert source.index(dependency) < source.index("ThemeManager.onChange")
