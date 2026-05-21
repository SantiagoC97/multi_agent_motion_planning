"""
pathfinding.py
==============
Algoritmos de búsqueda de rutas para SmartRide Planner.

El entorno se modela como una grilla 20x20, donde cada celda libre es un nodo
del grafo y cada movimiento cardinal válido representa una arista.

Algoritmos implementados:

    - A*
    - Dijkstra
    - BFS
    - Greedy Best-First Search

Todos retornan una ruta como lista de posiciones, sin incluir la posición
inicial e incluyendo la posición objetivo.
"""

from __future__ import annotations

import heapq
from collections import deque

from models import Position
from city_grid import CityGrid


ROUTE_ASTAR = "astar"
ROUTE_DIJKSTRA = "dijkstra"
ROUTE_BFS = "bfs"
ROUTE_GREEDY = "greedy"


ROUTE_ALGORITHM_LABELS = {
    ROUTE_ASTAR: "A*",
    ROUTE_DIJKSTRA: "Dijkstra",
    ROUTE_BFS: "BFS",
    ROUTE_GREEDY: "Greedy Best-First",
}


ROUTE_ALGORITHM_VALUE_BY_LABEL = {
    "A*": ROUTE_ASTAR,
    "Dijkstra": ROUTE_DIJKSTRA,
    "BFS": ROUTE_BFS,
    "Greedy Best-First": ROUTE_GREEDY,
}


def normalize_route_algorithm(route_algorithm: str | None) -> str:
    """
    Retorna un algoritmo válido. Si llega uno inválido, usa A*.
    """
    valid = {
        ROUTE_ASTAR,
        ROUTE_DIJKSTRA,
        ROUTE_BFS,
        ROUTE_GREEDY,
    }

    if route_algorithm in valid:
        return route_algorithm

    return ROUTE_ASTAR


def route_algorithm_explanation(route_algorithm: str) -> str:
    """
    Explicación corta para mostrar en la GUI.
    """
    route_algorithm = normalize_route_algorithm(route_algorithm)

    if route_algorithm == ROUTE_ASTAR:
        return "A*: usa costo acumulado g(n) + heurística Manhattan h(n)."

    if route_algorithm == ROUTE_DIJKSTRA:
        return "Dijkstra: expande el nodo con menor costo acumulado."

    if route_algorithm == ROUTE_BFS:
        return "BFS: explora por niveles; óptimo si cada paso pesa 1."

    if route_algorithm == ROUTE_GREEDY:
        return "Greedy Best-First: usa solo la heurística hacia el objetivo."

    return "A*: búsqueda informada sobre la grilla."


def heuristic(a: Position, b: Position) -> int:
    """
    Distancia Manhattan para grilla con movimientos cardinales.
    """
    return abs(a.row - b.row) + abs(a.col - b.col)


def reconstruct_path(
    came_from: dict[Position, Position | None],
    current: Position,
) -> list[Position]:
    """
    Reconstruye la ruta desde el objetivo hasta el inicio.
    """
    path: list[Position] = []

    while came_from[current] is not None:
        path.append(current)
        current = came_from[current]

    path.reverse()
    return path


def _prepare_blocked_positions(
    start: Position,
    goal: Position,
    blocked_positions: set[Position] | None,
) -> set[Position]:
    """
    Prepara las posiciones bloqueadas temporalmente.
    """
    if blocked_positions is None:
        blocked_positions = set()

    blocked = set(blocked_positions)
    blocked.discard(start)
    blocked.discard(goal)

    return blocked


def _valid_problem(
    city_grid: CityGrid,
    start: Position,
    goal: Position,
) -> bool:
    """
    Verifica que inicio y destino sean válidos.
    """
    if not city_grid.in_bounds(start):
        return False

    if not city_grid.in_bounds(goal):
        return False

    if city_grid.is_obstacle(start):
        return False

    if city_grid.is_obstacle(goal):
        return False

    return True


def astar(
    city_grid: CityGrid,
    start: Position,
    goal: Position,
    blocked_positions: set[Position] | None = None,
) -> list[Position]:
    """
    A* con heurística Manhattan.

    f(n) = g(n) + h(n)
    """
    if not _valid_problem(city_grid, start, goal):
        return []

    if start == goal:
        return []

    blocked = _prepare_blocked_positions(start, goal, blocked_positions)

    came_from: dict[Position, Position | None] = {start: None}
    g_score: dict[Position, int] = {start: 0}

    open_set: list[tuple[int, int, Position]] = []
    counter = 0

    heapq.heappush(open_set, (heuristic(start, goal), counter, start))

    while open_set:
        _f_score, _tie, current = heapq.heappop(open_set)

        if current == goal:
            return reconstruct_path(came_from, current)

        for neighbor in city_grid.get_neighbors(current):
            if neighbor in blocked:
                continue

            tentative_g = g_score[current] + 1

            if neighbor not in g_score or tentative_g < g_score[neighbor]:
                came_from[neighbor] = current
                g_score[neighbor] = tentative_g

                counter += 1
                f_score = tentative_g + heuristic(neighbor, goal)

                heapq.heappush(open_set, (f_score, counter, neighbor))

    return []


def bfs(
    city_grid: CityGrid,
    start: Position,
    goal: Position,
    blocked_positions: set[Position] | None = None,
) -> list[Position]:
    """
    Breadth-First Search.

    En una grilla no ponderada, BFS encuentra una ruta mínima en número
    de pasos porque explora por niveles.
    """
    if not _valid_problem(city_grid, start, goal):
        return []

    if start == goal:
        return []

    blocked = _prepare_blocked_positions(start, goal, blocked_positions)

    queue: deque[Position] = deque([start])
    came_from: dict[Position, Position | None] = {start: None}
    visited: set[Position] = {start}

    while queue:
        current = queue.popleft()

        if current == goal:
            return reconstruct_path(came_from, current)

        for neighbor in city_grid.get_neighbors(current):
            if neighbor in blocked:
                continue

            if neighbor in visited:
                continue

            visited.add(neighbor)
            came_from[neighbor] = current
            queue.append(neighbor)

    return []


def dijkstra(
    city_grid: CityGrid,
    start: Position,
    goal: Position,
    blocked_positions: set[Position] | None = None,
) -> list[Position]:
    """
    Dijkstra para costos no negativos.

    En esta grilla cada movimiento tiene costo 1. Por eso puede entregar
    rutas equivalentes a BFS, pero el mecanismo de expansión se basa en
    costo acumulado.
    """
    if not _valid_problem(city_grid, start, goal):
        return []

    if start == goal:
        return []

    blocked = _prepare_blocked_positions(start, goal, blocked_positions)

    came_from: dict[Position, Position | None] = {start: None}
    distance: dict[Position, int] = {start: 0}

    open_set: list[tuple[int, int, Position]] = []
    counter = 0

    heapq.heappush(open_set, (0, counter, start))

    while open_set:
        current_cost, _tie, current = heapq.heappop(open_set)

        if current == goal:
            return reconstruct_path(came_from, current)

        if current_cost > distance.get(current, float("inf")):
            continue

        for neighbor in city_grid.get_neighbors(current):
            if neighbor in blocked:
                continue

            new_cost = current_cost + 1

            if new_cost < distance.get(neighbor, float("inf")):
                distance[neighbor] = new_cost
                came_from[neighbor] = current

                counter += 1
                heapq.heappush(open_set, (new_cost, counter, neighbor))

    return []


def greedy_best_first(
    city_grid: CityGrid,
    start: Position,
    goal: Position,
    blocked_positions: set[Position] | None = None,
) -> list[Position]:
    """
    Greedy Best-First Search.

    Usa únicamente h(n), es decir, la distancia heurística al objetivo.
    Puede ser rápido, pero no garantiza la ruta más corta.
    """
    if not _valid_problem(city_grid, start, goal):
        return []

    if start == goal:
        return []

    blocked = _prepare_blocked_positions(start, goal, blocked_positions)

    came_from: dict[Position, Position | None] = {start: None}
    visited: set[Position] = {start}

    open_set: list[tuple[int, int, Position]] = []
    counter = 0

    heapq.heappush(open_set, (heuristic(start, goal), counter, start))

    while open_set:
        _h_score, _tie, current = heapq.heappop(open_set)

        if current == goal:
            return reconstruct_path(came_from, current)

        for neighbor in city_grid.get_neighbors(current):
            if neighbor in blocked:
                continue

            if neighbor in visited:
                continue

            visited.add(neighbor)
            came_from[neighbor] = current

            counter += 1
            h_score = heuristic(neighbor, goal)

            heapq.heappush(open_set, (h_score, counter, neighbor))

    return []


def find_path(
    city_grid: CityGrid,
    start: Position,
    goal: Position,
    route_algorithm: str = ROUTE_ASTAR,
    blocked_positions: set[Position] | None = None,
) -> list[Position]:
    """
    Selector general de algoritmo de ruta.
    """
    route_algorithm = normalize_route_algorithm(route_algorithm)

    if route_algorithm == ROUTE_ASTAR:
        return astar(
            city_grid=city_grid,
            start=start,
            goal=goal,
            blocked_positions=blocked_positions,
        )

    if route_algorithm == ROUTE_DIJKSTRA:
        return dijkstra(
            city_grid=city_grid,
            start=start,
            goal=goal,
            blocked_positions=blocked_positions,
        )

    if route_algorithm == ROUTE_BFS:
        return bfs(
            city_grid=city_grid,
            start=start,
            goal=goal,
            blocked_positions=blocked_positions,
        )

    if route_algorithm == ROUTE_GREEDY:
        return greedy_best_first(
            city_grid=city_grid,
            start=start,
            goal=goal,
            blocked_positions=blocked_positions,
        )

    return astar(
        city_grid=city_grid,
        start=start,
        goal=goal,
        blocked_positions=blocked_positions,
    )