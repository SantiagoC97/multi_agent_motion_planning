"""
collision_manager.py
====================
Módulo de detección y resolución de colisiones entre taxis.

Este módulo decide qué movimientos son permitidos en cada tick.

Tipos de conflicto:

    1. Same-cell:
       Dos o más taxis quieren ocupar la misma celda.

    2. Stationary-block:
       Un taxi intenta entrar a una celda ocupada por otro taxi quieto.

    3. Swap:
       Dos taxis intentan intercambiar posiciones.

    4. Route-crossing local:
       Dos taxis tienen rutas próximas que cruzan una misma celda dentro
       de pocos pasos. En este caso se permite avanzar al taxi con mayor
       derecho de paso y el otro espera.

Convención:
    Menor movement_score = mayor prioridad de movimiento.
"""

from __future__ import annotations

from collections import defaultdict

from models import Taxi, Position


# ---------------------------------------------------------------------------
# Utilidades
# ---------------------------------------------------------------------------

def get_next_position(taxi: Taxi) -> Position:
    """
    Retorna la posición que el taxi intenta ocupar en el próximo tick.
    """
    if taxi.route:
        return taxi.route[0]

    return taxi.position


def is_stationary(taxi: Taxi) -> bool:
    """
    Retorna True si el taxi no intenta cambiar de celda.
    """
    return get_next_position(taxi) == taxi.position


def _score_of(
    taxi: Taxi,
    movement_scores: dict[int, float] | None,
) -> float:
    """
    Retorna el score de movimiento de un taxi.
    """
    if movement_scores is None:
        return float(taxi.id)

    return movement_scores.get(taxi.id, float(taxi.id))


def _winner_by_score(
    taxis: list[Taxi],
    movement_scores: dict[int, float] | None,
) -> Taxi:
    """
    Selecciona el taxi ganador.

    Menor score = mayor prioridad.
    """
    return sorted(
        taxis,
        key=lambda taxi: (
            _score_of(taxi, movement_scores),
            taxi.id,
        ),
    )[0]


def _route_window(taxi: Taxi, steps: int = 2) -> set[Position]:
    """
    Retorna una ventana corta de la ruta futura del taxi.

    Se usa para detectar cruces locales antes de que se conviertan en
    colisiones visibles.
    """
    return set(taxi.route[:steps])


# ---------------------------------------------------------------------------
# Detección de conflictos
# ---------------------------------------------------------------------------

def detect_same_cell_conflicts(
    taxis: list[Taxi],
) -> dict[Position, list[Taxi]]:
    """
    Detecta celdas destino solicitadas por dos o más taxis.
    """
    destination_map: dict[Position, list[Taxi]] = defaultdict(list)

    for taxi in taxis:
        destination_map[get_next_position(taxi)].append(taxi)

    return {
        position: taxi_list
        for position, taxi_list in destination_map.items()
        if len(taxi_list) > 1
    }


def detect_swap_conflicts(taxis: list[Taxi]) -> list[tuple[Taxi, Taxi]]:
    """
    Detecta taxis que intentan intercambiar posiciones.
    """
    position_to_taxi: dict[Position, Taxi] = {
        taxi.position: taxi
        for taxi in taxis
    }

    swap_conflicts: list[tuple[Taxi, Taxi]] = []
    seen_pairs: set[frozenset[int]] = set()

    for taxi_a in taxis:
        next_a = get_next_position(taxi_a)
        taxi_b = position_to_taxi.get(next_a)

        if taxi_b is None:
            continue

        if taxi_b.id == taxi_a.id:
            continue

        next_b = get_next_position(taxi_b)

        if next_b == taxi_a.position:
            pair_key = frozenset({taxi_a.id, taxi_b.id})

            if pair_key not in seen_pairs:
                seen_pairs.add(pair_key)
                swap_conflicts.append((taxi_a, taxi_b))

    return swap_conflicts


def detect_local_route_crossings(
    taxis: list[Taxi],
    lookahead_steps: int = 2,
) -> list[tuple[Taxi, Taxi]]:
    """
    Detecta taxis cuyas rutas se cruzan localmente en los próximos pasos.

    Esto evita que dos taxis avancen simultáneamente hacia una intersección
    común. En ese caso, se permite avanzar primero al taxi con mayor derecho
    de paso y el otro espera.
    """
    conflicts: list[tuple[Taxi, Taxi]] = []
    seen_pairs: set[frozenset[int]] = set()

    moving_taxis = [
        taxi
        for taxi in taxis
        if taxi.route
    ]

    for i in range(len(moving_taxis)):
        for j in range(i + 1, len(moving_taxis)):
            taxi_a = moving_taxis[i]
            taxi_b = moving_taxis[j]

            window_a = _route_window(taxi_a, lookahead_steps)
            window_b = _route_window(taxi_b, lookahead_steps)

            if not window_a or not window_b:
                continue

            if window_a.intersection(window_b):
                pair_key = frozenset({taxi_a.id, taxi_b.id})

                if pair_key not in seen_pairs:
                    seen_pairs.add(pair_key)
                    conflicts.append((taxi_a, taxi_b))

    return conflicts


# ---------------------------------------------------------------------------
# Resolución principal
# ---------------------------------------------------------------------------

def resolve_movements(
    taxis: list[Taxi],
    movement_scores: dict[int, float] | None = None,
) -> dict[int, Position]:
    """
    Calcula la posición final permitida para cada taxi.

    Args:
        taxis (list[Taxi]): Taxis activos.
        movement_scores (dict[int, float] | None):
            Score de prioridad por taxi.
            Menor score = mayor prioridad.

    Returns:
        dict[int, Position]: taxi_id -> posición final permitida.
    """
    desired_positions: dict[int, Position] = {
        taxi.id: get_next_position(taxi)
        for taxi in taxis
    }

    blocked_ids: set[int] = set()

    # ------------------------------------------------------------------
    # A. Conflictos same-cell
    # ------------------------------------------------------------------

    same_cell_conflicts = detect_same_cell_conflicts(taxis)

    for destination, competing_taxis in same_cell_conflicts.items():

        stationary_occupants = [
            taxi
            for taxi in competing_taxis
            if taxi.position == destination and is_stationary(taxi)
        ]

        if stationary_occupants:
            winner = _winner_by_score(
                stationary_occupants,
                movement_scores,
            )

            for taxi in competing_taxis:
                if taxi.id != winner.id:
                    blocked_ids.add(taxi.id)

            continue

        winner = _winner_by_score(
            competing_taxis,
            movement_scores,
        )

        for taxi in competing_taxis:
            if taxi.id != winner.id:
                blocked_ids.add(taxi.id)

    # ------------------------------------------------------------------
    # B. Conflictos swap
    # ------------------------------------------------------------------
    # En un intercambio directo ambos esperan. En el siguiente tick,
    # dependiendo de prioridad y rutas alternativas, uno podrá avanzar
    # o recalcular.

    swap_conflicts = detect_swap_conflicts(taxis)

    for taxi_a, taxi_b in swap_conflicts:
        blocked_ids.add(taxi_a.id)
        blocked_ids.add(taxi_b.id)

    # ------------------------------------------------------------------
    # C. Cruces locales de ruta
    # ------------------------------------------------------------------
    # Si dos taxis se dirigen hacia una misma intersección en los próximos
    # pasos, solo se deja avanzar al de mayor derecho de paso.

    route_crossings = detect_local_route_crossings(
        taxis,
        lookahead_steps=2,
    )

    for taxi_a, taxi_b in route_crossings:

        # Si alguno ya quedó bloqueado por un conflicto más grave,
        # no hace falta resolver este par.
        if taxi_a.id in blocked_ids or taxi_b.id in blocked_ids:
            continue

        winner = _winner_by_score(
            [taxi_a, taxi_b],
            movement_scores,
        )

        loser = taxi_b if winner.id == taxi_a.id else taxi_a
        blocked_ids.add(loser.id)

    # ------------------------------------------------------------------
    # D. Construcción inicial de posiciones finales
    # ------------------------------------------------------------------

    final_positions: dict[int, Position] = {}

    for taxi in taxis:
        if taxi.id in blocked_ids:
            final_positions[taxi.id] = taxi.position
        else:
            final_positions[taxi.id] = desired_positions[taxi.id]

    # ------------------------------------------------------------------
    # E. Protección final contra duplicados
    # ------------------------------------------------------------------

    taxi_by_id: dict[int, Taxi] = {
        taxi.id: taxi
        for taxi in taxis
    }

    position_groups: dict[Position, list[Taxi]] = defaultdict(list)

    for taxi_id, final_pos in final_positions.items():
        position_groups[final_pos].append(taxi_by_id[taxi_id])

    for position, group in position_groups.items():

        if len(group) <= 1:
            continue

        original_occupants = [
            taxi
            for taxi in group
            if taxi.position == position
        ]

        if original_occupants:
            winner = _winner_by_score(
                original_occupants,
                movement_scores,
            )
        else:
            winner = _winner_by_score(
                group,
                movement_scores,
            )

        for taxi in group:
            if taxi.id != winner.id:
                final_positions[taxi.id] = taxi.position

    return final_positions