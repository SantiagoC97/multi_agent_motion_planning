"""
assignment.py
=============
Módulo de asignación de taxis a usuarios para SmartRide Planner.

Este módulo decide qué taxi disponible debe atender a qué usuario pendiente.

La asignación se realiza con una estrategia greedy configurable. Para cada
par taxi-usuario se calcula:

    - Ruta A*.
    - Costo de ruta.
    - Score según la estrategia seleccionada.

Estrategias disponibles:
    - distance:
        Asigna por menor distancia.

    - priority:
        Favorece usuarios con mayor prioridad.

    - waiting:
        Favorece usuarios con mayor tiempo de espera.

    - weighted:
        Combina distancia, prioridad y espera.

La solución sigue siendo greedy, por tanto no garantiza siempre el óptimo
global, pero es eficiente, clara y adecuada para el contexto académico
del proyecto.
"""

from __future__ import annotations

from models import Taxi, UserRequest
from city_grid import CityGrid
from pathfinding import ROUTE_ASTAR, find_path
from decision_policy import (
    STRATEGY_DISTANCE,
    assignment_score,
    normalize_strategy,
)


# Una asignación es:
# (taxi_id, user_id, costo_de_ruta)
Assignment = tuple[int, int, int]


# ---------------------------------------------------------------------------
# 1. Costo de ruta
# ---------------------------------------------------------------------------

def route_cost(route: list) -> int:
    """
    Calcula el costo de una ruta como su número de pasos.

    Args:
        route (list): Lista de posiciones de la ruta.

    Returns:
        int: Longitud de la ruta.
    """
    return len(route)


# ---------------------------------------------------------------------------
# 2. Asignación principal
# ---------------------------------------------------------------------------

def assign_taxis_to_users(
    city_grid: CityGrid,
    strategy: str = STRATEGY_DISTANCE,
    route_algorithm: str = ROUTE_ASTAR,
) -> list[Assignment]:
    """
    Asigna taxis disponibles a usuarios pendientes usando una estrategia greedy.

    Args:
        city_grid (CityGrid): Grilla con taxis, usuarios y obstáculos.
        strategy (str): Estrategia de asignación.

    Returns:
        list[Assignment]: Lista de asignaciones realizadas.
    """
    strategy = normalize_strategy(strategy)

    available_taxis: list[Taxi] = [
        taxi
        for taxi in city_grid.taxis
        if taxi.is_available
    ]

    pending_users: list[UserRequest] = [
        user
        for user in city_grid.users
        if user.is_unassigned
    ]

    if not available_taxis or not pending_users:
        return []

    # Cada candidato contiene:
    # (score, costo, taxi_id, user_id, taxi, user, route)
    candidate_pairs: list[
        tuple[float, int, int, int, Taxi, UserRequest, list]
    ] = []

    for taxi in available_taxis:
        for user in pending_users:

            route = find_path(
                city_grid=city_grid,
                start=taxi.position,
                goal=user.position,
                route_algorithm=route_algorithm,
            )

            if not route and taxi.position != user.position:
                continue

            cost = route_cost(route)

            score = assignment_score(
                taxi=taxi,
                user=user,
                route_cost=cost,
                strategy=strategy,
            )

            candidate_pairs.append(
                (
                    score,
                    cost,
                    taxi.id,
                    user.id,
                    taxi,
                    user,
                    route,
                )
            )

    if not candidate_pairs:
        return []

    # Orden:
    # 1. Mejor score según estrategia.
    # 2. Menor distancia como desempate.
    # 3. ID de taxi.
    # 4. ID de usuario.
    candidate_pairs.sort(
        key=lambda item: (
            item[0],
            item[1],
            item[2],
            item[3],
        )
    )

    assigned_taxi_ids: set[int] = set()
    assigned_user_ids: set[int] = set()

    assignments: list[Assignment] = []

    for _score, cost, _taxi_id, _user_id, taxi, user, route in candidate_pairs:

        if taxi.id in assigned_taxi_ids:
            continue

        if user.id in assigned_user_ids:
            continue

        taxi.assign_user(user.id, route)
        user.assigned = True

        assigned_taxi_ids.add(taxi.id)
        assigned_user_ids.add(user.id)

        assignments.append(
            (
                taxi.id,
                user.id,
                cost,
            )
        )

    return assignments