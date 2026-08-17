"""
Клиент для МойСклад JSON API 1.2.

Авторизация: логин/пароль (Basic Auth) или токен (Bearer) — из .env.
Если задан MOYSKLAD_TOKEN, используется он; иначе логин/пароль.
"""
import base64
import os
import time

import httpx
from dotenv import load_dotenv

load_dotenv()

BASE_URL = "https://api.moysklad.ru/api/remap/1.2"

RETRY_ATTEMPTS = 6
RETRY_BASE_SLEEP = 0.8  # секунд * номер попытки — тот же паттерн, что в GAS-скриптах


class MoySkladError(Exception):
    """Ошибка запроса к МойСклад API после всех попыток."""


def _build_auth_header() -> str:
    token = os.getenv("MOYSKLAD_TOKEN")
    if token:
        return f"Bearer {token}"

    login = os.getenv("MOYSKLAD_LOGIN")
    password = os.getenv("MOYSKLAD_PASSWORD")
    if not login or not password:
        raise MoySkladError(
            "Не заданы MOYSKLAD_TOKEN или MOYSKLAD_LOGIN/MOYSKLAD_PASSWORD в .env"
        )
    raw = f"{login}:{password}".encode("utf-8")
    return "Basic " + base64.b64encode(raw).decode("ascii")


def _headers() -> dict:
    return {
        "Authorization": _build_auth_header(),
        "Accept-Encoding": "gzip",
        "Accept": "application/json;charset=utf-8",
    }


def _get_with_retry(url: str, params: dict | None = None) -> dict:
    """GET с ретраями на 429/5xx — тот же паттерн, что fetchJsonWithRetry_ в GAS."""
    last_error = ""
    with httpx.Client(timeout=30.0) as client:
        for attempt in range(1, RETRY_ATTEMPTS + 1):
            try:
                response = client.get(url, headers=_headers(), params=params)
            except httpx.RequestError as exc:
                last_error = str(exc)
                time.sleep(RETRY_BASE_SLEEP * attempt)
                continue

            if response.status_code == 200:
                return response.json()

            if response.status_code == 429 or response.status_code >= 500:
                last_error = f"HTTP {response.status_code}: {response.text[:300]}"
                time.sleep(RETRY_BASE_SLEEP * attempt)
                continue

            # 4xx кроме 429 — повторять бессмысленно, ошибка в самом запросе
            raise MoySkladError(f"HTTP {response.status_code}: {response.text[:500]}")

    raise MoySkladError(
        f"Не удалось получить ответ после {RETRY_ATTEMPTS} попыток. Последняя ошибка: {last_error}"
    )


def get_stock_by_cells(assortment_ids: list[str], store_ids: list[str] | None = None) -> dict:
    """
    Текущие остатки по ячейкам для списка товаров/модификаций.

    assortment_ids — UUID (поле id объекта assortment из позиций заказа),
                      НЕ артикул и не штрихкод.
    store_ids       — опционально, UUID складов, чтобы сузить выборку.

    Возвращает сырой JSON отчёта как есть — точную структуру строк ответа
    разберём по первому реальному вызову, не угадываем поля заранее.
    """
    if not assortment_ids:
        raise ValueError("assortment_ids не может быть пустым")

    filter_parts = ["assortmentId=" + ",".join(assortment_ids)]
    if store_ids:
        filter_parts.append("storeId=" + ",".join(store_ids))

    params = {"filter": ";".join(filter_parts)}
    url = f"{BASE_URL}/report/stock/byslot/current"
    return _get_with_retry(url, params=params)