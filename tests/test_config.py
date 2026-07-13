from music_analytics.config import Config


def test_secret_key_is_generated_per_config(monkeypatch):
    monkeypatch.delenv("MUSIC_ANALYSIS_SECRET_KEY", raising=False)

    first = Config().secret_key
    second = Config().secret_key

    assert len(first) >= 32
    assert len(second) >= 32
    assert first != second
    assert first != "netmusic-analysis-secret-key"


def test_secret_key_can_be_overridden_from_environment(monkeypatch):
    expected = "test-only-secret-from-environment"
    monkeypatch.setenv("MUSIC_ANALYSIS_SECRET_KEY", expected)

    assert Config().secret_key == expected


def test_official_chart_catalog_contains_all_supported_charts():
    charts = Config().chart_ids

    assert len(charts) == 12
    assert charts["热歌榜"] == "3778678"
    assert charts["网易云日语榜"] == "5059644681"
