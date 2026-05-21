"""
models.py
=========
Define las entidades principales del sistema SmartRide Planner:
    - CellType   : tipos de celda en la grilla.
    - Position   : coordenada (fila, columna) en la grilla.
    - Taxi       : agente autónomo que recorre la ciudad.
    - UserRequest: pasajero que espera ser recogido.
    - Obstacle   : celda o grupo de celdas bloqueadas.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Optional


# ---------------------------------------------------------------------------
# CellType
# ---------------------------------------------------------------------------

class CellType(Enum):
    """
    Tipos posibles para cada celda de la grilla de ciudad.

    Valores:
        EMPTY       : celda vacía sin rol activo (relleno / fuera de red).
        ROAD        : calle libre, transitable por los taxis.
        OBSTACLE    : celda bloqueada (edificio, parque, construcción, etc.).
        TAXI        : celda ocupada por un taxi autónomo.
        USER        : celda donde un usuario espera ser recogido.
    """
    EMPTY       = auto()
    ROAD        = auto()
    OBSTACLE    = auto()
    TAXI        = auto()
    USER        = auto()


# ---------------------------------------------------------------------------
# Position
# ---------------------------------------------------------------------------

@dataclass
class Position:
    """
    Coordenada discreta dentro de la grilla de ciudad.

    Atributos:
        row (int): Índice de fila   (0 = fila superior).
        col (int): Índice de columna (0 = columna izquierda).
    """
    row: int
    col: int

    # ------------------------------------------------------------------
    # Métodos de utilidad
    # ------------------------------------------------------------------

    def distance_to(self, other: Position) -> int:
        """
        Calcula la distancia Manhattan entre esta posición y otra.

        La distancia Manhattan es la suma de las diferencias absolutas
        de filas y columnas, equivalente al número mínimo de pasos en
        movimiento de 4 direcciones sin obstáculos.

        Args:
            other (Position): Posición de destino.

        Returns:
            int: Distancia Manhattan (siempre >= 0).

        Ejemplo:
            >>> Position(0, 0).distance_to(Position(3, 4))
            7
        """
        return abs(self.row - other.row) + abs(self.col - other.col)

    def __eq__(self, other: object) -> bool:
        """Dos posiciones son iguales si comparten fila y columna."""
        if not isinstance(other, Position):
            return NotImplemented
        return self.row == other.row and self.col == other.col

    def __hash__(self) -> int:
        """Permite usar Position como clave en diccionarios y conjuntos."""
        return hash((self.row, self.col))

    def __repr__(self) -> str:
        return f"Position(row={self.row}, col={self.col})"


# ---------------------------------------------------------------------------
# Taxi
# ---------------------------------------------------------------------------

# Valores válidos para el estado de un taxi.
TaxiStatus = str   # Literal["available", "assigned", "waiting", "completed"]

@dataclass
class Taxi:
    """
    Agente autónomo que se mueve por la grilla para recoger usuarios.

    Atributos:
        id             (int)            : Identificador único del taxi.
        position       (Position)       : Celda actual del taxi en la grilla.
        target_user_id (int | None)     : ID del usuario asignado, o None si libre.
        route          (list[Position]) : Secuencia de celdas que debe recorrer.
        status         (TaxiStatus)     : Estado actual del taxi.
            - "available" : sin asignación, listo para recibir una tarea.
            - "assigned"  : tiene un usuario asignado y se dirige a él.
            - "waiting"   : llegó al destino, espera confirmación de recogida.
            - "completed" : finalizó la recogida del usuario asignado.
        color          (tuple)          : Color RGB para representación visual.
    """
    id:             int
    position:       Position
    target_user_id: Optional[int]       = field(default=None)
    route:          list[Position]      = field(default_factory=list)
    status:         TaxiStatus          = field(default="available")
    color:          tuple               = field(default=(0, 120, 215))   # Azul por defecto

    # ------------------------------------------------------------------
    # Métodos de movimiento
    # ------------------------------------------------------------------

    def move_to(self, new_position: Position) -> None:
        """
        Mueve el taxi a una nueva celda de la grilla.

        Si la ruta no está vacía, elimina el primer paso (ya recorrido).
        No valida si la celda es transitable; esa lógica recae en el
        CollisionManager y el SimulationEngine.

        Args:
            new_position (Position): Celda destino del movimiento.
        """
        self.position = new_position
        # Avanzar en la ruta: descartar el paso que acaba de completarse.
        if self.route and self.route[0] == new_position:
            self.route.pop(0)

    # ------------------------------------------------------------------
    # Métodos de asignación
    # ------------------------------------------------------------------

    def assign_user(self, user_id: int, route: list[Position]) -> None:
        """
        Asigna un usuario al taxi y establece la ruta hacia él.

        Cambia el estado a "assigned" e inicializa la ruta de navegación.

        Args:
            user_id (int)           : ID del usuario a recoger.
            route   (list[Position]): Ruta calculada desde la posición
                                      actual del taxi hasta el usuario.
        """
        self.target_user_id = user_id
        self.route          = route
        self.status         = "assigned"

    def clear_assignment(self) -> None:
        """
        Libera la asignación actual del taxi.

        Restablece todos los campos relacionados con la tarea en curso
        y vuelve el estado a "available".
        Útil cuando el usuario ya fue recogido o la tarea fue cancelada.
        """
        self.target_user_id = None
        self.route          = []
        self.status         = "available"

    # ------------------------------------------------------------------
    # Propiedades de consulta
    # ------------------------------------------------------------------

    @property
    def is_available(self) -> bool:
        """Retorna True si el taxi no tiene ninguna asignación activa."""
        return self.status == "available"

    @property
    def has_route(self) -> bool:
        """Retorna True si el taxi tiene pasos pendientes en su ruta."""
        return len(self.route) > 0

    def __repr__(self) -> str:
        return (
            f"Taxi(id={self.id}, pos={self.position}, "
            f"status='{self.status}', target={self.target_user_id})"
        )


# ---------------------------------------------------------------------------
# UserRequest
# ---------------------------------------------------------------------------

@dataclass
class UserRequest:
    """
    Pasajero estático que espera ser recogido en una celda de la grilla.

    Atributos:
        id           (int)     : Identificador único del usuario.
        position     (Position): Celda donde el usuario espera.
        priority     (int)     : Prioridad de recogida (mayor valor = más urgente).
        waiting_time (int)     : Pasos de tiempo que lleva esperando.
        assigned     (bool)    : True si ya tiene un taxi asignado.
        completed    (bool)    : True si ya fue recogido exitosamente.
    """
    id:           int
    position:     Position
    priority:     int  = field(default=1)
    waiting_time: int  = field(default=0)
    assigned:     bool = field(default=False)
    completed:    bool = field(default=False)

    # ------------------------------------------------------------------
    # Métodos de ciclo de vida
    # ------------------------------------------------------------------

    def mark_completed(self) -> None:
        """
        Marca al usuario como recogido exitosamente.

        Establece 'completed' en True y 'assigned' en True (consistencia).
        Una vez completado, el usuario no debe ser reasignado.
        """
        self.assigned  = True
        self.completed = True

    def increment_waiting(self) -> None:
        """
        Incrementa en 1 el contador de pasos de tiempo en espera.

        Debe llamarse en cada tick de la simulación para los usuarios
        que aún no han sido recogidos.
        """
        if not self.completed:
            self.waiting_time += 1

    # ------------------------------------------------------------------
    # Propiedades de consulta
    # ------------------------------------------------------------------

    @property
    def is_pending(self) -> bool:
        """Retorna True si el usuario todavía está esperando ser recogido."""
        return not self.completed

    @property
    def is_unassigned(self) -> bool:
        """Retorna True si el usuario no tiene taxi asignado aún."""
        return not self.assigned and not self.completed

    def __repr__(self) -> str:
        return (
            f"UserRequest(id={self.id}, pos={self.position}, "
            f"assigned={self.assigned}, completed={self.completed})"
        )


# ---------------------------------------------------------------------------
# Obstacle
# ---------------------------------------------------------------------------

# Tipos de obstáculo válidos en la ciudad.
ObstacleKind = str  # Literal["building", "park", "tree", "construction", "accident"]

@dataclass
class Obstacle:
    """
    Celda o grupo de celdas bloqueadas dentro de la grilla de ciudad.

    Un obstáculo puede ocupar una o más celdas contiguas (p. ej., un
    edificio grande). Ningún taxi puede transitar por estas celdas.

    Atributos:
        id    (int)            : Identificador único del obstáculo.
        cells (list[Position]) : Lista de celdas que ocupa el obstáculo.
        kind  (ObstacleKind)   : Tipo de obstáculo urbano.
            - "building"     : edificio.
            - "park"         : parque o zona verde.
            - "tree"         : árbol en medio de la vía.
            - "construction" : zona de construcción.
            - "accident"     : accidente de tránsito.
    """
    id:    int
    cells: list[Position]  = field(default_factory=list)
    kind:  ObstacleKind    = field(default="building")

    # ------------------------------------------------------------------
    # Métodos de utilidad
    # ------------------------------------------------------------------

    def contains(self, position: Position) -> bool:
        """
        Verifica si una posición dada está bloqueada por este obstáculo.

        Args:
            position (Position): Celda a verificar.

        Returns:
            bool: True si la celda pertenece a este obstáculo.
        """
        return position in self.cells

    def __repr__(self) -> str:
        return (
            f"Obstacle(id={self.id}, kind='{self.kind}', "
            f"cells={len(self.cells)})"
        )
