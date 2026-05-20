"""
tests.py
========
Suite de pruebas manuales para el SmartRide Planner.

Cada función de prueba es independiente: crea su propio escenario,
ejecuta la lógica bajo prueba y lanza AssertionError si el resultado
no es el esperado.

La función run_all_tests() invoca todas las pruebas y reporta el
resultado con etiquetas [OK] o [ERROR] para facilitar la depuración
y la explicación en el informe académico.

Uso:
    python tests.py
"""

from models import Position, Taxi, UserRequest, Obstacle
from city_grid import CityGrid
from pathfinding import astar
from assignment import assign_taxis_to_users
from collision_manager import resolve_movements


# ---------------------------------------------------------------------------
# 1. A* sin obstáculos
# ---------------------------------------------------------------------------

def test_astar_without_obstacles() -> None:
    """
    Verifica que A* encuentra la ruta directa en una grilla sin obstáculos.

    Escenario:
        - Grilla 20×20 vacía (solo ROAD).
        - Inicio : Position(0, 0).
        - Destino: Position(0, 5).

    Expectativa:
        - La ruta tiene exactamente 5 pasos (no incluye el inicio).
        - El destino Position(0, 5) es el último elemento.
    """
    grid = CityGrid()

    route = astar(grid, Position(0, 0), Position(0, 5))

    assert len(route) == 5, (
        f"Se esperaba longitud 5, se obtuvo {len(route)}"
    )
    assert route[-1] == Position(0, 5), (
        f"El destino debe ser Position(0,5), se obtuvo {route[-1]}"
    )
    assert Position(0, 0) not in route, (
        "El inicio no debe estar incluido en la ruta"
    )


# ---------------------------------------------------------------------------
# 2. A* con obstáculos
# ---------------------------------------------------------------------------

def test_astar_with_obstacles() -> None:
    """
    Verifica que A* rodea una barrera de obstáculos y sigue encontrando ruta.

    Escenario:
        - Grilla 20×20.
        - Barrera vertical de obstáculos en la columna 3, filas 0-4.
          (Bloquea el camino directo de (0,0) a (0,5) por esa zona.)
        - Inicio : Position(0, 0).
        - Destino: Position(0, 7).

    Expectativa:
        - A* debe encontrar una ruta no vacía rodeando la barrera.
        - Ningún paso de la ruta puede ser una celda de obstáculo.
    """
    grid = CityGrid()

    # Barrera vertical en columna 3 (filas 0 a 4).
    barrier = Obstacle(
        id=1,
        kind="building",
        cells=[Position(r, 3) for r in range(5)],
    )
    grid.add_obstacle(barrier)

    route = astar(grid, Position(0, 0), Position(0, 7))

    assert len(route) > 0, "A* debe encontrar una ruta alternativa"

    # Ningún paso debe caer en una celda de obstáculo.
    for step in route:
        assert not grid.is_obstacle(step), (
            f"La ruta pasa por un obstáculo en {step}"
        )

    assert route[-1] == Position(0, 7), (
        f"El destino debe ser Position(0,7), se obtuvo {route[-1]}"
    )


# ---------------------------------------------------------------------------
# 3. Asignación con múltiples taxis y usuarios
# ---------------------------------------------------------------------------

def test_assignment_multiple_taxis_users() -> None:
    """
    Verifica que assign_taxis_to_users genera al menos una asignación
    cuando hay taxis disponibles y usuarios pendientes.

    Escenario:
        - Taxi 1 en Position(0, 0).
        - Taxi 2 en Position(0, 2).
        - Usuario 1 en Position(0, 5).
        - Usuario 2 en Position(5, 0).

    Expectativa:
        - Se realizan exactamente 2 asignaciones (un taxi por usuario).
        - Cada taxi queda en estado "assigned".
        - Cada usuario queda marcado como asignado.
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
        f"Se esperaban 2 asignaciones, se obtuvieron {len(assignments)}"
    )

    # Verificar que los taxis ya no están disponibles.
    for taxi in grid.taxis:
        assert taxi.status == "assigned", (
            f"Taxi {taxi.id} debería estar 'assigned', está '{taxi.status}'"
        )

    # Verificar que los usuarios quedaron marcados.
    for user in grid.users:
        assert user.assigned, (
            f"Usuario {user.id} debería estar asignado"
        )


# ---------------------------------------------------------------------------
# 4. Conflicto de celda compartida (same-cell)
# ---------------------------------------------------------------------------

def test_same_cell_collision() -> None:
    """
    Verifica que resolve_movements resuelve un conflicto same-cell:
    solo el taxi con menor ID avanza; el otro permanece en su posición.

    Escenario:
        - Taxi 1 en Position(0, 0) → quiere ir a Position(0, 1).
        - Taxi 2 en Position(1, 1) → quiere ir a Position(0, 1).
        Ambos apuntan al mismo destino.

    Expectativa:
        - Taxi 1 (id menor) avanza a Position(0, 1).
        - Taxi 2 queda en Position(1, 1).
    """
    taxi1 = Taxi(id=1, position=Position(0, 0))
    taxi1.route = [Position(0, 1)]

    taxi2 = Taxi(id=2, position=Position(1, 1))
    taxi2.route = [Position(0, 1)]

    result = resolve_movements([taxi1, taxi2])

    assert result[1] == Position(0, 1), (
        f"Taxi 1 debe avanzar a (0,1), obtuvo {result[1]}"
    )
    assert result[2] == Position(1, 1), (
        f"Taxi 2 debe esperar en (1,1), obtuvo {result[2]}"
    )


# ---------------------------------------------------------------------------
# 5. Conflicto de intercambio (swap)
# ---------------------------------------------------------------------------

def test_swap_collision() -> None:
    """
    Verifica que resolve_movements resuelve un conflicto de intercambio:
    los dos taxis quieren cruzarse; solo el de menor ID avanza.

    Escenario:
        - Taxi 3 en Position(2, 3) → quiere ir a Position(2, 4).
        - Taxi 4 en Position(2, 4) → quiere ir a Position(2, 3).
        Forman un intercambio directo.

    Expectativa:
        - Taxi 3 (id menor) avanza a Position(2, 4).
        - Taxi 4 permanece en Position(2, 4)  ← espera en su celda actual.
    """
    taxi3 = Taxi(id=3, position=Position(2, 3))
    taxi3.route = [Position(2, 4)]

    taxi4 = Taxi(id=4, position=Position(2, 4))
    taxi4.route = [Position(2, 3)]

    result = resolve_movements([taxi3, taxi4])

    assert result[3] == Position(2, 4), (
        f"Taxi 3 debe avanzar a (2,4), obtuvo {result[3]}"
    )
    assert result[4] == Position(2, 4), (
        f"Taxi 4 debe esperar en (2,4), obtuvo {result[4]}"
    )


# ---------------------------------------------------------------------------
# Ejecutor de pruebas
# ---------------------------------------------------------------------------

def run_all_tests() -> None:
    """
    Ejecuta todas las pruebas de la suite y reporta el resultado.

    Cada prueba se ejecuta dentro de un bloque try/except para capturar
    tanto AssertionError (fallo lógico) como cualquier excepción inesperada.
    """
    tests = [
        ("A* sin obstáculos",                    test_astar_without_obstacles),
        ("A* con obstáculos (ruta alternativa)",  test_astar_with_obstacles),
        ("Asignación múltiples taxis/usuarios",   test_assignment_multiple_taxis_users),
        ("Colisión same-cell",                    test_same_cell_collision),
        ("Colisión swap",                         test_swap_collision),
    ]

    print("=" * 52)
    print("  SmartRide Planner — Suite de pruebas")
    print("=" * 52)

    passed = 0
    failed = 0

    for name, test_fn in tests:
        try:
            test_fn()
            print(f"  [OK]    {name}")
            passed += 1
        except AssertionError as err:
            print(f"  [ERROR] {name}")
            print(f"          → {err}")
            failed += 1
        except Exception as exc:
            print(f"  [ERROR] {name}")
            print(f"          → Excepción inesperada: {exc}")
            failed += 1

    print("-" * 52)
    print(f"  Resultado: {passed} OK  |  {failed} ERROR  "
          f"(total: {len(tests)})")
    print("=" * 52)


if __name__ == "__main__":
    run_all_tests()
