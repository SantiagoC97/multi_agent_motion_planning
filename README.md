# SmartRide Planner — Planeación de Movimiento Multiagente

SmartRide Planner es una simulación urbana en una grilla discreta de 20x20 para resolver un problema de planeación de movimiento multiagente. El sistema representa taxis autónomos que deben recoger usuarios en una ciudad con obstáculos, evitando colisiones y calculando rutas de forma coordinada.

## Características principales

- Espacio de trabajo rectangular discretizado en celdas.
- Múltiples agentes tipo taxi.
- Usuarios con diferentes niveles de prioridad.
- Obstáculos representados como edificios.
- Generación aleatoria de escenarios.
- Cantidad configurable de taxis.
- Cantidad configurable de usuarios.
- Planeación de rutas con varios algoritmos:
  - A*
  - Dijkstra
  - BFS
  - Greedy Best-First
- Criterios de asignación:
  - Taxi más cercano
  - Usuario prioritario
- Resolución de colisiones:
  - Conflicto por misma celda
  - Conflicto por intercambio de posición
  - Cruce local de rutas
- Replaneación dinámica ante bloqueos persistentes.
- Interfaz gráfica en Tkinter.
- Suite de pruebas manuales.

## Prioridades de usuarios

| Color | Prioridad | Significado |
|---|---:|---|
| Azul | 1 | Usuario normal |
| Morado | 2 | Usuario importante |
| Rojo | 3 | Usuario urgente |

## Algoritmos de ruta

El entorno se modela como una grilla, donde cada celda libre representa un nodo del grafo y cada movimiento válido representa una arista. Los algoritmos implementados permiten comparar diferentes estrategias de búsqueda:

- **A\***: búsqueda informada usando costo acumulado y heurística Manhattan.
- **Dijkstra**: búsqueda por costo acumulado mínimo.
- **BFS**: búsqueda por niveles, adecuada para grillas no ponderadas.
- **Greedy Best-First**: búsqueda guiada únicamente por heurística.

## Criterios de asignación

- **Taxi más cercano**: asigna el taxi con menor distancia calculada hacia el usuario.
- **Usuario prioritario**: atiende primero usuarios urgentes, luego importantes y luego normales.

## Cómo ejecutar

```bash
python main.py