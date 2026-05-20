"""
assignment.py
=============
Módulo de asignación de taxis a usuarios para el SmartRide Planner.

Estrategia utilizada: **Asignación greedy por costo mínimo de ruta**.
    1. Se calculan todas las rutas posibles entre taxis disponibles y
       usuarios pendientes usando el algoritmo A*.
    2. Los pares (taxi, usuario) se ordenan de menor a mayor costo de ruta.
    3. Se asignan en ese orden garantizando que cada taxi y cada usuario
       participe en, como máximo, una sola asignación por llamada.

Esta estrategia no garantiza la solución globalmente óptima (eso requeriría
el algoritmo húngaro u otro de asignación bipartita), pero es eficiente,
simple de implementar y suficientemente buena para el contexto académico
del proyecto.

No incluye lógica de GUI, simulación ni control de colisiones.
"""

from __future__ import annotations

from models import Taxi, UserRequest
from city_grid import CityGrid
from pathfinding import astar


# ---------------------------------------------------------------------------
# Tipo auxiliar para describir una asignación realizada
# ---------------------------------------------------------------------------

# Una asignación es una tupla (taxi_id, user_id, costo_de_ruta).
Assignment = tuple[int, int, int]


# ---------------------------------------------------------------------------
# 1. Costo de una ruta
# ---------------------------------------------------------------------------

def route_cost(route: list) -> int:
    """
    Calcula el costo de una ruta como su número de pasos.

    Dado que cada movimiento tiene costo unitario (= 1), el costo total
    de una ruta es simplemente su longitud: ``len(route)``.

    Cuando la ruta está vacía y el origen es distinto del destino, esto
    indica que no existe camino; en ese contexto el llamador debe interpretar
    ``0`` como «ruta inexistente» y descartar el par taxi-usuario.

    Args:
        route (list[Position]): Lista de celdas retornada por ``astar()``.
                                No incluye la posición inicial; sí incluye
                                la posición objetivo.

    Returns:
        int: Número de pasos necesarios para recorrer la ruta (≥ 0).

    Ejemplo:
        >>> route_cost([Position(1,0), Position(2,0), Position(3,0)])
        3
        >>> route_cost([])   # sin ruta o ya en el destino
        0
    """
    return len(route)


# ---------------------------------------------------------------------------
# 2. Asignación greedy de taxis a usuarios
# ---------------------------------------------------------------------------

def assign_taxis_to_users(city_grid: CityGrid) -> list[Assignment]:
    """
    Asigna taxis disponibles a usuarios pendientes usando una estrategia
    greedy de costo mínimo de ruta (A*).

    Algoritmo paso a paso:
        1. Recopilar taxis cuyo estado sea ``"available"``.
        2. Recopilar usuarios que no estén completados ni asignados.
        3. Para cada par ``(taxi, usuario)`` calcular la ruta con ``astar()``.
        4. Descartar pares para los que no existe ruta (ruta vacía).
        5. Ordenar los pares válidos por costo de ruta ascendente.
        6. Iterar sobre la lista ordenada:
             - Si el taxi y el usuario aún no han sido asignados en esta
               ronda, realizar la asignación y registrarla.
        7. Retornar la lista de asignaciones efectuadas.

    Restricciones:
        - Un taxi recibe **como máximo un usuario** por llamada.
        - Un usuario es asignado a **como máximo un taxi** por llamada.
        - Los pares sin ruta válida son ignorados silenciosamente.

    Args:
        city_grid (CityGrid): Grilla de ciudad con taxis, usuarios y
                              obstáculos ya registrados.

    Returns:
        list[Assignment]: Lista de tuplas ``(taxi_id, user_id, cost)``
                          con las asignaciones realizadas en esta llamada.
                          Puede estar vacía si no hay taxis disponibles,
                          no hay usuarios pendientes o ningún par tiene
                          ruta viable.

    Ejemplo de uso:
        >>> grid = CityGrid()
        >>> grid.add_taxi(Taxi(id=1, position=Position(0, 0)))
        >>> grid.add_user(UserRequest(id=1, position=Position(5, 5)))
        >>> assign_taxis_to_users(grid)
        [(1, 1, 10)]
    """

    # ------------------------------------------------------------------
    # Paso 1: Recopilar agentes elegibles
    # ------------------------------------------------------------------

    # Taxis con estado "available" (sin asignación activa).
    available_taxis: list[Taxi] = [
        taxi for taxi in city_grid.taxis
        if taxi.is_available
    ]

    # Usuarios que aún esperan ser recogidos y no tienen taxi asignado.
    pending_users: list[UserRequest] = [
        user for user in city_grid.users
        if user.is_unassigned
    ]

    # Optimización temprana: si alguno de los dos grupos está vacío,
    # no hay nada que asignar.
    if not available_taxis or not pending_users:
        return []

    # ------------------------------------------------------------------
    # Paso 2: Calcular todas las rutas posibles (taxi × usuario)
    # ------------------------------------------------------------------

    # Cada elemento: (costo, taxi, usuario, ruta)
    # Se usará costo para ordenar; taxi y usuario para la asignación final.
    candidate_pairs: list[tuple[int, Taxi, UserRequest, list]] = []

    for taxi in available_taxis:
        for user in pending_users:

            # Calcular la ruta óptima del taxi al usuario con A*.
            route = astar(city_grid, taxi.position, user.position)

            # Si la ruta está vacía Y las posiciones son distintas, no hay
            # camino viable → descartar este par.
            if not route and taxi.position != user.position:
                continue

            # Agregar el par con su costo al conjunto de candidatos.
            cost = route_cost(route)
            candidate_pairs.append((cost, taxi, user, route))

    # Si no existe ningún par viable, terminar.
    if not candidate_pairs:
        return []

    # ------------------------------------------------------------------
    # Paso 3: Ordenar por costo de ruta (menor primero → greedy)
    # ------------------------------------------------------------------

    # sorted() es estable: pares con igual costo mantienen su orden relativo.
    candidate_pairs.sort(key=lambda item: item[0])

    # ------------------------------------------------------------------
    # Paso 4: Asignar en orden de costo, respetando unicidad
    # ------------------------------------------------------------------

    # Conjuntos de IDs ya comprometidos en esta ronda.
    assigned_taxi_ids: set[int]  = set()
    assigned_user_ids: set[int]  = set()

    # Lista de asignaciones efectuadas que se retornará al llamador.
    assignments: list[Assignment] = []

    for cost, taxi, user, route in candidate_pairs:

        # Saltar si el taxi o el usuario ya fueron asignados en esta ronda.
        if taxi.id in assigned_taxi_ids or user.id in assigned_user_ids:
            continue

        # ---- Realizar la asignación ------------------------------------

        # Actualizar el estado del taxi: le entrega la ruta y lo marca
        # como "assigned". Internamente llama a taxi.assign_user().
        taxi.assign_user(user.id, route)

        # Marcar al usuario como asignado (tiene taxi en camino).
        user.assigned = True

        # Registrar los IDs comprometidos para evitar reasignaciones.
        assigned_taxi_ids.add(taxi.id)
        assigned_user_ids.add(user.id)

        # Registrar la asignación para el informe de retorno.
        assignments.append((taxi.id, user.id, cost))

    return assignments
