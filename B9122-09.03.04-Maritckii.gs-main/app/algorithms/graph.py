import heapq
from collections import defaultdict
from typing import List, Dict, Tuple

def calculate_robust_weights(logs: List[Tuple]) -> Dict[Tuple[str, str], float]:
    edge_times = defaultdict(list)
    for ts, f_loc, t_loc in logs:
        if f_loc != t_loc:
            edge_times[(f_loc, t_loc)].append(ts)
    weights = {}
    for (u, v), times in edge_times.items():
        if len(times) < 3:
            continue
        times.sort()
        k = max(1, int(len(times) * 0.1))
        trimmed = times[k:-k] if len(times) > 2 * k else times
        avg_time = sum(trimmed) / len(trimmed)
        weights[(u, v)] = avg_time
        weights[(v, u)] = avg_time
    return weights

def dijkstra_path(graph: Dict[str, Dict[str, float]], start: str, goal: str) -> List[str]:
    if start == goal:
        return [start]
    dist = {start: 0.0}
    parent = {start: None}
    heap = [(0.0, start)]
    while heap:
        d, u = heapq.heappop(heap)
        if u == goal:
            break
        if d > dist.get(u, float('inf')):
            continue
        for v, w in graph.get(u, {}).items():
            nd = d + w
            if nd < dist.get(v, float('inf')):
                dist[v] = nd
                parent[v] = u
                heapq.heappush(heap, (nd, v))
    if goal not in dist:
        return []
    path = []
    cur = goal
    while cur is not None:
        path.append(cur)
        cur = parent.get(cur)
    return path[::-1]