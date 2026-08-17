"""
Разовый прогон против реального МойСклад — не автотест, а инструмент разведки.
Берёт несколько настоящих товаров из аккаунта и смотрит по ним живые остатки
по ячейкам, чтобы увидеть реальную структуру ответа report/stock/byslot/current.

Запуск (из backend/, при активном .venv):
    python scripts/smoke_test_stock.py
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.services.moysklad_client import get_sample_assortment, get_stock_by_cells


def main() -> None:
    print("Беру несколько реальных товаров из аккаунта...")
    sample = get_sample_assortment(limit=5)

    if not sample:
        print("Товары не найдены — проверьте .env и наличие товаров в аккаунте.")
        return

    print(f"Получено {len(sample)} товаров:")
    assortment_ids = []
    for item in sample:
        item_id = item.get("id", "")
        name = item.get("name", "(без имени)")
        assortment_ids.append(item_id)
        print(f"  - {name} ({item_id})")

    print("\nЗапрашиваю текущие остатки по ячейкам для этих товаров...\n")
    stock_report = get_stock_by_cells(assortment_ids)

    print("Сырой ответ report/stock/byslot/current:")
    print("Сырой ответ report/stock/byslot/current:")
    print(json.dumps(stock_report, ensure_ascii=False, indent=2))

    if stock_report:
        inspect_store(stock_report[0]["storeId"])


def inspect_store(store_id: str) -> None:
    """
    Разведка: смотрим, что API реально отдаёт по складу — вдруг зоны/ячейки
    вложены прямо в сущность store, а не отдельным методом.
    """
    from app.services.moysklad_client import BASE_URL, _get_with_retry

    print(f"\nЗапрашиваю сущность store/{store_id}...")
    store = _get_with_retry(f"{BASE_URL}/entity/store/{store_id}")
    print(json.dumps(store, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()