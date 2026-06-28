from typing import List, Dict, Tuple

def split_into_trips(
    tsp_route: List[str],
    order_items: List[Dict],
    max_weight: float,
    max_volume: float
) -> List[List[str]]:
    trips = []
    current_trip = ["ISSUE"]
    cur_w, cur_v = 0.0, 0.0
    loc_items = {}
    for item in order_items:
        rack = item['rack']
        if rack not in loc_items:
            loc_items[rack] = []
        loc_items[rack].append(item)
    for loc in tsp_route:
        if loc == "ISSUE":
            continue
        if loc not in loc_items:
            continue
        for item in loc_items[loc]:
            unit_w = item['unit_weight']
            unit_v = item['unit_volume']
            qty = item['qty']
            if unit_w > max_weight or unit_v > max_volume:
                if len(current_trip) > 1:
                    current_trip.append("ISSUE")
                    trips.append(current_trip)
                for _ in range(qty):
                    trips.append(["ISSUE", loc, "ISSUE"])
                current_trip = ["ISSUE"]
                cur_w, cur_v = 0.0, 0.0
                continue
            for _ in range(qty):
                if cur_w + unit_w > max_weight or cur_v + unit_v > max_volume:
                    current_trip.append("ISSUE")
                    trips.append(current_trip)
                    current_trip = ["ISSUE"]
                    cur_w, cur_v = 0.0, 0.0
                if current_trip[-1] != loc:
                    current_trip.append(loc)
                cur_w += unit_w
                cur_v += unit_v
    if len(current_trip) > 1:
        if current_trip[-1] != "ISSUE":
            current_trip.append("ISSUE")
        trips.append(current_trip)
    return trips if trips else [["ISSUE"]]