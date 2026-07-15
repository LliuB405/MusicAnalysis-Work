"""收藏 API 的并发、校验和持久化测试。"""

import json
from concurrent.futures import ThreadPoolExecutor

import pytest

import app as app_module
from app import app as flask_app


@pytest.fixture(autouse=True)
def isolated_favorites_file(tmp_path, monkeypatch):
    """每个测试都使用临时文件，绝不读写项目根目录的真实收藏。"""
    favorites_file = tmp_path / "favorites.json"
    monkeypatch.setattr(app_module, "_FAVORITES_FILE", str(favorites_file))
    return favorites_file


@pytest.fixture
def client():
    flask_app.config["TESTING"] = True
    with flask_app.test_client() as test_client:
        yield test_client


def _song(index=1, **overrides):
    payload = {
        "title": f"歌曲 {index}",
        "artist": f"歌手 {index}",
        "chart": "飙升榜",
    }
    payload.update(overrides)
    return payload


def test_get_returns_empty_list_without_creating_file(client, isolated_favorites_file):
    response = client.get("/api/favorites")

    assert response.status_code == 200
    assert response.get_json() == {"success": True, "favorites": []}
    assert not isolated_favorites_file.exists()


def test_add_is_idempotent_and_persists_atomically(client, isolated_favorites_file):
    first = client.post("/api/favorites", json=_song(action="add"))
    second = client.post(
        "/api/favorites",
        json=_song(action="add", chart="不应覆盖原值"),
    )

    assert first.status_code == 200
    assert first.get_json()["changed"] is True
    assert second.status_code == 200
    assert second.get_json()["action"] == "added"
    assert second.get_json()["changed"] is False
    assert len(second.get_json()["favorites"]) == 1
    assert second.get_json()["favorites"][0]["chart"] == "飙升榜"
    assert json.loads(isolated_favorites_file.read_text(encoding="utf-8")) == [
        {"title": "歌曲 1", "artist": "歌手 1", "chart": "飙升榜"}
    ]
    assert list(isolated_favorites_file.parent.glob(".favorites-*.tmp")) == []


def test_remove_is_idempotent(client):
    client.post("/api/favorites", json=_song(action="add"))

    first = client.post("/api/favorites", json=_song(action="remove"))
    second = client.post("/api/favorites", json=_song(action="remove"))

    assert first.get_json()["changed"] is True
    assert first.get_json()["favorites"] == []
    assert second.status_code == 200
    assert second.get_json()["action"] == "removed"
    assert second.get_json()["changed"] is False


def test_missing_action_and_explicit_toggle_remain_compatible(client):
    added = client.post("/api/favorites", json=_song())
    removed = client.post("/api/favorites", json=_song(action="toggle"))

    assert added.status_code == 200
    assert added.get_json()["action"] == "added"
    assert removed.status_code == 200
    assert removed.get_json()["action"] == "removed"
    assert removed.get_json()["favorites"] == []


@pytest.mark.parametrize(
    ("payload", "expected_code"),
    [
        ([], "invalid_request"),
        ({"artist": "歌手"}, "validation_error"),
        ({"title": "歌曲", "artist": 123}, "validation_error"),
        (_song(title="x" * 201), "validation_error"),
        (_song(action="delete"), "invalid_action"),
        (_song(action=["add"]), "invalid_action"),
    ],
)
def test_bad_parameters_return_clear_errors(client, payload, expected_code):
    response = client.post("/api/favorites", json=payload)

    assert response.status_code == 400
    assert response.get_json()["success"] is False
    assert response.get_json()["code"] == expected_code


def test_rejects_oversized_request_body(client):
    response = client.post(
        "/api/favorites",
        data=json.dumps(_song(extra="x" * 5000)),
        content_type="application/json",
    )

    assert response.status_code == 413
    assert response.get_json()["code"] == "payload_too_large"


def test_maximum_count_blocks_growth_but_allows_idempotent_add(client, monkeypatch):
    monkeypatch.setattr(app_module, "_FAVORITES_MAX_COUNT", 2)
    assert client.post("/api/favorites", json=_song(1, action="add")).status_code == 200
    assert client.post("/api/favorites", json=_song(2, action="add")).status_code == 200

    duplicate = client.post("/api/favorites", json=_song(1, action="add"))
    overflow = client.post("/api/favorites", json=_song(3, action="add"))

    assert duplicate.status_code == 200
    assert duplicate.get_json()["changed"] is False
    assert overflow.status_code == 409
    assert overflow.get_json()["code"] == "favorite_limit_reached"


def test_corrupt_storage_returns_error_without_overwriting(
    client, isolated_favorites_file
):
    isolated_favorites_file.write_text("{broken", encoding="utf-8")

    response = client.get("/api/favorites")

    assert response.status_code == 500
    assert response.get_json()["code"] == "favorites_storage_error"
    assert isolated_favorites_file.read_text(encoding="utf-8") == "{broken"


def test_atomic_write_failure_returns_error_and_cleans_temp_file(
    client, isolated_favorites_file, monkeypatch
):
    def fail_replace(_source, _target):
        raise PermissionError("simulated read-only storage")

    monkeypatch.setattr(app_module.os, "replace", fail_replace)

    response = client.post("/api/favorites", json=_song(action="add"))

    assert response.status_code == 500
    assert response.get_json()["code"] == "favorites_storage_error"
    assert not isolated_favorites_file.exists()
    assert list(isolated_favorites_file.parent.glob(".favorites-*.tmp")) == []


def test_concurrent_additions_do_not_lose_updates(isolated_favorites_file):
    def add_song(index):
        with flask_app.test_client() as test_client:
            return test_client.post(
                "/api/favorites", json=_song(index, action="add")
            ).status_code

    with ThreadPoolExecutor(max_workers=8) as executor:
        statuses = list(executor.map(add_song, range(1, 25)))

    assert statuses == [200] * 24
    stored = json.loads(isolated_favorites_file.read_text(encoding="utf-8"))
    assert len(stored) == 24
    assert {(item["title"], item["artist"]) for item in stored} == {
        (f"歌曲 {index}", f"歌手 {index}") for index in range(1, 25)
    }
