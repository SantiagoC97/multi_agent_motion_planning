"""
scenario_generator.py
=====================
Generador de escenarios aleatorios para SmartRide Planner.

Este módulo se encarga de construir escenarios válidos sobre una grilla
discreta. Su responsabilidad es ubicar obstáculos, taxis y usuarios sin
superposición y con prioridades aleatorias.

La generación puede ser:
    - Aleatoria no reproducible: seed=None.
    - Aleatoria reproducible: seed=<entero>.

Esto permite que el sistema tenga variabilidad entre reinicios, pero que
también se puedan repetir escenarios específicos para pruebas, informe y
sustentación.
"""

from __future__ import annotations

import random

from city_grid import CityGrid, GRID_SIZE
from models import Position, Taxi, UserRequest, Obstacle
from pathfinding import astar


YELLOW = (255, 214, 0)


# ---------------------------------------------------------------------------
# 1. Configuración por escenario
# ---------------------------------------------------------------------------

SCENARIO_CONFIGS: dict[str, dict[str, int]] = {
    "basic": {
        "num_taxis": 1,
        "num_users": 1,
        "num_obstacles": 0,
        "max_block_size": 1,
    },
    "obstacles": {
        "num_taxis": 1,
        "num_users": 2,
        "num_obstacles": 5,
        "max_block_size": 3,
    },
    "city_complete": {
        "num_taxis": 3,
        "num_users": 5,
        "num_obstacles": 8,
        "max_block_size": 3,
    },
    "high_demand_zone": {
        "num_taxis": 3,
        "num_users": 6,
        "num_obstacles": 6,
        "max_block_size": 3,
    },
    "priority_users": {
        "num_taxis": 3,
        "num_users": 5,
        "num_obstacles": 6,
        "max_block_size": 3,
    },
}


# ---------------------------------------------------------------------------
# 2. Utilidades básicas
# ---------------------------------------------------------------------------

def all_positions() -> list[Position]:
    """
    Retorna todas las posiciones posibles de la grilla.

    Returns:
        list[Position]: Lista de posiciones desde (0,0) hasta
                        (GRID_SIZE-1, GRID_SIZE-1).
    """
    return [
        Position(row, col)
        for row in range(GRID_SIZE)
        for col in range(GRID_SIZE)
    ]


def get_occupied_positions(city_grid: CityGrid) -> set[Position]:
    """
    Obtiene todas las posiciones actualmente ocupadas por obstáculos,
    taxis o usuarios.

    Args:
        city_grid (CityGrid): Grilla actual.

    Returns:
        set[Position]: Conjunto de celdas no disponibles.
    """
    occupied: set[Position] = set()

    for obstacle in city_grid.obstacles:
        occupied.update(obstacle.cells)

    for taxi in city_grid.taxis:
        occupied.add(taxi.position)

    for user in city_grid.users:
        if not user.completed:
            occupied.add(user.position)

    return occupied


def random_free_position(
    city_grid: CityGrid,
    rng: random.Random,
) -> Position:
    """
    Selecciona una posición libre de forma aleatoria.

    Una posición libre es una celda que:
        - Está dentro de la grilla.
        - No es obstáculo.
        - No está ocupada por taxi.
        - No está ocupada por usuario.

    Args:
        city_grid (CityGrid): Grilla actual.
        rng (random.Random): Generador aleatorio.

    Returns:
        Position: Posición libre seleccionada.

    Raises:
        RuntimeError: Si no quedan posiciones libres.
    """
    candidates = [
        pos
        for pos in all_positions()
        if city_grid.is_free(pos)
    ]

    if not candidates:
        raise RuntimeError("No hay posiciones libres disponibles.")

    return rng.choice(candidates)


# ---------------------------------------------------------------------------
# 3. Generación de obstáculos
# ---------------------------------------------------------------------------

def generate_obstacle_cells(
    start: Position,
    height: int,
    width: int,
) -> list[Position]:
    """
    Genera las celdas de un obstáculo rectangular.

    Args:
        start (Position): Esquina superior izquierda del obstáculo.
        height (int): Alto del bloque.
        width (int): Ancho del bloque.

    Returns:
        list[Position]: Celdas ocupadas por el obstáculo.
    """
    cells: list[Position] = []

    for delta_row in range(height):
        for delta_col in range(width):
            cell = Position(
                row=start.row + delta_row,
                col=start.col + delta_col,
            )

            if 0 <= cell.row < GRID_SIZE and 0 <= cell.col < GRID_SIZE:
                cells.append(cell)

    return cells


def can_place_obstacle(
    city_grid: CityGrid,
    cells: list[Position],
) -> bool:
    """
    Verifica si un obstáculo puede ubicarse en las celdas dadas.

    Args:
        city_grid (CityGrid): Grilla actual.
        cells (list[Position]): Celdas candidatas.

    Returns:
        bool: True si todas las celdas son válidas y libres.
    """
    if not cells:
        return False

    for cell in cells:
        if not city_grid.in_bounds(cell):
            return False

        if not city_grid.is_free(cell):
            return False

    return True


def add_random_obstacles(
    city_grid: CityGrid,
    rng: random.Random,
    num_obstacles: int,
    max_block_size: int,
) -> None:
    """
    Agrega obstáculos aleatorios a la grilla.

    Los obstáculos se generan como bloques rectangulares pequeños para
    representar edificios.

    Args:
        city_grid (CityGrid): Grilla a modificar.
        rng (random.Random): Generador aleatorio.
        num_obstacles (int): Número de obstáculos a intentar agregar.
        max_block_size (int): Tamaño máximo de alto/ancho.
    """
    obstacle_id = 1
    attempts = 0
    max_attempts = num_obstacles * 30

    while obstacle_id <= num_obstacles and attempts < max_attempts:
        attempts += 1

        height = rng.randint(1, max_block_size)
        width = rng.randint(1, max_block_size)

        start = Position(
            row=rng.randint(0, GRID_SIZE - 1),
            col=rng.randint(0, GRID_SIZE - 1),
        )

        cells = generate_obstacle_cells(start, height, width)

        if not can_place_obstacle(city_grid, cells):
            continue

        obstacle = Obstacle(
            id=obstacle_id,
            kind="building",
            cells=cells,
        )

        city_grid.add_obstacle(obstacle)
        obstacle_id += 1


# ---------------------------------------------------------------------------
# 4. Generación de taxis y usuarios
# ---------------------------------------------------------------------------

def add_random_taxis(
    city_grid: CityGrid,
    rng: random.Random,
    num_taxis: int,
) -> None:
    """
    Agrega taxis en posiciones aleatorias libres.

    Args:
        city_grid (CityGrid): Grilla a modificar.
        rng (random.Random): Generador aleatorio.
        num_taxis (int): Número de taxis a crear.
    """
    for taxi_id in range(1, num_taxis + 1):
        position = random_free_position(city_grid, rng)

        taxi = Taxi(
            id=taxi_id,
            position=position,
            color=YELLOW,
        )

        added = city_grid.add_taxi(taxi)

        if not added:
            raise RuntimeError(
                f"No se pudo agregar el taxi {taxi_id} en {position}."
            )


def add_random_users(
    city_grid: CityGrid,
    rng: random.Random,
    num_users: int,
    high_demand_zone: bool = False,
) -> None:
    """
    Agrega usuarios en posiciones aleatorias libres.

    Args:
        city_grid (CityGrid): Grilla a modificar.
        rng (random.Random): Generador aleatorio.
        num_users (int): Número de usuarios a crear.
        high_demand_zone (bool): Si True, intenta ubicar usuarios cerca
                                 de la zona central de la grilla.
    """
    for user_id in range(1, num_users + 1):

        if high_demand_zone:
            position = random_free_position_near_center(city_grid, rng)
        else:
            position = random_free_position(city_grid, rng)

        priority = rng.randint(1, 3)

        user = UserRequest(
            id=user_id,
            position=position,
            priority=priority,
        )

        added = city_grid.add_user(user)

        if not added:
            raise RuntimeError(
                f"No se pudo agregar el usuario {user_id} en {position}."
            )


def random_free_position_near_center(
    city_grid: CityGrid,
    rng: random.Random,
) -> Position:
    """
    Selecciona una posición libre preferiblemente cerca del centro.

    Si no encuentra posición libre en la zona central, usa cualquier
    posición libre de la grilla.

    Args:
        city_grid (CityGrid): Grilla actual.
        rng (random.Random): Generador aleatorio.

    Returns:
        Position: Posición libre seleccionada.
    """
    center_min = GRID_SIZE // 2 - 4
    center_max = GRID_SIZE // 2 + 4

    candidates = [
        Position(row, col)
        for row in range(center_min, center_max + 1)
        for col in range(center_min, center_max + 1)
        if city_grid.in_bounds(Position(row, col))
        and city_grid.is_free(Position(row, col))
    ]

    if candidates:
        return rng.choice(candidates)

    return random_free_position(city_grid, rng)


# ---------------------------------------------------------------------------
# 5. Validación de conectividad básica
# ---------------------------------------------------------------------------

def has_at_least_one_route_to_each_user(city_grid: CityGrid) -> bool:
    """
    Verifica que cada usuario tenga al menos una ruta desde algún taxi.

    Esto evita generar escenarios imposibles donde un usuario quede
    completamente encerrado por obstáculos.

    Args:
        city_grid (CityGrid): Grilla generada.

    Returns:
        bool: True si cada usuario es alcanzable por al menos un taxi.
    """
    taxis = city_grid.taxis
    users = city_grid.users

    if not taxis or not users:
        return True

    for user in users:
        reachable = False

        for taxi in taxis:
            route = astar(city_grid, taxi.position, user.position)

            if route or taxi.position == user.position:
                reachable = True
                break

        if not reachable:
            return False

    return True


# ---------------------------------------------------------------------------
# 6. Generador principal
# ---------------------------------------------------------------------------

def generate_random_scenario(
    scenario_name: str = "city_complete",
    seed: int | None = None,
    num_taxis: int | None = None,
    num_users: int | None = None,
    num_obstacles: int | None = None,
) -> CityGrid:
    """
    Genera una grilla completa con obstáculos, taxis y usuarios.

    Args:
        scenario_name (str): Nombre del escenario base.
        seed (int | None): Semilla aleatoria. Si es None, cada ejecución
                           puede generar un escenario diferente.
        num_taxis (int | None): Número de taxis. Si es None, se toma de
                                la configuración del escenario.
        num_users (int | None): Número de usuarios. Si es None, se toma de
                                la configuración del escenario.
        num_obstacles (int | None): Número de obstáculos. Si es None, se toma
                                    de la configuración del escenario.

    Returns:
        CityGrid: Grilla generada.

    Raises:
        RuntimeError: Si después de varios intentos no se puede generar
                      un escenario válido.
    """
    config = SCENARIO_CONFIGS.get(
        scenario_name,
        SCENARIO_CONFIGS["city_complete"],
    )

    final_num_taxis = num_taxis if num_taxis is not None else config["num_taxis"]
    final_num_users = num_users if num_users is not None else config["num_users"]
    final_num_obstacles = (
        num_obstacles
        if num_obstacles is not None
        else config["num_obstacles"]
    )
    max_block_size = config["max_block_size"]

    # Por seguridad, el proyecto trabaja con máximo 3 taxis.
    final_num_taxis = max(1, min(final_num_taxis, 3))

    # Se usa un generador local para no afectar otros módulos.
    rng = random.Random(seed)

    max_generation_attempts = 50

    for _attempt in range(max_generation_attempts):
        city_grid = CityGrid()

        add_random_obstacles(
            city_grid=city_grid,
            rng=rng,
            num_obstacles=final_num_obstacles,
            max_block_size=max_block_size,
        )

        add_random_taxis(
            city_grid=city_grid,
            rng=rng,
            num_taxis=final_num_taxis,
        )

        high_demand = scenario_name == "high_demand_zone"

        add_random_users(
            city_grid=city_grid,
            rng=rng,
            num_users=final_num_users,
            high_demand_zone=high_demand,
        )

        if has_at_least_one_route_to_each_user(city_grid):
            return city_grid

    raise RuntimeError(
        "No fue posible generar un escenario válido después de varios intentos."
    )