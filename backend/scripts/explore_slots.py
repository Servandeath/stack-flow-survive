"""
Разведка: группирует все ячейки по залам/зонам и показывает выборку названий —
чтобы увидеть реальные паттерны именования до того, как писать парсер.

Запуск (из backend/, при активном .venv):
    python scripts/explore_slots.py <store_id>
"""
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.services.moysklad_client import extract_id_from_href, get_slots, get_zones

SAMPLE_SIZE = 20


def main() -> None:
    if len(sys.argv) < 2:
        print("Использование: python scripts/explore_slots.py <store_id>")
        return

    store_id = sys.argv[1]

    print("Загружаю зоны...")
    zones = get_zones(store_id)
    zone_names = {z["id"]: z.get("name", "(без имени)") for z in zones}
    print(f"Зон: {len(zones)}")

    print("Загружаю ячейки (может занять время, их 2000+)...")
    slots = get_slots(store_id)
    print(f"Ячеек всего: {len(slots)}\n")

    by_zone = defaultdict(list)
    no_zone = []

    for slot in slots:
        zone_href = (slot.get("zone") or {}).get("meta", {}).get("href", "")
        zone_id = extract_id_from_href(zone_href)
        if zone_id:
            by_zone[zone_id].append(slot["name"])
        else:
            no_zone.append(slot["name"])

    for zone_id, names in by_zone.items():
        zone_name = zone_names.get(zone_id, "(неизвестная зона)")
        print(f"=== {zone_name} ({len(names)} ячеек) ===")
        for name in names[:SAMPLE_SIZE]:
            print(f"  {name}")
        if len(names) > SAMPLE_SIZE:
            print(f"  ... и ещё {len(names) - SAMPLE_SIZE}")
        print()

    if no_zone:
        print(f"=== БЕЗ ЗОНЫ ({len(no_zone)} ячеек) ===")
        for name in no_zone[:SAMPLE_SIZE]:
            print(f"  {name}")


if __name__ == "__main__":
    main()