"""
pathfinding.py
==============
Implementa el algoritmo A* (A-estrella) para encontrar la ruta óptima entre
dos celdas de la grilla urbana del SmartRide Planner.

Conceptos clave:
    - g(n) : costo acumulado real desde el inicio hasta el nodo n.
    - h(n) : estimación heurística del costo de n hasta el objetivo.
    - f(n) = g(n) + h(n) : prioridad del nodo en la cola abierta.

La heurística usada es la distancia Manhattan, que es admisible (nunca
sobreestima) para grillas con movimiento en 4 direcciones y costo unitario.

Movimiento permitido : 4 direcciones cardinales (arriba, abajo, izq., der.).
Costo por movimiento : 1 (uniforme).
Obstáculos           : excluidos por ``city_grid.get_neighbors()``.

No incluye lógica de GUI, simulación ni asignación de taxis.
"""

from __future__ import annotations

import heapq
from typing import Optional

from models import Position
from city_grid import CityGrid


# ---------------------------------------------------------------------------
# 1. Heurística: distancia Manhattan
# ---------------------------------------------------------------------------

def heuristic(a: Position, b: Position) -> int:
    """
    Calcula la heurística h(n) entre dos celdas usando distancia Manhattan.

    La distancia Manhattan entre dos puntos (r1, c1) y (r2, c2) es:
        |r1 - r2| + |c1 - c2|

    Es **admisible** para este problema porque:
        - El costo de cada paso es 1.
        - Solo se permiten movimientos cardinales.
        - Por tanto, nunca sobreestima el costo real al destino.

    Args:
        a (Position): Celda de origen.
        b (Position): Celda de destino.

    Returns:
        int: Distancia Manhattan entre ``a`` y ``b`` (siempre ≥ 0).

    Ejemplo:
        >>> heuristic(Position(0, 0), Position(3, 4))
        7
    """
    return abs(a.row - b.row) + abs(a.col - b.col)


# ---------------------------------------------------------------------------
# 2. Reconstrucción de la ruta
# ---------------------------------------------------------------------------

def reconstruct_path(
    came_from: dict[Position, Optional[Position]],
    current: Position,
) -> list[Position]:
    """
    Reconstruye la ruta completa desde el inicio hasta el nodo ``current``.

    Sigue el diccionario ``came_from`` en sentido inverso —desde el objetivo
    hasta el nodo cuyo predecesor es ``None`` (el nodo inicial)— y luego
    invierte la lista para obtener el orden correcto inicio → objetivo.

    La posición de inicio **no** se incluye en el resultado; el objetivo
    **sí** se incluye.

    Args:
        came_from (dict[Position, Position | None]):
            Mapa nodo → predecesor construido durante la búsqueda A*.
            El nodo inicial debe tener como valor ``None``.
        current (Position):
            Último nodo explorado, normalmente el objetivo alcanzado.

    Returns:
        list[Position]: Secuencia de celdas desde (pero sin incluir) el
                        inicio hasta (e incluyendo) el objetivo.

    Ejemplo:
        Si la ruta fue A → B → C → D, retorna [B, C, D].
    """
    path: list[Position] = []

    # Remontar el camino desde el objetivo hasta el inicio.
    node: Optional[Position] = current
    while node is not None:
        path.append(node)
        node = came_from[node]

    # Eliminar el nodo inicial (el último en la lista invertida).
    path.pop()

    # Invertir para obtener el orden inicio → objetivo.
    path.reverse()
    return path


# ---------------------------------------------------------------------------
# 3. Algoritmo A*
# ---------------------------------------------------------------------------

def astar(
    city_grid: CityGrid,
    start: Position,
    goal: Position,
) -> list[Position]:
    """
    Encuentra la ruta más corta entre ``start`` y ``goal`` usando A*.

    El algoritmo mantiene dos estructuras principales:
        - **Cola abierta (open_set)**: montículo mínimo (min-heap) ordenado
          por f(n) = g(n) + h(n). Cada entrada es la tupla
          ``(f, tie_breaker, position)``.
        - **Diccionario g_score**: costo real acumulado más bajo conocido
          para llegar a cada nodo explorado.

    Tie-breaking:
        Cuando dos nodos tienen el mismo f(n), el desempate se hace mediante
        un contador entero creciente (``_counter``), lo que garantiza un
        orden FIFO estable y evita comparaciones entre objetos ``Position``.

    Complejidad teórica:
        - Tiempo  : O(b^d)  donde b = factor de ramificación (≤ 4) y d = profundidad.
        - Espacio : O(b^d)  para los nodos en la cola abierta y g_score.

    Args:
        city_grid (CityGrid): Grilla de ciudad con obstáculos ya registrados.
        start     (Position): Celda inicial (posición actual del taxi).
        goal      (Position): Celda destino (posición del usuario a recoger).

    Returns:
        list[Position]: Secuencia de celdas desde (sin incluir) ``start``
                        hasta (incluyendo) ``goal``.
                        Retorna ``[]`` si no existe ninguna ruta posible.

    Casos especiales:
        - Si ``start == goal``, retorna ``[]`` (ya está en el destino).
        - Si ``start`` o ``goal`` son obstáculos o están fuera de límites,
          retorna ``[]``.

    Ejemplo:
        >>> grid = CityGrid()
        >>> ruta = astar(grid, Position(0, 0), Position(3, 3))
        >>> len(ruta)
        6   # 3 pasos horizontales + 3 verticales, sin contar el inicio
    """
    # ------------------------------------------------------------------
    # Casos de borde rápidos
    # ------------------------------------------------------------------

    # Destino inalcanzable estructuralmente.
    if not city_grid.in_bounds(start) or not city_grid.in_bounds(goal):
        return []

    if city_grid.is_obstacle(start) or city_grid.is_obstacle(goal):
        return []

    # Ya estamos en el destino.
    if start == goal:
        return []

    # ------------------------------------------------------------------
    # Inicialización
    # ------------------------------------------------------------------

    # came_from[n] = predecesor de n en la ruta óptima encontrada hasta ahora.
    # El nodo de inicio tiene None como predecesor.
    came_from: dict[Position, Optional[Position]] = {start: None}

    # g_score[n] = costo real más bajo conocido para llegar a n desde start.
    g_score: dict[Position, int] = {start: 0}

    # Contador de desempate para la cola de prioridad.
    _counter: int = 0

    # Cola abierta: (f_score, tie_breaker, nodo)
    # Se usa heapq para extraer siempre el nodo con menor f en O(log n).
    open_set: list[tuple[int, int, Position]] = []
    heapq.heappush(open_set, (heuristic(start, goal), _counter, start))

    # ------------------------------------------------------------------
    # Bucle principal de A*
    # ------------------------------------------------------------------

    while open_set:

        # Extraer el nodo con menor f(n) = g(n) + h(n).
        _f, _tie, current = heapq.heappop(open_set)

        # ---- Objetivo alcanzado ----------------------------------------
        if current == goal:
            return reconstruct_path(came_from, current)

        # ---- Explorar vecinos transitables --------------------------------
        for neighbor in city_grid.get_neighbors(current):

            # Costo para llegar al vecino desde el inicio pasando por current.
            # Cada arista tiene costo uniforme = 1.
            tentative_g = g_score[current] + 1

            # Si encontramos un camino más barato hacia neighbor, actualizamos.
            if tentative_g < g_score.get(neighbor, float("inf")):

                # Registrar al predecesor y el nuevo g más bajo.
                came_from[neighbor] = current
                g_score[neighbor]   = tentative_g

                # f(neighbor) = g(neighbor) + h(neighbor)
                f_neighbor = tentative_g + heuristic(neighbor, goal)

                # Añadir a la cola con el nuevo f.
                _counter += 1
                heapq.heappush(open_set, (f_neighbor, _counter, neighbor))

    # ------------------------------------------------------------------
    # Sin ruta: el objetivo es inalcanzable desde el inicio.
    # ------------------------------------------------------------------
    return []
