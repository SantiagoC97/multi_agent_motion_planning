"""
simulation.py
=============
Módulo principal de simulación del SmartRide Planner.

Este archivo contiene el motor discreto de simulación. Su responsabilidad es:
    - Mantener el estado actual de la ciudad.
    - Ejecutar los ticks de simulación.
    - Asignar taxis a usuarios.
    - Mover taxis según sus rutas.
    - Resolver colisiones.
    - Marcar usuarios como completados.
    - Permitir escenarios fijos y escenarios aleatorios.

La generación aleatoria de escenarios NO se implementa directamente aquí.
Esa responsabilidad pertenece al módulo scenario_generator.py.
"""

from __future__ import annotations

from models import Position, Taxi, UserRequest, Obstacle
from city_grid import CityGrid
from assignment import assign_taxis_to_users
from collision_manager import resolve_movements
from scenario_generator import generate_random_scenario
from pathfinding import (
    ROUTE_ASTAR,
    find_path,
    normalize_route_algorithm,
    route_algorithm_explanation,
)
from decision_policy import (
    STRATEGY_DISTANCE,
    movement_score,
    movement_score_details,
    normalize_strategy,
    strategy_explanation,
)

YELLOW = (255, 214, 0)


class Simulation:
    """
    Motor de simulación discreta del SmartRide Planner.

    Args:
        scenario_name (str):
            Nombre del escenario que se desea ejecutar.

        randomize (bool):
            Si es True, se genera un escenario aleatorio usando
            scenario_generator.py.
            Si es False, se usan los escenarios fijos definidos
            dentro de esta clase.

        seed (int | None):
            Semilla aleatoria. Si es None, cada ejecución puede producir
            un escenario diferente. Si es un entero, el escenario será
            reproducible.

        num_taxis (int | None):
            Número de taxis. Si es None, se usa la configuración propia
            del escenario. Por seguridad, el generador limita el máximo
            a 3 taxis.
    """

    def __init__(
        self,
        scenario_name: str = "city_complete",
        randomize: bool = True,
        seed: int | None = None,
        num_taxis: int | None = None,
        num_users: int | None = None,
        assignment_strategy: str = STRATEGY_DISTANCE,
        route_algorithm: str = ROUTE_ASTAR,
    ) -> None:
        self.scenario_name: str = scenario_name
        self.randomize: bool = randomize
        self.seed: int | None = seed
        self.num_taxis: int | None = num_taxis
        self.num_users: int | None = num_users
        self.assignment_strategy: str = normalize_strategy(assignment_strategy)
        self.route_algorithm: str = normalize_route_algorithm(route_algorithm)
        self.blocked_ticks: dict[int, int] = {}

        self.city_grid: CityGrid = CityGrid()
        self.tick_count: int = 0
        self.completed_tasks: int = 0
        self.initial_total_users: int = 0

        if self.randomize:
            self._setup_random_scenario()
        else:
            self._setup_fixed_scenario()

        self.initial_total_users = len(self.city_grid.users)

    # ------------------------------------------------------------------
    # Configuración de escenarios
    # ------------------------------------------------------------------

    def _setup_random_scenario(self) -> None:
        """
        Crea un escenario aleatorio válido.

        Este método delega la generación al módulo scenario_generator.py.
        La simulación solo recibe la grilla ya construida.
        """
        self.city_grid = generate_random_scenario(
            scenario_name=self.scenario_name,
            seed=self.seed,
            num_taxis=self.num_taxis,
            num_users=self.num_users,
        )

    def _setup_fixed_scenario(self) -> None:
        """
        Carga un escenario fijo/manual.

        Estos escenarios se conservan por dos razones:
            1. Sirven para depuración.
            2. Permiten tener casos controlados para pruebas o demostraciones.
        """
        self.city_grid = CityGrid()

        scenarios = {
            "high_demand_zone": self.setup_high_demand_zone,
            "priority_users": self.setup_priority_users,
            "city_complete": self.setup_city_complete,
            "basic": self.setup_basic,
            "obstacles": self.setup_obstacles,
            "same_cell_collision": self.setup_same_cell_collision,
            "swap_collision": self.setup_swap_collision,
        }

        setup_fn = scenarios.get(self.scenario_name, self.setup_city_complete)
        setup_fn()

    # ------------------------------------------------------------------
    # Escenarios fijos
    # ------------------------------------------------------------------

    def setup_city_complete(self) -> None:
        """
        Escenario fijo:
            - 3 taxis.
            - 5 usuarios con prioridad.
            - Varios edificios.
        """

        self.city_grid.add_obstacle(Obstacle(id=1, kind="building", cells=[
            Position(2, 2), Position(2, 3),
            Position(3, 2), Position(3, 3),
        ]))

        self.city_grid.add_obstacle(Obstacle(id=2, kind="building", cells=[
            Position(8, 14), Position(8, 15),
            Position(9, 14), Position(9, 15),
        ]))

        self.city_grid.add_obstacle(Obstacle(id=3, kind="building", cells=[
            Position(5, 5), Position(5, 6), Position(5, 7),
        ]))

        self.city_grid.add_obstacle(Obstacle(id=4, kind="building", cells=[
            Position(12, 1), Position(13, 1), Position(14, 1),
        ]))

        self.city_grid.add_obstacle(Obstacle(id=5, kind="building", cells=[
            Position(16, 8), Position(16, 9),
            Position(17, 8), Position(17, 9),
        ]))

        self.city_grid.add_obstacle(Obstacle(id=6, kind="building", cells=[
            Position(0, 10), Position(0, 11),
        ]))

        self.city_grid.add_obstacle(Obstacle(id=7, kind="building", cells=[
            Position(6, 18), Position(7, 18),
        ]))

        for taxi in [
            Taxi(id=1, position=Position(0, 0), color=YELLOW),
            Taxi(id=2, position=Position(10, 10), color=YELLOW),
            Taxi(id=3, position=Position(18, 18), color=YELLOW),
        ]:
            if not self.city_grid.add_taxi(taxi):
                print(f"[WARN] No se pudo agregar {taxi}.")

        for user in [
            UserRequest(id=1, position=Position(0, 19), priority=2),
            UserRequest(id=2, position=Position(7, 4), priority=1),
            UserRequest(id=3, position=Position(13, 13), priority=3),
            UserRequest(id=4, position=Position(19, 1), priority=1),
            UserRequest(id=5, position=Position(4, 17), priority=2),
        ]:
            if not self.city_grid.add_user(user):
                print(f"[WARN] No se pudo agregar {user}.")

    setup_initial_scenario = setup_city_complete

    def setup_high_demand_zone(self) -> None:
        """
        Escenario fijo:
            - 3 taxis.
            - Usuarios concentrados en zona central.
            - Obstáculos distribuidos.
        """

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
            Position(10, 2), Position(10, 3),
            Position(11, 2), Position(11, 3),
        ]))

        self.city_grid.add_obstacle(Obstacle(id=5, kind="building", cells=[
            Position(15, 12), Position(15, 13),
        ]))

        for taxi in [
            Taxi(id=1, position=Position(0, 0), color=YELLOW),
            Taxi(id=2, position=Position(0, 19), color=YELLOW),
            Taxi(id=3, position=Position(19, 0), color=YELLOW),
        ]:
            if not self.city_grid.add_taxi(taxi):
                print(f"[WARN] No se pudo agregar {taxi}.")

        for user in [
            UserRequest(id=1, position=Position(8, 8), priority=3),
            UserRequest(id=2, position=Position(9, 9), priority=1),
            UserRequest(id=3, position=Position(8, 11), priority=2),
            UserRequest(id=4, position=Position(10, 8), priority=1),
            UserRequest(id=5, position=Position(9, 12), priority=2),
        ]:
            if not self.city_grid.add_user(user):
                print(f"[WARN] No se pudo agregar {user}.")

    def setup_priority_users(self) -> None:
        """
        Escenario fijo:
            - 3 taxis.
            - Usuarios con prioridades variadas.
            - Obstáculos fijos.
        """

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

        for taxi in [
            Taxi(id=1, position=Position(0, 0), color=YELLOW),
            Taxi(id=2, position=Position(10, 10), color=YELLOW),
            Taxi(id=3, position=Position(19, 19), color=YELLOW),
        ]:
            if not self.city_grid.add_taxi(taxi):
                print(f"[WARN] No se pudo agregar {taxi}.")

        for user in [
            UserRequest(id=1, position=Position(0, 19), priority=1),
            UserRequest(id=2, position=Position(7, 4), priority=2),
            UserRequest(id=3, position=Position(15, 15), priority=2),
            UserRequest(id=4, position=Position(19, 1), priority=3),
        ]:
            if not self.city_grid.add_user(user):
                print(f"[WARN] No se pudo agregar {user}.")

    def setup_basic(self) -> None:
        """
        Escenario fijo simple:
            - 1 taxi.
            - 1 usuario.
            - Sin obstáculos.
        """
        self.city_grid.add_taxi(
            Taxi(id=1, position=Position(0, 0), color=YELLOW)
        )

        self.city_grid.add_user(
            UserRequest(id=1, position=Position(0, 5), priority=1)
        )

    def setup_obstacles(self) -> None:
        """
        Escenario fijo con obstáculo:
            - 1 taxi.
            - 1 usuario.
            - Barrera vertical.
        """
        self.city_grid.add_obstacle(Obstacle(
            id=1,
            kind="building",
            cells=[Position(row, 3) for row in range(5)],
        ))

        self.city_grid.add_taxi(
            Taxi(id=1, position=Position(0, 0), color=YELLOW)
        )

        self.city_grid.add_user(
            UserRequest(id=1, position=Position(0, 7), priority=1)
        )

    def setup_same_cell_collision(self) -> None:
        """
        Escenario fijo de depuración:
            - 2 taxis intentan ir a la misma celda.
        """
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
        """
        Escenario fijo de depuración:
            - 2 taxis intentan intercambiar posiciones.
        """
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
    # Tick de simulación
    # ------------------------------------------------------------------
    def _replan_blocked_taxi_routes(self) -> None:
        """
        Recalcula rutas solo para taxis que llevan varios ticks bloqueados.

        Esto evita que un taxi se devuelva inmediatamente ante un bloqueo
        temporal. Primero espera. Si el bloqueo persiste, entonces replantea.

        La nueva ruta se calcula con el algoritmo seleccionado en la GUI:
            - A*
            - Dijkstra
            - BFS
            - Greedy Best-First
        """
        users_by_id: dict[int, UserRequest] = {
            user.id: user
            for user in self.city_grid.users
        }

        for taxi in self.city_grid.taxis:

            if taxi.target_user_id is None:
                continue

            if self.blocked_ticks.get(taxi.id, 0) < 2:
                continue

            target_user = users_by_id.get(taxi.target_user_id)

            if target_user is None:
                taxi.clear_assignment()
                self.blocked_ticks[taxi.id] = 0
                continue

            blocked_positions: set[Position] = {
                other_taxi.position
                for other_taxi in self.city_grid.taxis
                if other_taxi.id != taxi.id
            }

            new_route = find_path(
                city_grid=self.city_grid,
                start=taxi.position,
                goal=target_user.position,
                route_algorithm=self.route_algorithm,
                blocked_positions=blocked_positions,
            )

            if new_route:
                taxi.route = new_route
                self.blocked_ticks[taxi.id] = 0



    def _build_movement_scores(self) -> dict[int, float]:
        """
        Construye los scores de prioridad de movimiento para cada taxi.

        Estos scores se usan en collision_manager.py para decidir qué taxi
        tiene derecho de paso cuando hay conflicto.

        Menor score = mayor prioridad.
        """
        users_by_id: dict[int, UserRequest] = {
            user.id: user
            for user in self.city_grid.users
        }

        scores: dict[int, float] = {}

        for taxi in self.city_grid.taxis:
            target_user = None

            if taxi.target_user_id is not None:
                target_user = users_by_id.get(taxi.target_user_id)

            scores[taxi.id] = movement_score(
                taxi=taxi,
                target_user=target_user,
                remaining_cost=len(taxi.route),
                strategy=self.assignment_strategy,
            )

        return scores




    def step(self) -> None:
        """
        Ejecuta un tick de simulación.

        Orden lógico:
            1. Incrementar el tiempo de espera de usuarios pendientes.
            2. Asignar taxis disponibles a usuarios pendientes.
            3. Recalcular rutas solo si hay bloqueos persistentes.
            4. Calcular scores de derecho de paso.
            5. Resolver colisiones.
            6. Mover taxis.
            7. Marcar usuarios completados.
        """

        if self.is_finished():
            return

        self.tick_count += 1

        # ------------------------------------------------------------
        # 1. Incrementar espera de usuarios pendientes
        # ------------------------------------------------------------
        for user in self.city_grid.users:
            if not user.completed:
                user.increment_waiting()

        # ------------------------------------------------------------
        # 2. Asignar taxis disponibles a usuarios pendientes
        # ------------------------------------------------------------
        assign_taxis_to_users(
            self.city_grid,
            strategy=self.assignment_strategy,
            route_algorithm=self.route_algorithm,
        )

        # ------------------------------------------------------------
        # 3. Replanear solo rutas bloqueadas de forma persistente
        # ------------------------------------------------------------
        self._replan_blocked_taxi_routes()

        # ------------------------------------------------------------
        # 4. Construir scores de prioridad de movimiento
        # ------------------------------------------------------------
        movement_scores = self._build_movement_scores()

        # ------------------------------------------------------------
        # 5. Resolver movimientos permitidos
        # ------------------------------------------------------------
        allowed_moves: dict[int, Position] = resolve_movements(
            self.city_grid.taxis,
            movement_scores=movement_scores,
        )

        # ------------------------------------------------------------
        # 6. Mover taxis y registrar bloqueos
        # ------------------------------------------------------------
        for taxi in self.city_grid.taxis:
            next_position = allowed_moves.get(taxi.id, taxi.position)

            if taxi.has_route and next_position == taxi.position:
                self.blocked_ticks[taxi.id] = (
                    self.blocked_ticks.get(taxi.id, 0) + 1
                )
            else:
                self.blocked_ticks[taxi.id] = 0

            taxi.move_to(next_position)

        # ------------------------------------------------------------
        # 7. Verificar tareas completadas
        # ------------------------------------------------------------
        users_by_id: dict[int, UserRequest] = {
            user.id: user
            for user in self.city_grid.users
        }

        for taxi in self.city_grid.taxis:

            if taxi.target_user_id is None:
                continue

            target_user = users_by_id.get(taxi.target_user_id)

            if target_user is None:
                taxi.clear_assignment()
                continue

            if taxi.position == target_user.position and not target_user.completed:
                target_user.completed = True
                self.completed_tasks += 1

                # El usuario se elimina de la lista de pendientes.
                self.city_grid.remove_user(target_user.id)

                taxi.clear_assignment()
                self.blocked_ticks[taxi.id] = 0

    # ------------------------------------------------------------------
    # Estado de simulación
    # ------------------------------------------------------------------

    def is_finished(self) -> bool:
        """
        Retorna True cuando ya no quedan usuarios pendientes.
        """
        return self.get_pending_users_count() == 0

    def get_pending_users_count(self) -> int:
        """
        Retorna la cantidad de usuarios pendientes.
        """
        return len(self.city_grid.users)


    
    def get_decision_snapshot(self) -> dict:
        """
        Retorna información explicativa sobre la toma de decisiones.

        Esta información está pensada para la GUI. Permite mostrar:
            - método activo,
            - explicación del método,
            - tabla de usuarios,
            - tabla de taxis,
            - coordenadas actuales,
            - coordenadas objetivo,
            - distancia restante,
            - prioridad,
            - espera,
            - score,
            - derecho de paso actual.
        """
        users_by_id: dict[int, UserRequest] = {
            user.id: user
            for user in self.city_grid.users
        }

        assigned_taxi_by_user_id: dict[int, Taxi] = {}

        for taxi in self.city_grid.taxis:
            if taxi.target_user_id is not None:
                assigned_taxi_by_user_id[taxi.target_user_id] = taxi

        # --------------------------------------------------------------
        # Filas de usuarios
        # --------------------------------------------------------------
        user_rows: list[dict] = []

        for user in sorted(self.city_grid.users, key=lambda u: u.id):
            assigned_taxi = assigned_taxi_by_user_id.get(user.id)

            priority_label_map = {
                1: "Normal",
                2: "Importante",
                3: "Urgente",
            }

            priority_color_map = {
                1: "Azul",
                2: "Morado",
                3: "Rojo",
            }

            row = {
                "user_id": user.id,
                "position": f"({user.position.row},{user.position.col})",
                "priority": user.priority,
                "priority_label": priority_label_map.get(user.priority, "Normal"),
                "priority_color": priority_color_map.get(user.priority, "Azul"),
                "waiting_time": user.waiting_time,
                "assigned_taxi": f"T{assigned_taxi.id}" if assigned_taxi else "-",
            }

            user_rows.append(row)

        # --------------------------------------------------------------
        # Filas de taxis
        # --------------------------------------------------------------
        taxi_rows: list[dict] = []

        for taxi in sorted(self.city_grid.taxis, key=lambda t: t.id):
            target_user = None

            if taxi.target_user_id is not None:
                target_user = users_by_id.get(taxi.target_user_id)

            details = movement_score_details(
                taxi=taxi,
                target_user=target_user,
                remaining_cost=len(taxi.route),
                strategy=self.assignment_strategy,
            )

            if target_user is not None:
                target_label = f"U{target_user.id}"
                target_position = (
                    f"({target_user.position.row},{target_user.position.col})"
                )
                priority_label = details["priority_label"]
                priority_color = details["priority_color"]
            else:
                target_label = "-"
                target_position = "-"
                priority_label = "-"
                priority_color = "-"

            taxi_rows.append(
                {
                    "taxi_id": taxi.id,
                    "position": f"({taxi.position.row},{taxi.position.col})",
                    "target_user": target_label,
                    "target_position": target_position,
                    "priority_label": priority_label,
                    "priority_color": priority_color,
                    "waiting_time": details["waiting_time"],
                    "remaining_distance": details["remaining_distance"],
                    "score": round(details["score"], 2),
                    "status": taxi.status,
                }
            )

        # --------------------------------------------------------------
        # Derecho de paso
        # --------------------------------------------------------------
        active_taxis = [
            row
            for row in taxi_rows
            if row["target_user"] != "-"
        ]

        right_of_way = "-"

        if active_taxis:
            winner = sorted(
                active_taxis,
                key=lambda row: (row["score"], row["taxi_id"]),
            )[0]

            right_of_way = (
                f"T{winner['taxi_id']} → {winner['target_user']} "
                f"{winner['priority_color']}/{winner['priority_label']} "
                f"| score={winner['score']}"
            )

        return {
            "strategy": self.assignment_strategy,
            "strategy_explanation": strategy_explanation(self.assignment_strategy),
            "route_algorithm": self.route_algorithm,
            "route_algorithm_explanation": route_algorithm_explanation(self.route_algorithm),
            "user_rows": user_rows,
            "taxi_rows": taxi_rows,
            "taxi_scores": taxi_rows,
            "right_of_way": right_of_way,
        }



    def get_state(self) -> dict:
        """
        Retorna un resumen del estado actual de la simulación.

        Returns:
            dict: Información de ticks, tareas completadas, taxis y usuarios.
        """
        pending = self.get_pending_users_count()

        return {
            "tick_count": self.tick_count,
            "completed_tasks": self.completed_tasks,
            "total_tasks": self.initial_total_users,
            "total_taxis": len(self.city_grid.taxis),
            "pending_users": pending,
            "scenario_name": self.scenario_name,
            "randomize": self.randomize,
            "seed": self.seed,
            "assignment_strategy": self.assignment_strategy,
            "route_algorithm": self.route_algorithm,
        }

    # ------------------------------------------------------------------
    # Ejecución en consola
    # ------------------------------------------------------------------

    def run_console(self, max_ticks: int = 200) -> None:
        """
        Ejecuta la simulación en consola.

        Es útil para depuración sin necesidad de abrir la interfaz gráfica.
        """
        print("=" * 50)
        print("   SmartRide Planner — Simulación en consola")
        print("=" * 50)

        while not self.is_finished() and self.tick_count < max_ticks:
            self.step()
            state = self.get_state()

            print(
                f"── Tick {state['tick_count']:>3} "
                f"| Completados: {state['completed_tasks']} "
                f"| Pendientes: {state['pending_users']} ──"
            )

            self.city_grid.print_grid()

            for taxi in self.city_grid.taxis:
                print(f"  {taxi}")

            print()

        print("=" * 50)

        if self.is_finished():
            print(f"Simulación completada en {self.tick_count} ticks.")
        else:
            print(
                f"Límite de {max_ticks} ticks. "
                f"Completados: {self.completed_tasks}."
            )

        print("=" * 50)