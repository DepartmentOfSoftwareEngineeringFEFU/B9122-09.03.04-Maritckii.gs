from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from .. import models, database, auth, schemas
from ..algorithms import graph, tsp, packing
from ..services.route_cache import get_cached_graph, generate_route_map
import os

router = APIRouter()
DEFAULT_TRAVEL_TIME = 60.0
SPEED_M_PER_SEC = 1.3
MIN_EDGES_FOR_MAP = 10

@router.post("/build/{order_id}", response_model=schemas.RouteResponse)
def build_route(order_id: str, current_user: models.User = Depends(auth.get_current_user), db: Session = Depends(database.get_db)):
    order = db.query(models.Order).filter(models.Order.id == order_id).first()
    if not order:
        raise HTTPException(404, "Заказ не найден")
    order_items_data = []
    unique_racks = set()
    for item in order.items:
        mat = db.query(models.Material).filter(models.Material.id == item.material_id).first()
        if not mat:
            continue
        unit_vol = mat.height * mat.width * mat.depth
        order_items_data.append({
            "material_id": mat.id,
            "rack": mat.rack,
            "qty": item.required_qty,
            "unit_weight": mat.weight,
            "unit_volume": unit_vol
        })
        unique_racks.add(mat.rack)
    edge_weights, adj_graph = get_cached_graph(db)
    locations = ["ISSUE"] + list(unique_racks)
    for i, loc1 in enumerate(locations):
        for j, loc2 in enumerate(locations):
            if i != j:
                if loc1 not in adj_graph:
                    adj_graph[loc1] = {}
                if loc2 not in adj_graph[loc1]:
                    adj_graph[loc1][loc2] = DEFAULT_TRAVEL_TIME
    tsp_route = tsp.solve_tsp(locations, edge_weights)
    MAX_W, MAX_V = 200.0, 2.0
    trips = packing.split_into_trips(tsp_route, order_items_data, MAX_W, MAX_V)
    steps = []
    step_num = 1
    total_time = 0.0
    cum_dist = 0.0
    for trip in trips:
        for i in range(len(trip) - 1):
            path = graph.dijkstra_path(adj_graph, trip[i], trip[i + 1])
            for j in range(len(path) - 1):
                t = adj_graph.get(path[j], {}).get(path[j + 1], DEFAULT_TRAVEL_TIME)
                dist = t * SPEED_M_PER_SEC
                cum_dist += dist
                steps.append(schemas.RouteStep(
                    step=step_num,
                    from_=path[j],
                    to=path[j + 1],
                    time_sec=t,
                    dist_m=dist,
                    cum_dist_m=cum_dist
                ))
                total_time += t
                step_num += 1
    segments = []
    full_png_url = ""
    map_warning = ""
    if len(edge_weights) >= MIN_EDGES_FOR_MAP:
        steps_dicts = [{"from": s.from_, "to": s.to} for s in steps]
        full_png_url = generate_route_map(order_id, steps_dicts, locations)
        if not full_png_url:
            map_warning = "Ошибка при генерации карты"
    else:
        map_warning = f"Недостаточно данных для карты (нужно {MIN_EDGES_FOR_MAP} рёбер, найдено {len(edge_weights)})"
    return schemas.RouteResponse(
        order_id=order_id,
        total_time_sec=total_time,
        total_distance_m=cum_dist,
        steps=steps,
        segments=segments,
        full_png_url=full_png_url,
        map_warning=map_warning
    )

@router.get("/map/{filename}")
def get_map_file(filename: str):
    filepath = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "static", "routes", filename)
    if not os.path.exists(filepath):
        raise HTTPException(404, "Файл карты не найден")
    return FileResponse(filepath, media_type="image/png")