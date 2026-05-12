"""
FastAPI integration tests for GET /dataset.

DATA_DIR is patched via monkeypatch so tests run without the real data directory.
The module-level singleton _dataset_info is reset between tests that verify
singleton behaviour to ensure isolation.
"""

import json
from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

FIXTURE_DATA = {
    "total_source": 9544,
    "total_selected": 50,
    "total_included": 49,
    "total_excluded": 1,
    "exclusions": [
        {
            "source_id": "3054",
            "category": "Network Support Engineer",
            "reason": "no_skills",
        }
    ],
}


@pytest.fixture()
def client(mocker, monkeypatch, tmp_path):
    # Patch get_collection so lifespan startup doesn't need the real Chroma index
    mocker.patch("src.main.get_collection", return_value=mocker.MagicMock())
    # Patch DATA_DIR to tmp_path and reset singleton before each test
    monkeypatch.setattr("src.features.dataset.router.DATA_DIR", tmp_path)
    monkeypatch.setattr("src.features.dataset.router._dataset_info", None)
    # Write valid exclusions.json into tmp_path
    (tmp_path / "exclusions.json").write_text(json.dumps(FIXTURE_DATA))

    from src.main import app

    with TestClient(app) as c:
        yield c, tmp_path


def test_get_dataset_success(client):
    c, _ = client
    response = c.get("/dataset")
    assert response.status_code == 200
    body = response.json()
    assert body["total_included"] == 49
    assert body["total_excluded"] == 1
    assert len(body["exclusions"]) == 1
    entry = body["exclusions"][0]
    assert entry["source_id"] == "3054"
    assert entry["reason"] == "no_skills"


def test_get_dataset_file_absent(mocker, monkeypatch, tmp_path):
    mocker.patch("src.main.get_collection", return_value=mocker.MagicMock())
    # Point DATA_DIR to tmp_path but do NOT create exclusions.json
    monkeypatch.setattr("src.features.dataset.router.DATA_DIR", tmp_path)
    monkeypatch.setattr("src.features.dataset.router._dataset_info", None)

    from src.main import app

    with TestClient(app) as c:
        response = c.get("/dataset")
    assert response.status_code == 500
    assert response.json()["detail"] == "Dataset info unavailable"


def test_get_dataset_singleton(mocker, monkeypatch, tmp_path):
    mocker.patch("src.main.get_collection", return_value=mocker.MagicMock())
    monkeypatch.setattr("src.features.dataset.router.DATA_DIR", tmp_path)
    monkeypatch.setattr("src.features.dataset.router._dataset_info", None)

    (tmp_path / "exclusions.json").write_text(json.dumps(FIXTURE_DATA))

    # Wrap read_text to count calls on the exclusions.json file
    original_read_text = Path.read_text
    call_count = 0

    def counting_read_text(self, *args, **kwargs):
        nonlocal call_count
        if self.name == "exclusions.json":
            call_count += 1
        return original_read_text(self, *args, **kwargs)

    from src.main import app

    with patch.object(Path, "read_text", counting_read_text):
        with TestClient(app) as c:
            c.get("/dataset")
            c.get("/dataset")

    assert call_count == 1
