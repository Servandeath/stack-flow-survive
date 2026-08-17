"""
Разовый прогон против реального МойСклад — не автотест, а инструмент разведки.

Запуск (из backend/, при активном .venv):
    python scripts/smoke_test_stock.py
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.services.moysklad_client import (
    BASE_URL,
    _get_with_retry,
    get_sample_assortment,
    get_slots,
    get_stock_by_cells,
)


def inspect_store(store_id: str) -> None:
    print(f"\nЗапрашиваю сущность store/{store_id}...")
    store = _get_with_retry(f"{BASE_URL}/entity/store/{store_id}")
    print(json.dumps(store, ensure_ascii=False, indent=2))


def inspect_slots(store_id: str, known_slot_ids: list[str]) -> None:
    print(f"\nЗапрашиваю ячейки склада {store_id}...")
    slots = get_slots(store_id)
    print(f"Всего ячеек: {len(slots)}")

    print("\nПервые 3 ячейки (структура полей):")
    for slot in slots[:3]:
        print(json.dumps(slot, ensure_ascii=False, indent=2))

    by_id = {s["id"]: s for s in slots}
    print("\nНазвания конкретных ячеек из отчёта об остатках:")
    for slot_id in known_slot_ids:
        slot = by_id.get(slot_id)
        name = slot.get("name") if slot else "НЕ НАЙДЕНА"
        print(f"  {slot_id} -> {name}")


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
    print(json.dumps(stock_report, ensure_ascii=False, indent=2))

    if stock_report:
        store_id = stock_report[0]["storeId"]
        inspect_store(store_id)
        known_slot_ids = [row["slotId"] for row in stock_report]
        inspect_slots(store_id, known_slot_ids)


if __name__ == "__main__":
    main()