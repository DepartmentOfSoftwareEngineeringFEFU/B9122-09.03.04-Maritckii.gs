# scripts/generate_history.py
"""
Генератор истории перемещений сборщиков на складе.
Создаёт ~1 млн записей для калибровки графа.
"""
import csv
import os
import random
from datetime import datetime, timedelta

# Настройки
OUTPUT_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)),
                           "data", "movements_history.csv")
NUM_RECORDS = 1_000_000  # 1 миллион записей

# Стеллажи склада (буква A-Z + номер 1-99)
AISLES = [chr(i) for i in range(ord('A'), ord('Z') + 1)]  # A-Z
SECTIONS = list(range(1, 100))  # 1-99
RACKS = [f"{a}{n}" for a in AISLES for n in SECTIONS]  # A1..Z99 = 2599 стеллажей

# Точки
ISSUE_POINT = "ISSUE"
ALL_LOCATIONS = [ISSUE_POINT] + RACKS

# Работники
WORKERS = [f"worker{i}" for i in range(1, 21)]  # 20 сборщиков


# Скорость движения (секунд на переход)
def get_travel_time(from_loc: str, to_loc: str) -> float:
    """Расчётное время перемещения между точками (приближённо)."""
    if from_loc == to_loc:
        return 0.0

    # ISSUE → стеллаж или стеллаж → ISSUE
    if from_loc == ISSUE_POINT or to_loc == ISSUE_POINT:
        # Среднее время до стеллажа зависит от буквы (расстояния)
        rack = to_loc if from_loc == ISSUE_POINT else from_loc
        if len(rack) >= 2:
            letter = rack[0]
            number = int(rack[1:])
            # Расстояние растёт с номером буквы и секции
            distance = (ord(letter) - ord('A') + 1) * 10 + number * 0.5
            return distance + random.uniform(-5, 5)
        return 60.0

    # Между стеллажами
    def parse_rack(r):
        return (ord(r[0]) - ord('A'), int(r[1:]))

    l1, n1 = parse_rack(from_loc)
    l2, n2 = parse_rack(to_loc)

    # Манхэттенское расстояние
    distance = abs(l1 - l2) * 10 + abs(n1 - n2) * 0.5
    return distance + random.uniform(-3, 3)


def generate_session(worker_id: str, start_time: datetime, num_picks: int):
    """Генерирует одну сессию сборки заказа."""
    records = []
    current_loc = ISSUE_POINT
    current_time = start_time

    # Выбираем случайные стеллажи для picks
    picks = random.sample(RACKS, min(num_picks, len(RACKS)))

    for rack in picks:
        # Переход к стеллажу
        travel_time = max(5.0, get_travel_time(current_loc, rack))
        current_time += timedelta(seconds=travel_time)

        records.append({
            'timestamp': current_time.strftime('%Y-%m-%d %H:%M:%S'),
            'from_loc': current_loc,
            'to_loc': rack,
            'duration_sec': round(travel_time, 2),
            'worker_id': worker_id,
            'session_id': f"session_{worker_id}_{start_time.strftime('%Y%m%d_%H%M%S')}"
        })

        # Время на сборку (10-30 сек)
        current_time += timedelta(seconds=random.uniform(10, 30))
        current_loc = rack

    # Возврат на ISSUE
    if current_loc != ISSUE_POINT:
        travel_time = max(5.0, get_travel_time(current_loc, ISSUE_POINT))
        current_time += timedelta(seconds=travel_time)

        records.append({
            'timestamp': current_time.strftime('%Y-%m-%d %H:%M:%S'),
            'from_loc': current_loc,
            'to_loc': ISSUE_POINT,
            'duration_sec': round(travel_time, 2),
            'worker_id': worker_id,
            'session_id': f"session_{worker_id}_{start_time.strftime('%Y%m%d_%H%M%S')}"
        })

    return records


def main():
    print(f"🚀 Генерация {NUM_RECORDS} записей истории перемещений...")
    print(f"📁 Выходной файл: {OUTPUT_FILE}")

    # Создаём папку
    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)

    # Удаляем старый файл
    if os.path.exists(OUTPUT_FILE):
        os.remove(OUTPUT_FILE)

    # Генерируем сессии
    session_start = datetime(2024, 1, 1, 8, 0, 0)
    total_records = 0
    session_count = 0

    with open(OUTPUT_FILE, 'w', encoding='utf-8', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['timestamp', 'from_loc', 'to_loc', 'duration_sec',
                         'worker_id', 'session_id'])

        while total_records < NUM_RECORDS:
            # Выбираем работника
            worker = random.choice(WORKERS)

            # Генерируем сессию (3-15 picks)
            num_picks = random.randint(3, 15)
            records = generate_session(worker, session_start, num_picks)

            for record in records:
                writer.writerow([
                    record['timestamp'],
                    record['from_loc'],
                    record['to_loc'],
                    record['duration_sec'],
                    record['worker_id'],
                    record['session_id']
                ])
                total_records += 1

                if total_records >= NUM_RECORDS:
                    break

            session_count += 1

            # Следующая сессия через 30-120 минут
            session_start += timedelta(minutes=random.randint(30, 120))

            # Прогресс
            if session_count % 1000 == 0:
                print(f"  📊 Сгенерировано {total_records} записей ({session_count} сессий)")

    print(f"✅ Готово! Сгенерировано {total_records} записей в {session_count} сессиях")
    print(f"📁 Файл сохранён: {OUTPUT_FILE}")
    print(f"💾 Размер файла: {os.path.getsize(OUTPUT_FILE) / 1024 / 1024:.2f} МБ")


if __name__ == "__main__":
    main()