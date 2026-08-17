import base64

import httpx
import pytest

from app.services import moysklad_client as ms


class FakeResponse:
    def __init__(self, status_code: int, json_data: dict | None = None, text: str = ""):
        self.status_code = status_code
        self._json_data = json_data or {}
        self.text = text or str(json_data)

    def json(self):
        return self._json_data


@pytest.fixture(autouse=True)
def no_sleep(monkeypatch):
    # Тесты не должны реально ждать между ретраями
    monkeypatch.setattr(ms.time, "sleep", lambda seconds: None)


@pytest.fixture(autouse=True)
def clean_env(monkeypatch):
    monkeypatch.delenv("MOYSKLAD_TOKEN", raising=False)
    monkeypatch.delenv("MOYSKLAD_LOGIN", raising=False)
    monkeypatch.delenv("MOYSKLAD_PASSWORD", raising=False)


def test_auth_header_prefers_token(monkeypatch):
    monkeypatch.setenv("MOYSKLAD_TOKEN", "abc123")
    assert ms._build_auth_header() == "Bearer abc123"


def test_auth_header_login_password(monkeypatch):
    monkeypatch.setenv("MOYSKLAD_LOGIN", "user")
    monkeypatch.setenv("MOYSKLAD_PASSWORD", "pass")
    expected = "Basic " + base64.b64encode(b"user:pass").decode("ascii")
    assert ms._build_auth_header() == expected


def test_auth_header_missing_credentials_raises():
    with pytest.raises(ms.MoySkladError):
        ms._build_auth_header()


def test_get_stock_by_cells_empty_list_raises(monkeypatch):
    monkeypatch.setenv("MOYSKLAD_TOKEN", "abc123")
    with pytest.raises(ValueError):
        ms.get_stock_by_cells([])


def test_get_stock_by_cells_builds_filter(monkeypatch):
    monkeypatch.setenv("MOYSKLAD_TOKEN", "abc123")
    captured = {}

    def fake_get(self, url, headers=None, params=None):
        captured["url"] = url
        captured["params"] = params
        return FakeResponse(200, json_data={"rows": []})

    monkeypatch.setattr(httpx.Client, "get", fake_get)

    ms.get_stock_by_cells(["id-1", "id-2"], store_ids=["store-1"])

    assert captured["url"].endswith("/report/stock/byslot/current")
    assert captured["params"]["filter"] == "assortmentId=id-1,id-2;storeId=store-1"


def test_retries_on_server_error_then_succeeds(monkeypatch):
    monkeypatch.setenv("MOYSKLAD_TOKEN", "abc123")
    calls = {"count": 0}

    def fake_get(self, url, headers=None, params=None):
        calls["count"] += 1
        if calls["count"] < 3:
            return FakeResponse(500, text="server error")
        return FakeResponse(200, json_data={"rows": [{"stock": 5}]})

    monkeypatch.setattr(httpx.Client, "get", fake_get)

    result = ms.get_stock_by_cells(["id-1"])

    assert calls["count"] == 3
    assert result == {"rows": [{"stock": 5}]}


def test_raises_after_all_attempts_fail(monkeypatch):
    monkeypatch.setenv("MOYSKLAD_TOKEN", "abc123")

    def fake_get(self, url, headers=None, params=None):
        return FakeResponse(500, text="always broken")

    monkeypatch.setattr(httpx.Client, "get", fake_get)

    with pytest.raises(ms.MoySkladError):
        ms.get_stock_by_cells(["id-1"])


def test_get_sample_assortment_returns_rows(monkeypatch):
    monkeypatch.setenv("MOYSKLAD_TOKEN", "abc123")

    def fake_get(self, url, headers=None, params=None):
        assert url.endswith("/entity/assortment")
        assert params == {"limit": 5}
        return FakeResponse(200, json_data={"rows": [{"id": "x1"}, {"id": "x2"}]})

    monkeypatch.setattr(httpx.Client, "get", fake_get)

    result = ms.get_sample_assortment(limit=5)
    assert result == [{"id": "x1"}, {"id": "x2"}]

    
def test_get_all_rows_paginates(monkeypatch):
    monkeypatch.setenv("MOYSKLAD_TOKEN", "abc123")
    calls = []

    def fake_get(self, url, headers=None, params=None):
        calls.append(dict(params))
        if params["offset"] == 0:
            return FakeResponse(200, json_data={"rows": [{"id": "a"}, {"id": "b"}]})
        return FakeResponse(200, json_data={"rows": [{"id": "c"}]})

    monkeypatch.setattr(httpx.Client, "get", fake_get)

    result = ms._get_all_rows("https://fake/url", page_size=2)

    assert result == [{"id": "a"}, {"id": "b"}, {"id": "c"}]
    assert calls[0]["offset"] == 0
    assert calls[1]["offset"] == 2


def test_get_slots_calls_correct_url(monkeypatch):
    monkeypatch.setenv("MOYSKLAD_TOKEN", "abc123")
    captured = {}

    def fake_get(self, url, headers=None, params=None):
        captured["url"] = url
        return FakeResponse(200, json_data={"rows": [{"id": "slot-1", "name": "A-01"}]})

    monkeypatch.setattr(httpx.Client, "get", fake_get)

    result = ms.get_slots("store-123")

    assert captured["url"] == f"{ms.BASE_URL}/entity/store/store-123/slots"
    assert result == [{"id": "slot-1", "name": "A-01"}]

    
def test_extract_id_from_href():
    href = "https://api.moysklad.ru/api/remap/1.2/entity/store/abc/zones/49fbc0fe-6b91-11ef-0a80-187500181599"
    assert ms.extract_id_from_href(href) == "49fbc0fe-6b91-11ef-0a80-187500181599"


def test_extract_id_from_href_empty():
    assert ms.extract_id_from_href("") == ""