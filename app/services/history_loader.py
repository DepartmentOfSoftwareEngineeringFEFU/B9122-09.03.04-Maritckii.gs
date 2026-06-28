# app/services/history_loader.py
import csv
import os
from datetime import datetime
from typing import List, Tuple
from sqlalchemy.orm import Session
from .. import models

# Путь к файлу с историей (относительно корня проекта)
HISTORY_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
                            "data", "movements_history.csv")


def load_history_to_db(db: Session) -> int:
    """
    Загружает исторические данные о перемещениях из CSV в БД.
    Возвращает количество загруженных записей.
    """
    if not os.path.exists(HISTORY_FILE):
        print(f"⚠️ Файл истории не найден: {HISTORY_FILE}")
        return 0

    # Проверяем, есть ли уже данные в БД
    existing_count = db.query(models.MovementLog).count()
    if existing_count > 0:
        print(f"ℹ️ В БД уже есть {existing_count} записей о перемещениях. Пропускаем загрузку.")
        return 0

    count = 0
    try:
        with open(HISTORY_FILE, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                try:
                    # Создаём запись о перемещении
                    log = models.MovementLog(
                        worker_id=1,  # Для истории используем ID=1
                        from_loc=row['from_loc'],
                        to_loc=row['to_loc'],
                        duration_sec=float(row['duration_sec']),
                        timestamp=datetime.strptime(row['timestamp'], '%Y-%m-%d %H:%M:%S')
                    )
                    db.add(log)
                    count += 1
                except Exception as e:
                    print(f"⚠️ Ошибка при загрузке строки: {e}")
                    continue

        db.commit()
        print(f"✅ Загружено {count} записей из {HISTORY_FILE}")
    except Exception as e:
        print(f"❌ Ошибка при загрузке истории: {e}")
        db.rollback()

    return count


def append_movement_to_csv(from_loc: str, to_loc: str, duration_sec: float, worker_id: int):
    """
    Добавляет новое перемещение в CSV-файл (для сохранения истории).
    """
    try:
        # Создаём папку, если её нет
        os.makedirs(os.path.dirname(HISTORY_FILE), exist_ok=True)

        # Проверяем, существует ли файл
        file_exists = os.path.exists(HISTORY_FILE)

        with open(HISTORY_FILE, 'a', encoding='utf-8', newline='') as f:
            writer = csv.writer(f)

            # Если файл новый — пишем заголовок
            if not file_exists:
                writer.writerow(['timestamp', 'from_loc', 'to_loc', 'duration_sec', 'worker_id', 'session_id'])

            # Пишем строку
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            session_id = f"session_{worker_id}_{int(datetime.now().timestamp())}"
            writer.writerow([timestamp, from_loc, to_loc, duration_sec, worker_id, session_id])

        print(f"📝 Новое перемещение записано в CSV: {from_loc} → {to_loc} ({duration_sec}с)")
    except Exception as e:
        print(f"⚠️ Ошибка при записи в CSV: {e}")