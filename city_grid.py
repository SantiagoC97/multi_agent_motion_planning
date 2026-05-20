"""
city_grid.py
============
Representa la ciudad del SmartRide Planner como una grilla discreta de 20×20.

Responsabilidades de este módulo:
    - Mantener el estado lógico de cada celda (ROAD, OBSTACLE, TAXI, USER).
    - Gestionar las listas de taxis, usuarios y obstáculos.
    - Proveer consultas espaciales: vecinos, libre, ocupado, etc.
    - Servir como fuente de verdad para el pathfinding y la simulación.

NO incluye lógica de A*, simulación ni GUI.
"""

from __future__ import annotations

from typing import Optional

from models import Position, Taxi, UserRequest, Obstacle, CellType


# ---------------------------------------------------------------------------
# Constantes
# ---------------------------------------------------------------------------

GRID_SIZE: int = 20   # Número de filas y columnas de la grilla cuadrada.

# Desplazamientos (Δfila, Δcol) para los 4 vecinos cardinales.
_CARDINAL_DELTAS: list[tuple[int, int]] = [
    (-1,  0),   # Arriba
    ( 1,  0),   # Abajo
    ( 0, -1),   # Izquierda
    ( 0,  1),   # Derecha
]


# ---------------------------------------------------------------------------
# CityGrid
# ---------------------------------------------------------------------------

class CityGrid:
    """
    Grilla de ciudad de GRID_SIZE × GRID_SIZE para el SmartRide Planner.

    Cada celda es inicialmente de tipo ROAD. Los métodos de esta clase permiten
    consultar y modificar el estado lógico de la grilla, además de gestionar
    las colecciones de taxis, usuarios y obstáculos.

    Atributos (internos):
        _grid      (list[list[CellType]]): Matriz 2-D del estado de cada celda.
        _taxis     (dict[int, Taxi])      : Taxis indexados por su ID.
        _users     (dict[int, UserRequest]): Usuarios indexados por su ID.
        _obstacles (dict[int, Obstacle])  : Obstáculos indexados por su ID.
        _obstacle_cells (set[Position])   : Conjunto rápido de celdas bloqueadas.
    """

    # ------------------------------------------------------------------
    # Constructor
    # ------------------------------------------------------------------

    def __init__(self) -> None:
        """
        Inicializa la grilla con todas las celdas en estado ROAD y las
        colecciones de agentes vacías.
        """
        # Grilla 20×20: lista de filas, cada fila es una lista de CellType.
        self._grid: list[list[CellType]] = [
            [CellType.ROAD for _ in range(GRID_SIZE)]
            for _ in range(GRID_SIZE)
        ]

        # Diccionarios de entidades activas, indexados por ID.
        self._taxis:     dict[int, Taxi]         = {}
        self._users:     dict[int, UserRequest]  = {}
        self._obstacles: dict[int, Obstacle]     = {}

        # Conjunto auxiliar para consultar obstáculos en O(1).
        self._obstacle_cells: set[Position] = set()

    # ------------------------------------------------------------------
    # Propiedades de acceso de solo lectura
    # ------------------------------------------------------------------

    @property
    def size(self) -> int:
        """Dimensión (filas = columnas) de la grilla cuadrada."""
        return GRID_SIZE

    @property
    def taxis(self) -> list[Taxi]:
        """Lista de todos los taxis registrados en la grilla."""
        return list(self._taxis.values())

    @property
    def users(self) -> list[UserRequest]:
        """Lista de todos los usuarios registrados en la grilla."""
        return list(self._users.values())

    @property
    def obstacles(self) -> list[Obstacle]:
        """Lista de todos los obstáculos registrados en la grilla."""
        return list(self._obstacles.values())

    # ------------------------------------------------------------------
    # 1. Consultas espaciales básicas
    # ------------------------------------------------------------------

    def in_bounds(self, position: Position) -> bool:
        """
        Verifica si una posición se encuentra dentro de los límites de la grilla.

        Args:
            position (Position): Celda a verificar.

        Returns:
            bool: True si 0 ≤ row < GRID_SIZE y 0 ≤ col < GRID_SIZE.

        Ejemplo:
            >>> grid.in_bounds(Position(0, 0))
            True
            >>> grid.in_bounds(Position(20, 5))
            False
        """
        return (
            0 <= position.row < GRID_SIZE
            and 0 <= position.col < GRID_SIZE
        )

    def is_obstacle(self, position: Position) -> bool:
        """
        Verifica si una celda está marcada como obstáculo.

        Usa el conjunto auxiliar ``_obstacle_cells`` para una consulta O(1).

        Args:
            position (Position): Celda a verificar.

        Returns:
            bool: True si la celda es OBSTACLE.
        """
        return position in self._obstacle_cells

    def is_road(self, position: Position) -> bool:
        """
        Verifica si una celda tiene tipo ROAD en la grilla.

        Una celda ROAD puede estar libre, ocupada por un taxi o por un usuario;
        simplemente no es un obstáculo declarado estructuralmente.

        Args:
            position (Position): Celda a verificar.

        Returns:
            bool: True si el tipo de celda en la matriz es ROAD.

        Nota:
            Para saber si una celda ROAD está realmente libre de agentes,
            usa ``is_free()``.
        """
        if not self.in_bounds(position):
            return False
        return self._grid[position.row][position.col] == CellType.ROAD

    def is_occupied_by_taxi(self, position: Position) -> bool:
        """
        Verifica si algún taxi ocupa actualmente la celda indicada.

        Itera sobre los taxis registrados y compara sus posiciones.

        Args:
            position (Position): Celda a verificar.

        Returns:
            bool: True si al menos un taxi está en esa posición.
        """
        return any(taxi.position == position for taxi in self._taxis.values())

    def is_occupied_by_user(self, position: Position) -> bool:
        """
        Verifica si algún usuario (no completado) ocupa la celda indicada.

        Solo se consideran usuarios que aún no han sido recogidos.

        Args:
            position (Position): Celda a verificar.

        Returns:
            bool: True si al menos un usuario pendiente está en esa posición.
        """
        return any(
            user.position == position
            for user in self._users.values()
            if not user.completed
        )

    def is_free(self, position: Position) -> bool:
        """
        Determina si una celda está completamente libre para ser ocupada.

        Una celda es libre cuando cumple todas estas condiciones:
            1. Está dentro de los límites de la grilla.
            2. No es un obstáculo.
            3. No está ocupada por ningún taxi.
            4. No está ocupada por ningún usuario pendiente.

        Args:
            position (Position): Celda a evaluar.

        Returns:
            bool: True si la celda puede ser ocupada por un nuevo agente.
        """
        return (
            self.in_bounds(position)
            and not self.is_obstacle(position)
            and not self.is_occupied_by_taxi(position)
            and not self.is_occupied_by_user(position)
        )

    # ------------------------------------------------------------------
    # 2. Métodos de adición de entidades
    # ------------------------------------------------------------------

    def add_taxi(self, taxi: Taxi) -> bool:
        """
        Registra un taxi en la grilla si su celda inicial está libre.

        Actualiza la matriz de celdas marcando la posición como TAXI.
        Si el ID ya existe, el taxi existente es reemplazado (la celda
        anterior se restaura a ROAD antes de registrar la nueva posición).

        Args:
            taxi (Taxi): Taxi a agregar.

        Returns:
            bool: True si el taxi fue añadido correctamente;
                  False si la celda destino no está libre.

        Raises:
            ValueError: Si la posición del taxi está fuera de los límites.
        """
        if not self.in_bounds(taxi.position):
            raise ValueError(
                f"Posición {taxi.position} fuera de los límites de la grilla."
            )

        # Si el taxi ya estaba registrado, liberar su celda anterior.
        if taxi.id in self._taxis:
            old_pos = self._taxis[taxi.id].position
            self._grid[old_pos.row][old_pos.col] = CellType.ROAD

        # Verificar disponibilidad de la nueva celda.
        if not self.is_free(taxi.position):
            return False

        # Registrar taxi y marcar la celda en la grilla.
        self._taxis[taxi.id] = taxi
        self._grid[taxi.position.row][taxi.position.col] = CellType.TAXI
        return True

    def add_user(self, user: UserRequest) -> bool:
        """
        Registra un usuario en la grilla si su celda inicial está libre.

        Actualiza la matriz de celdas marcando la posición como USER.
        Si el ID ya existe, el usuario existente es reemplazado.

        Args:
            user (UserRequest): Usuario a agregar.

        Returns:
            bool: True si el usuario fue añadido correctamente;
                  False si la celda destino no está libre.

        Raises:
            ValueError: Si la posición del usuario está fuera de los límites.
        """
        if not self.in_bounds(user.position):
            raise ValueError(
                f"Posición {user.position} fuera de los límites de la grilla."
            )

        # Si el usuario ya estaba registrado, liberar su celda anterior.
        if user.id in self._users:
            old_pos = self._users[user.id].position
            self._grid[old_pos.row][old_pos.col] = CellType.ROAD

        # Verificar disponibilidad de la nueva celda.
        if not self.is_free(user.position):
            return False

        # Registrar usuario y marcar la celda en la grilla.
        self._users[user.id] = user
        self._grid[user.position.row][user.position.col] = CellType.USER
        return True

    def add_obstacle(self, obstacle: Obstacle) -> None:
        """
        Registra un obstáculo y bloquea todas sus celdas en la grilla.

        Los obstáculos pueden ocupar varias celdas. Cada celda válida del
        obstáculo se marca como OBSTACLE en la matriz y se añade al conjunto
        auxiliar ``_obstacle_cells``. Las celdas fuera de los límites son
        ignoradas con una advertencia.

        Args:
            obstacle (Obstacle): Obstáculo a registrar (puede tener varias celdas).
        """
        self._obstacles[obstacle.id] = obstacle

        for cell in obstacle.cells:
            if not self.in_bounds(cell):
                # Celda inválida: se omite silenciosamente (o se puede loguear).
                continue
            self._grid[cell.row][cell.col] = CellType.OBSTACLE
            self._obstacle_cells.add(cell)

    # ------------------------------------------------------------------
    # 3. Métodos de eliminación de entidades
    # ------------------------------------------------------------------

    def remove_user(self, user_id: int) -> Optional[UserRequest]:
        """
        Elimina un usuario de la grilla por su ID.

        Restaura la celda que ocupaba a ROAD si ningún otro agente la ocupa.

        Args:
            user_id (int): ID del usuario a eliminar.

        Returns:
            UserRequest: El usuario eliminado, o None si no se encontró.
        """
        user = self._users.pop(user_id, None)
        if user is None:
            return None

        # Restaurar la celda a ROAD solo si no hay un taxi encima.
        pos = user.position
        if self.in_bounds(pos) and not self.is_occupied_by_taxi(pos):
            self._grid[pos.row][pos.col] = CellType.ROAD

        return user

    # ------------------------------------------------------------------
    # 4. Navegación: vecinos transitables
    # ------------------------------------------------------------------

    def get_neighbors(self, position: Position) -> list[Position]:
        """
        Devuelve las celdas adyacentes transitables de una posición dada.

        Se consideran los 4 vecinos cardinales (arriba, abajo, izquierda,
        derecha). Una celda vecina es válida (transitable) cuando:
            1. Está dentro de los límites de la grilla.
            2. No es un obstáculo.

        Los taxis y usuarios NO bloquean el movimiento; la gestión de
        colisiones es responsabilidad del CollisionManager.

        Args:
            position (Position): Celda desde la que calcular vecinos.

        Returns:
            list[Position]: Lista ordenada (arriba, abajo, izq., der.)
                            de celdas transitables. Puede estar vacía si
                            la posición está completamente rodeada.

        Ejemplo:
            >>> grid.get_neighbors(Position(0, 0))
            [Position(row=1, col=0), Position(row=0, col=1)]
        """
        neighbors: list[Position] = []

        for delta_row, delta_col in _CARDINAL_DELTAS:
            candidate = Position(
                row=position.row + delta_row,
                col=position.col + delta_col,
            )
            # Solo se incluye si está en bounds y no es obstáculo.
            if self.in_bounds(candidate) and not self.is_obstacle(candidate):
                neighbors.append(candidate)

        return neighbors

    # ------------------------------------------------------------------
    # 5. Restablecimiento de celdas dinámicas
    # ------------------------------------------------------------------

    def reset_dynamic_cells(self) -> None:
        """
        Restaura todas las celdas dinámicas (TAXI y USER) a estado ROAD.

        Este método sincroniza la grilla con las posiciones actuales de los
        agentes registrados. El flujo es:
            1. Recorrer toda la grilla y convertir TAXI/USER → ROAD.
            2. Volver a marcar las celdas de los taxis activos como TAXI.
            3. Volver a marcar las celdas de los usuarios pendientes como USER.

        Úsalo al comienzo de cada tick de simulación para garantizar que
        la grilla refleje el estado real de los agentes tras sus movimientos.

        Nota:
            Las celdas OBSTACLE nunca son modificadas por este método.
        """
        # Paso 1: limpiar todas las celdas dinámicas.
        for row in range(GRID_SIZE):
            for col in range(GRID_SIZE):
                cell_type = self._grid[row][col]
                if cell_type in (CellType.TAXI, CellType.USER):
                    self._grid[row][col] = CellType.ROAD

        # Paso 2: re-marcar posiciones actuales de los taxis.
        for taxi in self._taxis.values():
            pos = taxi.position
            if self.in_bounds(pos) and not self.is_obstacle(pos):
                self._grid[pos.row][pos.col] = CellType.TAXI

        # Paso 3: re-marcar posiciones de los usuarios no completados.
        for user in self._users.values():
            if user.completed:
                continue
            pos = user.position
            if self.in_bounds(pos) and not self.is_obstacle(pos):
                # Un taxi tiene prioridad visual sobre un usuario en la misma celda.
                if self._grid[pos.row][pos.col] != CellType.TAXI:
                    self._grid[pos.row][pos.col] = CellType.USER

    # ------------------------------------------------------------------
    # 6. Acceso directo a la grilla (utilidad para GUI / depuración)
    # ------------------------------------------------------------------

    def get_cell_type(self, position: Position) -> CellType:
        """
        Retorna el tipo de celda de una posición dada.

        Args:
            position (Position): Celda a consultar.

        Returns:
            CellType: Estado actual de la celda.

        Raises:
            IndexError: Si la posición está fuera de los límites.
        """
        if not self.in_bounds(position):
            raise IndexError(
                f"Posición {position} fuera de los límites de la grilla "
                f"({GRID_SIZE}×{GRID_SIZE})."
            )
        return self._grid[position.row][position.col]

    # ------------------------------------------------------------------
    # 7. Representación textual (depuración)
    # ------------------------------------------------------------------

    def __repr__(self) -> str:
        """Representación compacta para depuración."""
        return (
            f"CityGrid("
            f"size={GRID_SIZE}×{GRID_SIZE}, "
            f"taxis={len(self._taxis)}, "
            f"users={len(self._users)}, "
            f"obstacles={len(self._obstacles)})"
        )

    def print_grid(self) -> None:
        """
        Imprime la grilla en la consola usando caracteres ASCII.

        Leyenda:
            .  → ROAD libre
            X  → OBSTACLE
            T  → TAXI
            U  → USER
        """
        symbols: dict[CellType, str] = {
            CellType.ROAD:     ".",
            CellType.OBSTACLE: "X",
            CellType.TAXI:     "T",
            CellType.USER:     "U",
            CellType.EMPTY:    " ",
        }
        separator = "+" + "-" * (GRID_SIZE * 2 - 1) + "+"
        print(separator)
        for row in self._grid:
            line = " ".join(symbols.get(cell, "?") for cell in row)
            print(f"|{line}|")
        print(separator)
