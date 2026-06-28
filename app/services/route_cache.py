# app/services/route_cache.py
"""
Кэш для графа перемещений и генератор карт маршрутов.
"""
import os
import matplotlib

matplotlib.use('Agg')  # Без GUI
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from typing import Dict, Tuple, List, Optional
from sqlalchemy.orm import Session
from .. import models
from ..algorithms import graph
import time

# 🔥 Глобальный кэш графа
_cached_graph: Optional[Dict[Tuple[str, str], float]] = None
_cached_adj_graph: Optional[Dict[str, Dict[str, float]]] = None
_cache_timestamp: Optional[float] = None
CACHE_TTL = 3600  # Время жизни кэша (1 час)

# Путь для сохранения карт
MAPS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
                        "static", "routes")


def get_cached_graph(db: Session) -> Tuple[Dict[Tuple[str, str], float], Dict[str, Dict[str, float]]]:
    """
    Возвращает кэшированный граф или пересчитывает его.
    """
    global _cached_graph, _cached_adj_graph, _cache_timestamp

    # Проверяем, нужен ли пересчёт
    current_time = time.time()
    if _cached_graph is not None and _cache_timestamp is not None:
        if current_time - _cache_timestamp < CACHE_TTL:
            print(f"✅ Используем кэшированный граф (возраст: {current_time - _cache_timestamp:.0f}с)")
            return _cached_graph, _cached_adj_graph

    # Пересчитываем граф
    print("🔄 Пересчёт графа из БД...")
    start_time = time.time()

    logs = db.query(models.MovementLog).all()
    print(f"📊 Загружено {len(logs)} записей о перемещениях")

    formatted_logs = [(l.duration_sec, l.from_loc, l.to_loc) for l in logs]
    edge_weights = graph.calculate_robust_weights(formatted_logs)

    # Создаём adjacency list
    adj_graph = {}
    for (u, v), w in edge_weights.items():
        if u not in adj_graph:
            adj_graph[u] = {}
        adj_graph[u][v] = w

    # Кэшируем
    _cached_graph = edge_weights
    _cached_adj_graph = adj_graph
    _cache_timestamp = current_time

    elapsed = time.time() - start_time
    print(f"✅ Граф пересчитан за {elapsed:.2f}с, рёбер: {len(edge_weights)}")

    return edge_weights, adj_graph


def generate_route_map(
        order_id: str,
        steps: List[dict],
        locations: List[str]
) -> str:
    """
    Генерирует PNG-карту маршрута.
    Возвращает путь к файлу.
    """
    os.makedirs(MAPS_DIR, exist_ok=True)
    filepath = os.path.join(MAPS_DIR, f"{order_id}_full.png")

    try:
        # Создаём фигуру
        fig, ax = plt.subplots(figsize=(12, 8))

        # 🔥 Координаты стеллажей (упрощённая схема склада)
        rack_coords = {}

        # ISSUE (точка выдачи) — в центре слева
        rack_coords['ISSUE'] = (0, 0)

        # Стеллажи располагаем по сетке
        for loc in locations:
            if loc == 'ISSUE':
                continue
            # Парсим имя стеллажа (например, "C30")
            if len(loc) >= 2:
                letter = loc[0]
                number = int(loc[1:])
                # X координата — по букве (A=1, B=2, ...)
                x = (ord(letter) - ord('A') + 1) * 2
                # Y координата — по номеру
                y = number * 0.5
                rack_coords[loc] = (x, y)
            else:
                rack_coords[loc] = (5, 5)  # Дефолт

        # Рисуем стеллажи
        for loc, (x, y) in rack_coords.items():
            if loc == 'ISSUE':
                # ISSUE — красный квадрат
                rect = patches.Rectangle((x - 0.5, y - 0.5), 1, 1,
                                         linewidth=2, edgecolor='red', facecolor='red', alpha=0.3)
                ax.add_patch(rect)
                ax.text(x, y, 'ISSUE', ha='center', va='center',
                        fontsize=10, fontweight='bold', color='red')
            else:
                # Стеллажи — синие квадраты
                rect = patches.Rectangle((x - 0.3, y - 0.3), 0.6, 0.6,
                                         linewidth=1, edgecolor='blue', facecolor='lightblue', alpha=0.5)
                ax.add_patch(rect)
                ax.text(x, y, loc, ha='center', va='center', fontsize=8)

        # Рисуем маршрут
        if steps:
            route_x = []
            route_y = []

            for step in steps:
                from_loc = step['from']
                to_loc = step['to']

                if from_loc in rack_coords and to_loc in rack_coords:
                    x1, y1 = rack_coords[from_loc]
                    x2, y2 = rack_coords[to_loc]

                    route_x.extend([x1, x2])
                    route_y.extend([y1, y2])

            if route_x:
                ax.plot(route_x, route_y, 'g-', linewidth=2, marker='o',
                        markersize=6, label='Маршрут')

        # Настройки графика
        ax.set_xlabel('X координата (м)')
        ax.set_ylabel('Y координата (м)')
        ax.set_title(f'Маршрут сборки заказа {order_id}')
        ax.grid(True, alpha=0.3)
        ax.legend()
        ax.axis('equal')

        # Сохраняем
        plt.tight_layout()
        plt.savefig(filepath, dpi=150, bbox_inches='tight')
        plt.close()

        print(f"✅ Карта сохранена: {filepath}")
        return f"/static/routes/{order_id}_full.png"

    except Exception as e:
        print(f"❌ Ошибка при генерации карты: {e}")
        return ""