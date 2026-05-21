"""
tests.py
========
Suite de pruebas manuales para el SmartRide Planner.

Cada función de prueba es independiente:
    - Crea su propio escenario.
    - Ejecuta la lógica bajo prueba.
    - Lanza AssertionError si el resultado no es el esperado.

Uso:
    python tests.py
"""

from models import Position, Taxi, UserRequest, Obstacle
from city_grid import CityGrid
from pathfinding import (
    ROUTE_ASTAR,
    ROUTE_DIJKSTRA,
    ROUTE_BFS,
    ROUTE_GREEDY,
    astar,
    bfs,
    dijkstra,
    greedy_best_first,
)
from assignment import assign_taxis_to_users
from collision_manager import resolve_movements
from scenario_generator import generate_random_scenario
from simulation import Simulation
from decision_policy import (
    STRATEGY_DISTANCE,
    STRATEGY_PRIORITY,
    STRATEGY_WAITING,
    STRATEGY_WEIGHTED,
)


# ---------------------------------------------------------------------------
# 1. A* sin obstáculos
# ---------------------------------------------------------------------------

def test_astar_without_obstacles() -> None:
    """
    Verifica que A* encuentra la ruta directa en una grilla sin obstáculos.

    Escenario:
        - Grilla 20x20 vacía.
        - Inicio:  Position(0, 0).
        - Destino: Position(0, 5).

    Resultado esperado:
        - La ruta debe tener 5 pasos.
        - El último paso debe ser Position(0, 5).
        - La ruta no debe incluir la posición inicial.
    """
    grid = CityGrid()

    route = astar(grid, Position(0, 0), Position(0, 5))

    assert len(route) == 5, (
        f"Se esperaba una ruta de longitud 5, pero se obtuvo {len(route)}"
    )

    assert route[-1] == Position(0, 5), (
        f"El destino esperado era Position(0,5), pero se obtuvo {route[-1]}"
    )

    assert Position(0, 0) not in route, (
        "La posición inicial no debe estar incluida en la ruta"
    )


# ---------------------------------------------------------------------------
# 2. A* con obstáculos
# ---------------------------------------------------------------------------

def test_astar_with_obstacles() -> None:
    """
    Verifica que A* rodea una barrera de obstáculos.

    Escenario:
        - Grilla 20x20.
        - Barrera vertical en columna 3, filas 0 a 4.
        - Inicio:  Position(0, 0).
        - Destino: Position(0, 7).

    Resultado esperado:
        - A* debe encontrar una ruta alternativa.
        - La ruta no debe pasar por obstáculos.
        - El último paso debe ser el destino.
    """
    grid = CityGrid()

    barrier = Obstacle(
        id=1,
        kind="building",
        cells=[Position(row, 3) for row in range(5)],
    )

    grid.add_obstacle(barrier)

    route = astar(grid, Position(0, 0), Position(0, 7))

    assert len(route) > 0, (
        "A* debe encontrar una ruta alternativa alrededor del obstáculo"
    )

    for step in route:
        assert not grid.is_obstacle(step), (
            f"La ruta pasa por un obstáculo en {step}"
        )

    assert route[-1] == Position(0, 7), (
        f"El destino esperado era Position(0,7), pero se obtuvo {route[-1]}"
    )


# ---------------------------------------------------------------------------
# 3. Asignación con múltiples taxis y usuarios
# ---------------------------------------------------------------------------

def test_assignment_multiple_taxis_users() -> None:
    """
    Verifica que el sistema asigna taxis disponibles a usuarios pendientes.

    Escenario:
        - Taxi 1 en Position(0, 0).
        - Taxi 2 en Position(0, 2).
        - Usuario 1 en Position(0, 5).
        - Usuario 2 en Position(5, 0).

    Resultado esperado:
        - Deben realizarse dos asignaciones.
        - Cada taxi debe quedar en estado assigned.
        - Cada usuario debe quedar marcado como assigned.
    """
    grid = CityGrid()

    taxi1 = Taxi(id=1, position=Position(0, 0))
    taxi2 = Taxi(id=2, position=Position(0, 2))

    grid.add_taxi(taxi1)
    grid.add_taxi(taxi2)

    user1 = UserRequest(id=1, position=Position(0, 5))
    user2 = UserRequest(id=2, position=Position(5, 0))

    grid.add_user(user1)
    grid.add_user(user2)

    assignments = assign_taxis_to_users(grid)

    assert len(assignments) == 2, (
        f"Se esperaban 2 asignaciones, pero se obtuvieron {len(assignments)}"
    )

    for taxi in grid.taxis:
        assert taxi.status == "assigned", (
            f"Taxi {taxi.id} debería estar assigned, pero está {taxi.status}"
        )

    for user in grid.users:
        assert user.assigned, (
            f"Usuario {user.id} debería estar asignado"
        )


# ---------------------------------------------------------------------------
# 4. Conflicto de celda compartida
# ---------------------------------------------------------------------------

def test_same_cell_collision() -> None:
    """
    Verifica la resolución de una colisión same-cell.

    Escenario:
        - Taxi 1 en Position(0, 0) quiere ir a Position(0, 1).
        - Taxi 2 en Position(1, 1) quiere ir a Position(0, 1).

    Resultado esperado:
        - Taxi 1 avanza porque tiene menor ID.
        - Taxi 2 espera.
    """
    taxi1 = Taxi(id=1, position=Position(0, 0))
    taxi1.route = [Position(0, 1)]

    taxi2 = Taxi(id=2, position=Position(1, 1))
    taxi2.route = [Position(0, 1)]

    result = resolve_movements([taxi1, taxi2])

    assert result[1] == Position(0, 1), (
        f"Taxi 1 debe avanzar a Position(0,1), pero obtuvo {result[1]}"
    )

    assert result[2] == Position(1, 1), (
        f"Taxi 2 debe esperar en Position(1,1), pero obtuvo {result[2]}"
    )


# ---------------------------------------------------------------------------
# 5. Conflicto de intercambio
# ---------------------------------------------------------------------------

def test_swap_collision() -> None:
    """
    Verifica la resolución de una colisión tipo swap.

    Escenario:
        - Taxi 3 en Position(2, 3) quiere ir a Position(2, 4).
        - Taxi 4 en Position(2, 4) quiere ir a Position(2, 3).

    Resultado esperado:
        - Ambos taxis esperan.
        - Taxi 3 permanece en Position(2, 3).
        - Taxi 4 permanece en Position(2, 4).

    Justificación:
        Si uno de los taxis avanza y el otro espera, ambos podrían terminar
        en la misma celda. Por eso, en un conflicto de intercambio, ambos
        taxis deben bloquearse durante un tick.
    """
    taxi3 = Taxi(id=3, position=Position(2, 3))
    taxi3.route = [Position(2, 4)]

    taxi4 = Taxi(id=4, position=Position(2, 4))
    taxi4.route = [Position(2, 3)]

    result = resolve_movements([taxi3, taxi4])

    assert result[3] == Position(2, 3), (
        f"Taxi 3 debe esperar en Position(2,3), pero obtuvo {result[3]}"
    )

    assert result[4] == Position(2, 4), (
        f"Taxi 4 debe esperar en Position(2,4), pero obtuvo {result[4]}"
    )


# ---------------------------------------------------------------------------
# Ejecutor de pruebas
# ---------------------------------------------------------------------------
# ---------------------------------------------------------------------------
# 6. Escenario aleatorio reproducible con seed
# ---------------------------------------------------------------------------

def test_random_scenario_reproducible_with_seed() -> None:
    """
    Verifica que una misma semilla genera el mismo escenario.

    Esto es útil para pruebas, informe y sustentación, porque permite
    repetir exactamente un escenario aleatorio.
    """
    grid_a = generate_random_scenario(
        scenario_name="city_complete",
        seed=123,
    )

    grid_b = generate_random_scenario(
        scenario_name="city_complete",
        seed=123,
    )

    taxis_a = [(taxi.position.row, taxi.position.col) for taxi in grid_a.taxis]
    taxis_b = [(taxi.position.row, taxi.position.col) for taxi in grid_b.taxis]

    users_a = [
        (user.position.row, user.position.col, user.priority)
        for user in grid_a.users
    ]
    users_b = [
        (user.position.row, user.position.col, user.priority)
        for user in grid_b.users
    ]

    obstacles_a = [
        sorted((cell.row, cell.col) for cell in obstacle.cells)
        for obstacle in grid_a.obstacles
    ]
    obstacles_b = [
        sorted((cell.row, cell.col) for cell in obstacle.cells)
        for obstacle in grid_b.obstacles
    ]

    assert taxis_a == taxis_b, (
        "Con la misma seed, las posiciones de taxis deben coincidir"
    )

    assert users_a == users_b, (
        "Con la misma seed, las posiciones y prioridades de usuarios deben coincidir"
    )

    assert obstacles_a == obstacles_b, (
        "Con la misma seed, los obstáculos deben coincidir"
    )


# ---------------------------------------------------------------------------
# 7. Escenario aleatorio sin superposición
# ---------------------------------------------------------------------------

def test_random_scenario_has_no_overlaps() -> None:
    """
    Verifica que el escenario aleatorio no tenga entidades superpuestas.

    Ningún taxi, usuario u obstáculo debe compartir la misma celda inicial.
    """
    grid = generate_random_scenario(
        scenario_name="city_complete",
        seed=456,
    )

    occupied_positions: set[Position] = set()

    for obstacle in grid.obstacles:
        for cell in obstacle.cells:
            assert cell not in occupied_positions, (
                f"Celda duplicada en obstáculo: {cell}"
            )
            occupied_positions.add(cell)

    for taxi in grid.taxis:
        assert taxi.position not in occupied_positions, (
            f"Taxi {taxi.id} aparece sobre una celda ocupada: {taxi.position}"
        )
        occupied_positions.add(taxi.position)

    for user in grid.users:
        assert user.position not in occupied_positions, (
            f"Usuario {user.id} aparece sobre una celda ocupada: {user.position}"
        )
        occupied_positions.add(user.position)


# ---------------------------------------------------------------------------
# 8. Escenario aleatorio con usuarios alcanzables
# ---------------------------------------------------------------------------

def test_random_scenario_users_are_reachable() -> None:
    """
    Verifica que cada usuario pueda ser alcanzado por al menos un taxi.
    """
    grid = generate_random_scenario(
        scenario_name="city_complete",
        seed=789,
    )

    for user in grid.users:
        reachable = False

        for taxi in grid.taxis:
            route = astar(grid, taxi.position, user.position)

            if route or taxi.position == user.position:
                reachable = True
                break

        assert reachable, (
            f"El usuario {user.id} en {user.position} no es alcanzable"
        )


# ---------------------------------------------------------------------------
# 9. Simulation usa escenarios aleatorios por defecto
# ---------------------------------------------------------------------------

def test_simulation_random_mode_creates_entities() -> None:
    """
    Verifica que Simulation pueda crear un escenario aleatorio completo.

    Resultado esperado:
        - Debe haber al menos un taxi.
        - Debe haber al menos un usuario.
        - El modo randomize debe estar activo.
    """
    simulation = Simulation(
        scenario_name="city_complete",
        randomize=True,
        seed=321,
    )

    state = simulation.get_state()

    assert state["randomize"] is True, (
        "La simulación debe estar en modo aleatorio"
    )

    assert state["total_taxis"] > 0, (
        "La simulación aleatoria debe crear al menos un taxi"
    )

    assert state["total_tasks"] > 0, (
        "La simulación aleatoria debe crear al menos un usuario"
    )


# ---------------------------------------------------------------------------
# 10. Simulation conserva escenarios fijos
# ---------------------------------------------------------------------------

def test_simulation_fixed_mode_basic() -> None:
    """
    Verifica que Simulation todavía pueda ejecutar escenarios fijos.

    Escenario:
        - basic fijo.
        - 1 taxi.
        - 1 usuario.
        - Sin aleatoriedad.

    Resultado esperado:
        - randomize debe ser False.
        - Debe haber 1 taxi.
        - Debe haber 1 tarea inicial.
    """
    simulation = Simulation(
        scenario_name="basic",
        randomize=False,
    )

    state = simulation.get_state()

    assert state["randomize"] is False, (
        "La simulación debe estar en modo fijo"
    )

    assert state["total_taxis"] == 1, (
        f"Se esperaba 1 taxi, pero se obtuvieron {state['total_taxis']}"
    )

    assert state["total_tasks"] == 1, (
        f"Se esperaba 1 tarea, pero se obtuvieron {state['total_tasks']}"
    )




# ---------------------------------------------------------------------------
# 11. A* evita bloqueos temporales
# ---------------------------------------------------------------------------

def test_astar_avoids_temporary_blocked_positions() -> None:
    """
    Verifica que A* pueda evitar una celda bloqueada temporalmente.

    Escenario:
        - Inicio:  (0,0)
        - Meta:    (0,2)
        - Bloqueo temporal: (0,1)

    Sin bloqueo, la ruta directa sería:
        (0,0) -> (0,1) -> (0,2)

    Con bloqueo temporal, A* debe rodear por otra celda.
    """
    grid = CityGrid()

    route = astar(
        city_grid=grid,
        start=Position(0, 0),
        goal=Position(0, 2),
        blocked_positions={Position(0, 1)},
    )

    assert route, (
        "A* debe encontrar una ruta alternativa evitando el bloqueo"
    )

    assert Position(0, 1) not in route, (
        "La ruta no debe pasar por la celda temporalmente bloqueada"
    )

    assert route[-1] == Position(0, 2), (
        f"La ruta debe terminar en Position(0,2), pero terminó en {route[-1]}"
    )




# ---------------------------------------------------------------------------
# 12. Replaneación cuando un taxi bloquea la ruta
# ---------------------------------------------------------------------------

def test_simulation_replans_route_blocked_by_stationary_taxi() -> None:
    """
    Verifica que la simulación replantee una ruta cuando el bloqueo persiste.

    Este caso reproduce una situación multiagente real:

        - Taxi 1 queda detenido en una celda.
        - Taxi 2 tiene una ruta antigua que pasa por esa celda.
        - Taxi 2 no debe atravesar la celda ocupada.
        - Taxi 2 primero debe esperar.
        - Si el bloqueo persiste, debe recalcular una ruta alternativa.

    La prueba no exige que el replanteo ocurra en el primer tick, porque
    eso puede producir movimientos poco naturales. Se permite una espera
    corta antes de recalcular.
    """
    simulation = Simulation(
        scenario_name="basic",
        randomize=False,
    )

    simulation.city_grid = CityGrid()
    simulation.tick_count = 0
    simulation.completed_tasks = 0
    simulation.initial_total_users = 1

    # Taxi 1 está detenido ocupando una celda del camino directo.
    taxi1 = Taxi(
        id=1,
        position=Position(0, 1),
    )

    # Taxi 2 tiene una ruta vieja hacia el usuario, pero esa ruta pasa
    # por la celda ocupada por Taxi 1.
    taxi2 = Taxi(
        id=2,
        position=Position(1, 0),
    )
    taxi2.status = "assigned"
    taxi2.target_user_id = 1
    taxi2.route = [
        Position(0, 0),
        Position(0, 1),
        Position(0, 2),
    ]

    user = UserRequest(
        id=1,
        position=Position(0, 2),
        priority=1,
        assigned=True,
    )

    assert simulation.city_grid.add_taxi(taxi1)
    assert simulation.city_grid.add_taxi(taxi2)
    assert simulation.city_grid.add_user(user)

    # Ejecutamos varios ticks para permitir:
    #   1. avance inicial,
    #   2. detección de bloqueo,
    #   3. espera,
    #   4. replanteo si el bloqueo persiste.
    for _ in range(5):
        simulation.step()

        # En ningún momento Taxi 2 debe ocupar la celda de Taxi 1.
        assert taxi2.position != taxi1.position, (
            "Taxi 2 nunca debe ocupar la celda donde está detenido Taxi 1"
        )

    assert Position(0, 1) not in taxi2.route, (
        "Después de un bloqueo persistente, la nueva ruta de Taxi 2 "
        "no debe incluir la celda ocupada por Taxi 1"
    )



def test_assignment_strategy_distance_prefers_closest_user() -> None:
    """
    Verifica que la estrategia distance elige el usuario más cercano.
    """
    grid = CityGrid()

    taxi = Taxi(id=1, position=Position(0, 0))
    grid.add_taxi(taxi)

    close_user = UserRequest(id=1, position=Position(0, 1), priority=1)
    urgent_far_user = UserRequest(id=2, position=Position(0, 5), priority=3)

    grid.add_user(close_user)
    grid.add_user(urgent_far_user)

    assignments = assign_taxis_to_users(
        grid,
        strategy=STRATEGY_DISTANCE,
    )

    assert assignments[0][1] == 1, (
        "Con estrategia distance, el taxi debe elegir el usuario más cercano"
    )



def test_assignment_strategy_priority_prefers_urgent_user() -> None:
    """
    Verifica que la estrategia priority elige el usuario urgente,
    aunque esté más lejos.
    """
    grid = CityGrid()

    taxi = Taxi(id=1, position=Position(0, 0))
    grid.add_taxi(taxi)

    close_user = UserRequest(id=1, position=Position(0, 1), priority=1)
    urgent_far_user = UserRequest(id=2, position=Position(0, 5), priority=3)

    grid.add_user(close_user)
    grid.add_user(urgent_far_user)

    assignments = assign_taxis_to_users(
        grid,
        strategy=STRATEGY_PRIORITY,
    )

    assert assignments[0][1] == 2, (
        "Con estrategia priority, el taxi debe elegir el usuario urgente"
    )





def test_collision_resolution_uses_movement_scores() -> None:
    """
    Verifica que en una colisión same-cell no gana necesariamente el menor ID,
    sino el taxi con mejor score de movimiento.
    """
    taxi1 = Taxi(id=1, position=Position(0, 0))
    taxi1.route = [Position(0, 1)]

    taxi2 = Taxi(id=2, position=Position(1, 1))
    taxi2.route = [Position(0, 1)]

    # Taxi 2 tiene mejor score, aunque su ID sea mayor.
    movement_scores = {
        1: 50.0,
        2: 10.0,
    }

    result = resolve_movements(
        [taxi1, taxi2],
        movement_scores=movement_scores,
    )

    assert result[2] == Position(0, 1), (
        "Taxi 2 debe avanzar porque tiene mejor score de movimiento"
    )

    assert result[1] == Position(0, 0), (
        "Taxi 1 debe esperar porque tiene peor score"
    )





def test_simulation_stores_assignment_strategy() -> None:
    """
    Verifica que Simulation almacena correctamente la estrategia elegida.
    """
    simulation = Simulation(
        scenario_name="city_complete",
        randomize=True,
        seed=999,
        assignment_strategy=STRATEGY_PRIORITY,
    )

    state = simulation.get_state()

    assert state["assignment_strategy"] == STRATEGY_PRIORITY, (
        "Simulation debe guardar la estrategia de asignación seleccionada"
    )



def test_local_route_crossing_allows_only_priority_taxi_to_move() -> None:
    """
    Verifica que si dos rutas se cruzan localmente, solo avanza el taxi
    con mejor score de movimiento.

    Escenario:
        Taxi 1 y Taxi 2 no quieren la misma celda inmediata, pero sus rutas
        se cruzan dentro de los próximos pasos.

    Resultado:
        Solo el taxi con mejor score debe avanzar.
    """
    taxi1 = Taxi(id=1, position=Position(0, 0))
    taxi1.route = [
        Position(0, 1),
        Position(1, 1),
    ]

    taxi2 = Taxi(id=2, position=Position(2, 1))
    taxi2.route = [
        Position(2, 0),
        Position(1, 1),
    ]

    movement_scores = {
        1: 50.0,
        2: 10.0,
    }

    result = resolve_movements(
        [taxi1, taxi2],
        movement_scores=movement_scores,
    )

    assert result[2] == Position(2, 0), (
        "Taxi 2 debe avanzar porque tiene mayor derecho de paso"
    )

    assert result[1] == Position(0, 0), (
        "Taxi 1 debe esperar porque su ruta cruza con un taxi prioritario"
    )


def test_simulation_respects_selected_number_of_taxis() -> None:
    """
    Verifica que Simulation respete el número de taxis solicitado.
    """
    simulation = Simulation(
        scenario_name="city_complete",
        randomize=True,
        seed=2026,
        num_taxis=2,
        num_users=5,
    )

    state = simulation.get_state()

    assert state["total_taxis"] == 2, (
        f"Se esperaban 2 taxis, pero se obtuvieron {state['total_taxis']}"
    )


def test_simulation_respects_selected_number_of_users() -> None:
    """
    Verifica que Simulation respete el número de usuarios solicitado.
    """
    simulation = Simulation(
        scenario_name="city_complete",
        randomize=True,
        seed=2027,
        num_taxis=3,
        num_users=7,
    )

    state = simulation.get_state()

    assert state["total_tasks"] == 7, (
        f"Se esperaban 7 usuarios iniciales, pero se obtuvieron {state['total_tasks']}"
    )



def test_simulation_runs_without_taxi_overlap() -> None:
    """
    Ejecuta una simulación aleatoria durante varios ticks y verifica que
    nunca existan dos taxis ocupando la misma celda.

    Esta prueba valida el comportamiento multiagente de manera integrada:
        - asignación,
        - movimiento,
        - colisiones,
        - derecho de paso,
        - replaneación.
    """
    simulation = Simulation(
        scenario_name="city_complete",
        randomize=True,
        seed=404,
        num_taxis=3,
        num_users=6,
        assignment_strategy=STRATEGY_PRIORITY,
    )

    for _ in range(30):
        if simulation.is_finished():
            break

        simulation.step()

        taxi_positions = [
            taxi.position
            for taxi in simulation.city_grid.taxis
        ]

        assert len(taxi_positions) == len(set(taxi_positions)), (
            "Dos taxis terminaron ocupando la misma celda durante la simulación"
        )




def test_simulation_accepts_all_assignment_strategies() -> None:
    """
    Verifica que Simulation pueda ejecutarse con todas las estrategias
    disponibles sin generar errores.

    Estrategias:
        - distance
        - priority
        - waiting
        - weighted
    """
    strategies = [
        STRATEGY_DISTANCE,
        STRATEGY_PRIORITY,
        STRATEGY_WAITING,
        STRATEGY_WEIGHTED,
    ]

    for index, strategy in enumerate(strategies):
        simulation = Simulation(
            scenario_name="city_complete",
            randomize=True,
            seed=500 + index,
            num_taxis=3,
            num_users=5,
            assignment_strategy=strategy,
        )

        for _ in range(10):
            if simulation.is_finished():
                break

            simulation.step()

        state = simulation.get_state()

        assert state["assignment_strategy"] == strategy, (
            f"La estrategia activa debía ser {strategy}, "
            f"pero se obtuvo {state['assignment_strategy']}"
        )




def test_decision_snapshot_contains_gui_information() -> None:
    """
    Verifica que get_decision_snapshot() entregue la información necesaria
    para justificar las decisiones en la interfaz.

    La GUI necesita mostrar:
        - explicación del método,
        - usuarios,
        - derecho de paso,
        - scores.
    """
    simulation = Simulation(
        scenario_name="city_complete",
        randomize=True,
        seed=606,
        num_taxis=3,
        num_users=5,
        assignment_strategy=STRATEGY_WEIGHTED,
    )

    simulation.step()

    snapshot = simulation.get_decision_snapshot()

    assert "strategy" in snapshot, (
        "El snapshot debe incluir la estrategia activa"
    )

    assert "strategy_explanation" in snapshot, (
        "El snapshot debe incluir la explicación del método"
    )

    assert "user_rows" in snapshot, (
        "El snapshot debe incluir filas de usuarios para la GUI"
    )

    assert "taxi_scores" in snapshot, (
        "El snapshot debe incluir scores de taxis"
    )

    assert "right_of_way" in snapshot, (
        "El snapshot debe incluir el derecho de paso"
    )

    assert isinstance(snapshot["user_rows"], list), (
        "user_rows debe ser una lista"
    )

    assert isinstance(snapshot["taxi_scores"], list), (
        "taxi_scores debe ser una lista"
    )




def test_movement_priority_favors_urgent_user() -> None:
    """
    Verifica que el derecho de paso favorece al taxi asignado a un usuario
    urgente sobre uno asignado a un usuario normal.

    Aunque ambos taxis quieran la misma celda, debe avanzar el taxi que
    atiende al usuario de mayor prioridad.
    """
    grid = CityGrid()

    taxi1 = Taxi(id=1, position=Position(0, 0))
    taxi1.status = "assigned"
    taxi1.target_user_id = 1
    taxi1.route = [Position(0, 1)]

    taxi2 = Taxi(id=2, position=Position(1, 1))
    taxi2.status = "assigned"
    taxi2.target_user_id = 2
    taxi2.route = [Position(0, 1)]

    user_normal = UserRequest(
        id=1,
        position=Position(0, 5),
        priority=1,
        assigned=True,
    )

    user_urgent = UserRequest(
        id=2,
        position=Position(5, 5),
        priority=3,
        assigned=True,
    )

    assert grid.add_taxi(taxi1)
    assert grid.add_taxi(taxi2)
    assert grid.add_user(user_normal)
    assert grid.add_user(user_urgent)

    simulation = Simulation(
        scenario_name="basic",
        randomize=False,
        assignment_strategy=STRATEGY_DISTANCE,
    )

    simulation.city_grid = grid
    simulation.initial_total_users = 2

    movement_scores = simulation._build_movement_scores()

    result = resolve_movements(
        simulation.city_grid.taxis,
        movement_scores=movement_scores,
    )

    assert result[2] == Position(0, 1), (
        "Taxi 2 debe avanzar porque atiende al usuario urgente"
    )

    assert result[1] == Position(0, 0), (
        "Taxi 1 debe esperar porque atiende a un usuario normal"
    )



def test_basic_simulation_completes_task() -> None:
    """
    Verifica que el escenario fijo basic se completa correctamente.

    Esta prueba valida el flujo completo:
        - creación del escenario,
        - asignación taxi-usuario,
        - cálculo de ruta,
        - movimiento del taxi,
        - finalización de la tarea.

    Se usa un límite amplio de ticks porque la distancia depende de la
    ubicación inicial del taxi y del usuario dentro de la grilla.
    """
    simulation = Simulation(
        scenario_name="basic",
        randomize=False,
        assignment_strategy=STRATEGY_DISTANCE,
        route_algorithm=ROUTE_ASTAR,
    )

    max_ticks = 80

    for _ in range(max_ticks):
        if simulation.is_finished():
            break

        simulation.step()

    assert simulation.is_finished(), (
        f"El escenario basic debería completarse dentro de {max_ticks} ticks"
    )

    assert simulation.completed_tasks == 1, (
        f"Se esperaba 1 tarea completada, pero se obtuvo {simulation.completed_tasks}"
    )


def test_bfs_finds_valid_route() -> None:
    """
    Verifica que BFS encuentre una ruta válida.
    """
    grid = CityGrid()

    route = bfs(
        city_grid=grid,
        start=Position(0, 0),
        goal=Position(0, 5),
    )

    assert route, "BFS debe encontrar una ruta"
    assert route[-1] == Position(0, 5), "BFS debe llegar al objetivo"


def test_dijkstra_finds_valid_route() -> None:
    """
    Verifica que Dijkstra encuentre una ruta válida.
    """
    grid = CityGrid()

    route = dijkstra(
        city_grid=grid,
        start=Position(0, 0),
        goal=Position(5, 0),
    )

    assert route, "Dijkstra debe encontrar una ruta"
    assert route[-1] == Position(5, 0), "Dijkstra debe llegar al objetivo"


def test_greedy_finds_valid_route() -> None:
    """
    Verifica que Greedy Best-First encuentre una ruta válida.
    """
    grid = CityGrid()

    route = greedy_best_first(
        city_grid=grid,
        start=Position(0, 0),
        goal=Position(3, 3),
    )

    assert route, "Greedy Best-First debe encontrar una ruta"
    assert route[-1] == Position(3, 3), (
        "Greedy Best-First debe llegar al objetivo"
    )



def test_simulation_accepts_all_route_algorithms() -> None:
    """
    Verifica que Simulation pueda ejecutar todos los algoritmos de ruta.
    """
    algorithms = [
        ROUTE_ASTAR,
        ROUTE_DIJKSTRA,
        ROUTE_BFS,
        ROUTE_GREEDY,
    ]

    for index, route_algorithm in enumerate(algorithms):
        simulation = Simulation(
            scenario_name="city_complete",
            randomize=True,
            seed=900 + index,
            num_taxis=3,
            num_users=5,
            assignment_strategy=STRATEGY_DISTANCE,
            route_algorithm=route_algorithm,
        )

        for _ in range(10):
            if simulation.is_finished():
                break

            simulation.step()

        state = simulation.get_state()

        assert state["route_algorithm"] == route_algorithm, (
            f"Se esperaba algoritmo {route_algorithm}, "
            f"pero se obtuvo {state['route_algorithm']}"
        )





def run_all_tests() -> None:
    """
    Ejecuta todas las pruebas de la suite y reporta el resultado.

    Cada prueba se ejecuta dentro de un bloque try/except para identificar
    fallos lógicos o excepciones inesperadas.
    """
    tests = [
    ("A* sin obstáculos", test_astar_without_obstacles),
    ("A* con obstáculos", test_astar_with_obstacles),
    ("Asignación múltiples taxis/usuarios", test_assignment_multiple_taxis_users),
    ("Colisión same-cell", test_same_cell_collision),
    ("Colisión swap", test_swap_collision),
    ("Escenario aleatorio reproducible con seed", test_random_scenario_reproducible_with_seed),
    ("Escenario aleatorio sin superposición", test_random_scenario_has_no_overlaps),
    ("Escenario aleatorio con usuarios alcanzables", test_random_scenario_users_are_reachable),
    ("Simulation crea entidades en modo aleatorio", test_simulation_random_mode_creates_entities),
    ("Simulation conserva modo fijo basic", test_simulation_fixed_mode_basic),
    ("A* evita bloqueos temporales", test_astar_avoids_temporary_blocked_positions),
    ("Simulation replantea ruta bloqueada por taxi detenido", test_simulation_replans_route_blocked_by_stationary_taxi),
    ("Asignación distance prefiere usuario cercano", test_assignment_strategy_distance_prefers_closest_user),
    ("Asignación priority prefiere usuario urgente", test_assignment_strategy_priority_prefers_urgent_user),
    ("Colisión usa scores de movimiento", test_collision_resolution_uses_movement_scores),
    ("Simulation almacena estrategia de asignación", test_simulation_stores_assignment_strategy),
    ("Cruce local permite mover solo taxi prioritario", test_local_route_crossing_allows_only_priority_taxi_to_move),
    ("Simulation respeta número seleccionado de taxis", test_simulation_respects_selected_number_of_taxis),
    ("Simulation respeta número seleccionado de usuarios", test_simulation_respects_selected_number_of_users),
    ("Simulation corre sin superposición de taxis", test_simulation_runs_without_taxi_overlap),
    ("Simulation acepta todas las estrategias", test_simulation_accepts_all_assignment_strategies),
    ("Decision snapshot contiene información de GUI", test_decision_snapshot_contains_gui_information),
    ("Derecho de paso favorece usuario urgente", test_movement_priority_favors_urgent_user),
    ("Escenario basic completa la tarea", test_basic_simulation_completes_task),
    ("BFS encuentra ruta válida", test_bfs_finds_valid_route),
    ("Dijkstra encuentra ruta válida", test_dijkstra_finds_valid_route),
    ("Greedy Best-First encuentra ruta válida", test_greedy_finds_valid_route),
    ("Simulation acepta todos los algoritmos de ruta", test_simulation_accepts_all_route_algorithms),
    ]   

    print("=" * 60)
    print("  SmartRide Planner — Suite de pruebas")
    print("=" * 60)

    passed = 0
    failed = 0

    for name, test_function in tests:
        try:
            test_function()
            print(f"  [OK]    {name}")
            passed += 1

        except AssertionError as error:
            print(f"  [ERROR] {name}")
            print(f"          {error}")
            failed += 1

        except Exception as error:
            print(f"  [ERROR] {name}")
            print(f"          Excepción inesperada: {error}")
            failed += 1

    print("-" * 60)
    print(f"  Resultado: {passed} OK | {failed} ERROR | Total: {len(tests)}")
    print("=" * 60)


if __name__ == "__main__":
    run_all_tests()