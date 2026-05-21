"""
decision_policy.py
==================
Políticas de decisión para SmartRide Planner.

Este módulo centraliza los criterios que utiliza el sistema para decidir:

    1. Qué taxi debe atender a qué usuario.
    2. Qué taxi tiene derecho de paso cuando hay conflicto de movimiento.
    3. Qué información debe mostrarse en la interfaz para justificar
       la decisión tomada.

Estrategias disponibles:

    - distance:
        Favorece menor distancia.

    - priority:
        Favorece usuarios con mayor prioridad.

    - waiting:
        Favorece usuarios con mayor tiempo de espera.

    - weighted:
        Combina distancia, prioridad y tiempo de espera.

Convención:
    Menor score = mejor decisión.

Importante:
    Para el derecho de paso entre taxis, la prioridad del usuario siempre
    domina. Esto evita que un taxi que atiende un usuario urgente quede
    cediendo paso frente a un taxi que atiende un usuario normal.
"""

from __future__ import annotations

from models import Taxi, UserRequest


# ---------------------------------------------------------------------------
# Estrategias internas
# ---------------------------------------------------------------------------

STRATEGY_DISTANCE = "distance"
STRATEGY_PRIORITY = "priority"
STRATEGY_WAITING = "waiting"
STRATEGY_WEIGHTED = "weighted"


VALID_STRATEGIES = {
    STRATEGY_DISTANCE,
    STRATEGY_PRIORITY,
    STRATEGY_WAITING,
    STRATEGY_WEIGHTED,
}


# ---------------------------------------------------------------------------
# Etiquetas visibles en GUI
# ---------------------------------------------------------------------------

STRATEGY_LABELS = {
    STRATEGY_DISTANCE: "Taxi más cercano",
    STRATEGY_PRIORITY: "Usuario prioritario",
    STRATEGY_WAITING: "Mayor espera del usuario",
    STRATEGY_WEIGHTED: "Costo ponderado",
}


# ---------------------------------------------------------------------------
# Parámetros del costo ponderado
# ---------------------------------------------------------------------------

DEFAULT_ALPHA_DISTANCE = 1.0
DEFAULT_BETA_PRIORITY = 8.0
DEFAULT_GAMMA_WAITING = 1.5


# ---------------------------------------------------------------------------
# Prioridades de usuario
# ---------------------------------------------------------------------------

PRIORITY_LABELS = {
    1: "Normal",
    2: "Importante",
    3: "Urgente",
}

PRIORITY_COLOR_NAMES = {
    1: "Azul",
    2: "Morado",
    3: "Rojo",
}


# ---------------------------------------------------------------------------
# Funciones auxiliares
# ---------------------------------------------------------------------------

def normalize_strategy(strategy: str | None) -> str:
    """
    Verifica si una estrategia es válida.

    Si llega una estrategia inválida, retorna distance por seguridad.
    """
    if strategy in VALID_STRATEGIES:
        return strategy

    return STRATEGY_DISTANCE


def priority_label(priority: int) -> str:
    """
    Retorna el nombre textual de una prioridad.
    """
    return PRIORITY_LABELS.get(priority, "Normal")


def priority_color_name(priority: int) -> str:
    """
    Retorna el color textual asociado a una prioridad.
    """
    return PRIORITY_COLOR_NAMES.get(priority, "Azul")


def weighted_cost_value(
    distance: float,
    priority: float,
    waiting_time: float,
) -> float:
    """
    Calcula el costo ponderado usado por la estrategia weighted.

    No representa precio económico. Representa un costo computacional
    de decisión.

    C = alpha*d - beta*P - gamma*W

    Donde:
        d = distancia o ruta restante.
        P = prioridad del usuario.
        W = tiempo de espera.
    """
    return (
        DEFAULT_ALPHA_DISTANCE * distance
        - DEFAULT_BETA_PRIORITY * priority
        - DEFAULT_GAMMA_WAITING * waiting_time
    )


def strategy_explanation(strategy: str) -> str:
    """
    Retorna una explicación breve para mostrar en la GUI.

    Esta explicación aclara qué dato usa cada método de decisión.
    """
    strategy = normalize_strategy(strategy)

    if strategy == STRATEGY_DISTANCE:
        return (
            "Menor distancia / llegada rápida: "
            "usa d = pasos de la ruta A*. Menor d gana."
        )

    if strategy == STRATEGY_PRIORITY:
        return (
            "Prioridad: Rojo/Urgente > Morado/Importante > Azul/Normal."
        )

    if strategy == STRATEGY_WAITING:
        return (
            "Mayor espera: usa W = ticks esperando. Mayor W gana."
        )

    if strategy == STRATEGY_WEIGHTED:
        return (
            "Costo ponderado: C = 1*d - 8*P - 1.5*W. "
            "Menor C gana."
        )

    return "El sistema usa menor distancia."


# ---------------------------------------------------------------------------
# Score de asignación taxi-usuario
# ---------------------------------------------------------------------------

def assignment_score(
    taxi: Taxi,
    user: UserRequest,
    route_cost: int,
    strategy: str = STRATEGY_DISTANCE,
) -> float:
    """
    Calcula el score para asignar un taxi a un usuario.

    Este score se usa para decidir qué taxi atiende a qué usuario.

    Menor score = mejor asignación.
    """
    strategy = normalize_strategy(strategy)

    distance = float(route_cost)
    priority = float(user.priority)
    waiting_time = float(user.waiting_time)

    if strategy == STRATEGY_DISTANCE:
        return distance

    if strategy == STRATEGY_PRIORITY:
        # La prioridad domina sobre la distancia.
        return distance - 100.0 * priority

    if strategy == STRATEGY_WAITING:
        # El tiempo de espera domina sobre la distancia.
        return distance - 100.0 * waiting_time

    if strategy == STRATEGY_WEIGHTED:
        return weighted_cost_value(
            distance=distance,
            priority=priority,
            waiting_time=waiting_time,
        )

    return distance


# ---------------------------------------------------------------------------
# Score de derecho de paso
# ---------------------------------------------------------------------------

def movement_score(
    taxi: Taxi,
    target_user: UserRequest | None,
    remaining_cost: int,
    strategy: str = STRATEGY_DISTANCE,
) -> float:
    """
    Calcula el score de derecho de paso de un taxi.

    Este score se usa cuando dos o más taxis pueden entrar en conflicto.

    Regla principal:
        La prioridad del usuario asignado siempre domina.

    Esto significa que un taxi atendiendo a un usuario urgente tiene mayor
    derecho de paso que uno atendiendo a un usuario normal, incluso si el
    método elegido por la GUI es distancia o costo ponderado.

    Menor score = mayor prioridad de movimiento.
    """
    strategy = normalize_strategy(strategy)

    if target_user is None:
        return 1_000_000.0 + taxi.id

    distance = float(remaining_cost)
    priority = float(target_user.priority)
    waiting_time = float(target_user.waiting_time)

    # Bloque dominante:
    # prioridad 3 genera un score mucho menor que prioridad 2 o 1.
    priority_dominance = -10_000.0 * priority

    if strategy == STRATEGY_DISTANCE:
        secondary = distance

    elif strategy == STRATEGY_PRIORITY:
        secondary = distance - 100.0 * waiting_time

    elif strategy == STRATEGY_WAITING:
        secondary = distance - 100.0 * waiting_time

    elif strategy == STRATEGY_WEIGHTED:
        secondary = weighted_cost_value(
            distance=distance,
            priority=priority,
            waiting_time=waiting_time,
        )

    else:
        secondary = distance

    return priority_dominance + secondary


def movement_score_details(
    taxi: Taxi,
    target_user: UserRequest | None,
    remaining_cost: int,
    strategy: str = STRATEGY_DISTANCE,
) -> dict:
    """
    Retorna los datos usados para justificar el derecho de paso.

    Esta función es útil para la interfaz, porque permite mostrar:
        - usuario asignado,
        - prioridad,
        - color,
        - espera,
        - distancia restante,
        - score final.
    """
    strategy = normalize_strategy(strategy)

    if target_user is None:
        return {
            "taxi_id": taxi.id,
            "user_id": None,
            "priority": None,
            "priority_label": "Sin usuario",
            "priority_color": "-",
            "waiting_time": 0,
            "remaining_distance": remaining_cost,
            "score": movement_score(taxi, None, remaining_cost, strategy),
        }

    score = movement_score(
        taxi=taxi,
        target_user=target_user,
        remaining_cost=remaining_cost,
        strategy=strategy,
    )

    return {
        "taxi_id": taxi.id,
        "user_id": target_user.id,
        "priority": target_user.priority,
        "priority_label": priority_label(target_user.priority),
        "priority_color": priority_color_name(target_user.priority),
        "waiting_time": target_user.waiting_time,
        "remaining_distance": remaining_cost,
        "score": score,
    }