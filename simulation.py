"""
simulation.py
=============
Módulo principal de simulación del SmartRide Planner.
"""

from __future__ import annotations

from models import Position, Taxi, UserRequest, Obstacle
from city_grid import CityGrid
from assignment import assign_taxis_to_users
from collision_manager import resolve_movements

YELLOW = (255, 214, 0)


class Simulation:
    """Motor de simulación discreta del SmartRide Planner."""

    def __init__(self, scenario_name: str = "city_complete") -> None:
        self.scenario_name: str = scenario_name
        self.city_grid: CityGrid = CityGrid()
        self.tick_count: int = 0
        self.completed_tasks: int = 0

        _scenarios = {
            "high_demand_zone":    self.setup_high_demand_zone,
            "priority_users":      self.setup_priority_users,
            "city_complete":       self.setup_city_complete,
            "basic":               self.setup_basic,
            "obstacles":           self.setup_obstacles,
            "same_cell_collision": self.setup_same_cell_collision,
            "swap_collision":      self.setup_swap_collision,
        }
        setup_fn = _scenarios.get(scenario_name, self.setup_city_complete)
        setup_fn()

    # ------------------------------------------------------------------
    # Escenarios
    # ------------------------------------------------------------------

    def setup_city_complete(self) -> None:
        """3 taxis amarillos, 5 usuarios con prioridad, solo edificios."""

        # Edificio A: 2x2 (filas 2-3, cols 2-3)
        self.city_grid.add_obstacle(Obstacle(id=1, kind="building", cells=[
            Position(2, 2), Position(2, 3),
            Position(3, 2), Position(3, 3),
        ]))
        # Edificio B: 2x2 (filas 8-9, cols 14-15)
        self.city_grid.add_obstacle(Obstacle(id=2, kind="building", cells=[
            Position(8, 14), Position(8, 15),
            Position(9, 14), Position(9, 15),
        ]))
        # Edificio C: 1x3 (fila 5, cols 5-7)
        self.city_grid.add_obstacle(Obstacle(id=3, kind="building", cells=[
            Position(5, 5), Position(5, 6), Position(5, 7),
        ]))
        # Edificio D: 3x1 (filas 12-14, col 1)
        self.city_grid.add_obstacle(Obstacle(id=4, kind="building", cells=[
            Position(12, 1), Position(13, 1), Position(14, 1),
        ]))
        # Edificio E: 2x2 (filas 16-17, cols 8-9)
        self.city_grid.add_obstacle(Obstacle(id=5, kind="building", cells=[
            Position(16, 8), Position(16, 9),
            Position(17, 8), Position(17, 9),
        ]))
        # Edificio F: 1x2 (fila 0, cols 10-11)
        self.city_grid.add_obstacle(Obstacle(id=6, kind="building", cells=[
            Position(0, 10), Position(0, 11),
        ]))
        # Edificio G: 2x1 (filas 6-7, col 18)
        self.city_grid.add_obstacle(Obstacle(id=7, kind="building", cells=[
            Position(6, 18), Position(7, 18),
        ]))

        # Taxis amarillos
        for taxi in [
            Taxi(id=1, position=Position(0,  0),  color=YELLOW),
            Taxi(id=2, position=Position(10, 10), color=YELLOW),
            Taxi(id=3, position=Position(18, 18), color=YELLOW),
        ]:
            if not self.city_grid.add_taxi(taxi):
                print(f"[WARN] No se pudo agregar {taxi}.")

        # Usuarios con prioridad 1=normal, 2=importante, 3=urgente
        for user in [
            UserRequest(id=1, position=Position(0,  19), priority=2),
            UserRequest(id=2, position=Position(7,   4), priority=1),
            UserRequest(id=3, position=Position(13, 13), priority=3),
            UserRequest(id=4, position=Position(19,  1), priority=1),
            UserRequest(id=5, position=Position(4,  17), priority=2),
        ]:
            if not self.city_grid.add_user(user):
                print(f"[WARN] No se pudo agregar {user}.")

    setup_initial_scenario = setup_city_complete

    def setup_high_demand_zone(self) -> None:
        """3 taxis amarillos, 5 usuarios concentrados, edificios como obstáculos."""
        # Edificios
        self.city_grid.add_obstacle(Obstacle(id=1, kind="building", cells=[
            Position(1, 5), Position(1, 6),
            Position(2, 5), Position(2, 6),
        ]))
        self.city_grid.add_obstacle(Obstacle(id=2, kind="building", cells=[
            Position(5, 10), Position(6, 10), Position(7, 10),
        ]))
        self.city_grid.add_obstacle(Obstacle(id=3, kind="building", cells=[
            Position(3, 15), Position(3, 16),
            Position(4, 15), Position(4, 16),
        ]))
        self.city_grid.add_obstacle(Obstacle(id=4, kind="building", cells=[
            Position(10, 2), Position(10, 3), Position(11, 2), Position(11, 3),
        ]))
        self.city_grid.add_obstacle(Obstacle(id=5, kind="building", cells=[
            Position(15, 12), Position(15, 13),
        ]))

        YELLOW = (255, 214, 0)
        for taxi in [
            Taxi(id=1, position=Position(0,  0), color=YELLOW),
            Taxi(id=2, position=Position(0, 19), color=YELLOW),
            Taxi(id=3, position=Position(19, 0), color=YELLOW),
        ]:
            if not self.city_grid.add_taxi(taxi):
                print(f"[WARN] No se pudo agregar {taxi}.")

        # Usuarios concentrados en zona central con prioridades variadas
        for user in [
            UserRequest(id=1, position=Position(8,  8), priority=3),
            UserRequest(id=2, position=Position(9,  9), priority=1),
            UserRequest(id=3, position=Position(8, 11), priority=2),
            UserRequest(id=4, position=Position(10, 8), priority=1),
            UserRequest(id=5, position=Position(9, 12), priority=2),
        ]:
            if not self.city_grid.add_user(user):
                print(f"[WARN] No se pudo agregar {user}.")

    def setup_priority_users(self) -> None:
        """3 taxis amarillos, 4 usuarios con prioridades variadas, edificios."""
        # Edificios
        self.city_grid.add_obstacle(Obstacle(id=1, kind="building", cells=[
            Position(4, 4), Position(4, 5),
            Position(5, 4), Position(5, 5),
        ]))
        self.city_grid.add_obstacle(Obstacle(id=2, kind="building", cells=[
            Position(2, 12), Position(3, 12), Position(4, 12),
        ]))
        self.city_grid.add_obstacle(Obstacle(id=3, kind="building", cells=[
            Position(12, 7), Position(12, 8),
            Position(13, 7), Position(13, 8),
        ]))
        self.city_grid.add_obstacle(Obstacle(id=4, kind="building", cells=[
            Position(17, 15), Position(17, 16),
        ]))

        YELLOW = (255, 214, 0)
        for taxi in [
            Taxi(id=1, position=Position(0,  0), color=YELLOW),
            Taxi(id=2, position=Position(10, 10), color=YELLOW),
            Taxi(id=3, position=Position(19, 19), color=YELLOW),
        ]:
            if not self.city_grid.add_taxi(taxi):
                print(f"[WARN] No se pudo agregar {taxi}.")

        # 1 prioridad-1, 2 prioridad-2, 1 prioridad-3
        for user in [
            UserRequest(id=1, position=Position(0,  19), priority=1),
            UserRequest(id=2, position=Position(7,   4), priority=2),
            UserRequest(id=3, position=Position(15, 15), priority=2),
            UserRequest(id=4, position=Position(19,  1), priority=3),
        ]:
            if not self.city_grid.add_user(user):
                print(f"[WARN] No se pudo agregar {user}.")

    def setup_basic(self) -> None:
        """1 taxi en (0,0), 1 usuario en (0,5), sin obstáculos."""
        self.city_grid.add_taxi(Taxi(id=1, position=Position(0, 0), color=YELLOW))
        self.city_grid.add_user(UserRequest(id=1, position=Position(0, 5), priority=1))

    def setup_obstacles(self) -> None:
        """1 taxi, 1 usuario con barrera de edificio vertical."""
        self.city_grid.add_obstacle(Obstacle(
            id=1, kind="building",
            cells=[Position(r, 3) for r in range(5)],
        ))
        self.city_grid.add_taxi(Taxi(id=1, position=Position(0, 0), color=YELLOW))
        self.city_grid.add_user(UserRequest(id=1, position=Position(0, 7), priority=1))

    def setup_same_cell_collision(self) -> None:
        """2 taxis apuntan a la misma celda destino."""
        taxi1 = Taxi(id=1, position=Position(0, 0), color=YELLOW)
        taxi1.route = [Position(0, 1)]
        taxi1.status = "assigned"
        taxi1.target_user_id = -1

        taxi2 = Taxi(id=2, position=Position(1, 1), color=YELLOW)
        taxi2.route = [Position(0, 1)]
        taxi2.status = "assigned"
        taxi2.target_user_id = -1

        self.city_grid.add_taxi(taxi1)
        self.city_grid.add_taxi(taxi2)

    def setup_swap_collision(self) -> None:
        """2 taxis intentan cruzarse (swap collision)."""
        taxi1 = Taxi(id=1, position=Position(5, 5), color=YELLOW)
        taxi1.route = [Position(5, 6)]
        taxi1.status = "assigned"
        taxi1.target_user_id = -1

        taxi2 = Taxi(id=2, position=Position(5, 6), color=YELLOW)
        taxi2.route = [Position(5, 5)]
        taxi2.status = "assigned"
        taxi2.target_user_id = -1

        self.city_grid.add_taxi(taxi1)
        self.city_grid.add_taxi(taxi2)

    # ------------------------------------------------------------------
    # Tick
    # ------------------------------------------------------------------

    def step(self) -> None:
        """Ejecuta un tick completo de la simulación."""
        for user in self.city_grid.users:
            user.increment_waiting()

        assign_taxis_to_users(self.city_grid)

        allowed_moves: dict[int, Position] = resolve_movements(self.city_grid.taxis)

        for taxi in self.city_grid.taxis:
            taxi.move_to(allowed_moves.get(taxi.id, taxi.position))

        users_by_id: dict[int, UserRequest] = {u.id: u for u in self.city_grid.users}

        for taxi in self.city_grid.taxis:
            if taxi.target_user_id is None:
                continue
            target_user = users_by_id.get(taxi.target_user_id)
            if target_user is None:
                taxi.clear_assignment()
                continue
            if taxi.position == target_user.position:
                target_user.mark_completed()
                self.city_grid.remove_user(target_user.id)
                taxi.clear_assignment()
                self.completed_tasks += 1

        self.city_grid.reset_dynamic_cells()
        self.tick_count += 1

    # ------------------------------------------------------------------
    # Estado / fin
    # ------------------------------------------------------------------

    def is_finished(self) -> bool:
        return all(user.completed for user in self.city_grid.users)

    def get_state(self) -> dict:
        pending = sum(1 for u in self.city_grid.users if not u.completed)
        return {
            "tick_count":      self.tick_count,
            "completed_tasks": self.completed_tasks,
            "total_taxis":     len(self.city_grid.taxis),
            "pending_users":   pending,
        }

    def run_console(self, max_ticks: int = 200) -> None:
        print("=" * 45)
        print("   SmartRide Planner — Simulación en consola")
        print("=" * 45)
        while not self.is_finished() and self.tick_count < max_ticks:
            self.step()
            state = self.get_state()
            print(f"── Tick {state['tick_count']:>3}  "
                  f"| Completados: {state['completed_tasks']}  "
                  f"| Pendientes: {state['pending_users']} ──")
            self.city_grid.print_grid()
            for taxi in self.city_grid.taxis:
                print(f"  {taxi}")
            print()
        print("=" * 45)
        if self.is_finished():
            print(f"Simulación completada en {self.tick_count} ticks.")
        else:
            print(f"Límite de {max_ticks} ticks. Completados: {self.completed_tasks}.")
        print("=" * 45)
