"""
collision_manager.py
====================
Módulo de detección y resolución de colisiones entre taxis para el
SmartRide Planner.

En cada tick de la simulación, varios taxis intentan avanzar un paso
en su ruta. Este módulo garantiza que sus movimientos no generen dos
tipos de conflicto:

    1. **Conflicto de celda compartida (same-cell)**:
       Dos o más taxis quieren ocupar la misma celda en el mismo instante.

    2. **Conflicto de intercambio (swap)**:
       El taxi A quiere moverse a la celda del taxi B, y simultáneamente
       el taxi B quiere moverse a la celda del taxi A.

Criterio de prioridad: el taxi con **menor ID** tiene prioridad para
avanzar; los demás esperan en su posición actual durante ese tick.

No incluye lógica de GUI, A* ni simulación completa.
"""

from __future__ import annotations

from collections import defaultdict

from models import Taxi, Position


# ---------------------------------------------------------------------------
# 1. Posición siguiente de un taxi
# ---------------------------------------------------------------------------

def get_next_position(taxi: Taxi) -> Position:
    """
    Retorna la celda a la que intentará moverse el taxi en el próximo tick.

    Si el taxi tiene al menos un paso en su ruta, devuelve el primer paso
    (``taxi.route[0]``). Si la ruta está vacía (taxi sin destino o ya
    llegó), devuelve su posición actual (el taxi permanece quieto).

    Args:
        taxi (Taxi): Taxi a consultar.

    Returns:
        Position: Celda objetivo para este tick.

    Ejemplo:
        >>> taxi = Taxi(id=1, position=Position(2, 3))
        >>> taxi.route = [Position(2, 4), Position(2, 5)]
        >>> get_next_position(taxi)
        Position(row=2, col=4)
    """
    if taxi.route:
        return taxi.route[0]   # Primer paso pendiente de la ruta.
    return taxi.position        # Sin ruta: el taxi no se mueve.


# ---------------------------------------------------------------------------
# 2. Detección de conflictos de celda compartida
# ---------------------------------------------------------------------------

def detect_same_cell_conflicts(
    taxis: list[Taxi],
) -> dict[Position, list[Taxi]]:
    """
    Detecta posiciones a las que más de un taxi quiere moverse simultáneamente.

    Para cada taxi calcula su ``next_position`` y agrupa los taxis por
    destino. Solo se incluyen en el resultado los destinos disputados por
    dos o más taxis.

    Args:
        taxis (list[Taxi]): Lista de taxis activos en la simulación.

    Returns:
        dict[Position, list[Taxi]]:
            Mapeo de celda destino → lista de taxis que quieren ir allí.
            Si no hay conflictos, el diccionario está vacío.

    Ejemplo:
        Taxi 1 en (0,0) quiere ir a (0,1).
        Taxi 2 en (1,1) quiere ir a (0,1).
        → {Position(0,1): [Taxi1, Taxi2]}
    """
    # Agrupar taxis por su próxima posición.
    destination_map: dict[Position, list[Taxi]] = defaultdict(list)

    for taxi in taxis:
        next_pos = get_next_position(taxi)
        destination_map[next_pos].append(taxi)

    # Retornar solo las celdas con más de un taxi compitiendo.
    return {
        pos: taxi_list
        for pos, taxi_list in destination_map.items()
        if len(taxi_list) > 1
    }


# ---------------------------------------------------------------------------
# 3. Detección de conflictos de intercambio (swap)
# ---------------------------------------------------------------------------

def detect_swap_conflicts(taxis: list[Taxi]) -> list[tuple[Taxi, Taxi]]:
    """
    Detecta pares de taxis que intentan intercambiar sus posiciones en el
    mismo tick.

    Un conflicto de intercambio ocurre cuando:
        - El taxi A está en la posición P₁ y quiere ir a P₂.
        - El taxi B está en la posición P₂ y quiere ir a P₁.

    Si ambos avanzaran, ocuparían la celda del otro en el mismo instante,
    lo que equivale a cruzarse en la misma arista de la grilla.

    Args:
        taxis (list[Taxi]): Lista de taxis activos en la simulación.

    Returns:
        list[tuple[Taxi, Taxi]]:
            Lista de pares ``(taxi_a, taxi_b)`` con conflicto de
            intercambio. Cada par aparece una sola vez (no duplicado).
            Si no hay conflictos, la lista está vacía.

    Ejemplo:
        Taxi A en (2,3) quiere ir a (2,4).
        Taxi B en (2,4) quiere ir a (2,3).
        → [(TaxiA, TaxiB)]
    """
    swap_conflicts: list[tuple[Taxi, Taxi]] = []

    # Construir mapa: posición_actual → taxi, para búsquedas rápidas.
    position_to_taxi: dict[Position, Taxi] = {
        taxi.position: taxi for taxi in taxis
    }

    # Conjunto de IDs ya emparejados para evitar duplicados.
    seen_pairs: set[frozenset[int]] = set()

    for taxi_a in taxis:
        next_a = get_next_position(taxi_a)

        # Si el siguiente paso de A no lleva a ninguna posición ocupada,
        # no puede haber intercambio.
        taxi_b = position_to_taxi.get(next_a)
        if taxi_b is None or taxi_b.id == taxi_a.id:
            continue

        # Verificar si B quiere ir exactamente a donde está A.
        next_b = get_next_position(taxi_b)
        if next_b == taxi_a.position:
            pair_key = frozenset({taxi_a.id, taxi_b.id})
            if pair_key not in seen_pairs:
                seen_pairs.add(pair_key)
                swap_conflicts.append((taxi_a, taxi_b))

    return swap_conflicts


# ---------------------------------------------------------------------------
# 4. Resolución de movimientos
# ---------------------------------------------------------------------------

def resolve_movements(taxis: list[Taxi]) -> dict[int, Position]:
    """
    Determina la posición final de cada taxi tras resolver todos los
    conflictos del tick actual.

    Algoritmo:
        1. Calcular la posición siguiente deseada de cada taxi.
        2. Detectar conflictos de celda compartida.
        3. Detectar conflictos de intercambio.
        4. Construir el conjunto de taxis bloqueados:
             - En un conflicto de celda compartida: avanza el de menor ID,
               los demás quedan bloqueados.
             - En un conflicto de intercambio: avanza el de menor ID,
               el otro queda bloqueado.
        5. Asignar la posición final:
             - Taxi no bloqueado → su ``next_position``.
             - Taxi bloqueado    → su posición actual (espera un tick).

    Args:
        taxis (list[Taxi]): Lista de taxis activos en la simulación.

    Returns:
        dict[int, Position]:
            Mapeo ``taxi_id → posición final`` para este tick.
            Todos los taxis de la lista reciben una entrada.

    Ejemplo:
        Taxi 1 en (0,0) quiere ir a (0,1).
        Taxi 2 en (1,1) quiere ir a (0,1).   # conflicto same-cell
        → {1: Position(0,1), 2: Position(1,1)}  # Taxi 1 avanza (id menor)
    """
    # ------------------------------------------------------------------
    # Paso 1: Posición deseada de cada taxi
    # ------------------------------------------------------------------

    desired: dict[int, Position] = {
        taxi.id: get_next_position(taxi)
        for taxi in taxis
    }

    # Conjunto de IDs que NO pueden avanzar en este tick.
    blocked_ids: set[int] = set()

    # ------------------------------------------------------------------
    # Paso 2: Resolver conflictos de celda compartida
    # ------------------------------------------------------------------

    same_cell_conflicts = detect_same_cell_conflicts(taxis)

    for _destination, competing_taxis in same_cell_conflicts.items():
        # Ordenar por ID: el menor tiene prioridad para avanzar.
        competing_taxis_sorted = sorted(competing_taxis, key=lambda t: t.id)

        # El primero (menor ID) avanza; los demás se bloquean.
        for loser in competing_taxis_sorted[1:]:
            blocked_ids.add(loser.id)

    # ------------------------------------------------------------------
    # Paso 3: Resolver conflictos de intercambio
    # ------------------------------------------------------------------

    swap_conflicts = detect_swap_conflicts(taxis)

    for taxi_a, taxi_b in swap_conflicts:
        # El taxi con mayor ID cede el paso.
        loser = taxi_a if taxi_a.id > taxi_b.id else taxi_b
        blocked_ids.add(loser.id)

    # ------------------------------------------------------------------
    # Paso 4: Construir el diccionario de posiciones finales
    # ------------------------------------------------------------------

    final_positions: dict[int, Position] = {}

    for taxi in taxis:
        if taxi.id in blocked_ids:
            # Taxi bloqueado: permanece en su posición actual este tick.
            final_positions[taxi.id] = taxi.position
        else:
            # Taxi libre: avanza a su posición deseada.
            final_positions[taxi.id] = desired[taxi.id]

    return final_positions
