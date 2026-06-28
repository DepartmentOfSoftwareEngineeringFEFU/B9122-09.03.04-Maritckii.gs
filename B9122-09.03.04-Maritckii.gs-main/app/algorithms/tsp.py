import numpy as np
from typing import List, Dict, Tuple

MAX_EXACT_LOCATIONS = 20

def solve_tsp(locations: List[str], dist_matrix: Dict[Tuple[str, str], float]) -> List[str]:
    n = len(locations)
    if n <= 1:
        return locations
    if not dist_matrix:
        return locations + [locations[0]]
    if n <= MAX_EXACT_LOCATIONS:
        return _held_karp(locations, dist_matrix)
    else:
        return _nearest_neighbor_2opt(locations, dist_matrix)

def _held_karp(locations: List[str], dist: Dict[Tuple[str, str], float]) -> List[str]:
    n = len(locations)
    if n < 2:
        return locations
    dp = [[float('inf')] * n for _ in range(1 << n)]
    parent = [[-1] * n for _ in range(1 << n)]
    for i in range(1, n):
        dp[1 << (i - 1)][i] = dist.get((locations[0], locations[i]), float('inf'))
        parent[1 << (i - 1)][i] = 0
    for mask in range(1, 1 << n):
        for i in range(1, n):
            if not (mask & (1 << (i - 1))):
                continue
            if dp[mask][i] == float('inf'):
                continue
            for j in range(1, n):
                if mask & (1 << (j - 1)):
                    continue
                next_mask = mask | (1 << (j - 1))
                new_cost = dp[mask][i] + dist.get((locations[i], locations[j]), float('inf'))
                if new_cost < dp[next_mask][j]:
                    dp[next_mask][j] = new_cost
                    parent[next_mask][j] = i
    full_mask = (1 << n) - 1
    last, best_cost = -1, float('inf')
    for i in range(1, n):
        cost = dp[full_mask][i] + dist.get((locations[i], locations[0]), float('inf'))
        if cost < best_cost:
            best_cost = cost
            last = i
    if last == -1:
        return locations + [locations[0]]
    path = []
    mask = full_mask
    cur = last
    while cur != 0 and cur > 0:
        path.append(cur)
        prev = parent[mask][cur]
        if prev < 0:
            break
        mask ^= (1 << (cur - 1))
        cur = prev
    path.append(0)
    path = path[::-1] + [0]
    return [locations[i] for i in path]

def _nearest_neighbor_2opt(locations: List[str], dist: Dict[Tuple[str, str], float]) -> List[str]:
    if len(locations) < 2:
        return locations
    unvisited = set(locations[1:])
    route = [locations[0]]
    curr = locations[0]
    while unvisited:
        candidates = [(loc, dist.get((curr, loc), float('inf'))) for loc in unvisited]
        if not candidates:
            break
        next_loc = min(candidates, key=lambda x: x[1])[0]
        route.append(next_loc)
        unvisited.remove(next_loc)
        curr = next_loc
    route.append(locations[0])
    return route