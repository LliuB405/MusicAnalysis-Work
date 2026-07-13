"""Static regression checks for the music player template."""

from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
PLAYER_TEMPLATE = PROJECT_ROOT / "templates" / "music_player.html"


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
