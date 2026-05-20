# SmartRide Planner

SmartRide Planner es una simulación de planeación de movimiento multi-agente en una ciudad discretizada como una grilla rectangular.

El entorno representa una ciudad dividida en celdas. Cada celda puede ser una calle libre, un obstáculo urbano, un taxi autónomo o un usuario que solicita ser recogido.

## Objetivo del proyecto

Desarrollar un sistema capaz de coordinar varios taxis autónomos para recoger usuarios distribuidos en la ciudad, evitando obstáculos y previniendo colisiones entre agentes.

## Elementos del modelo

- Workspace: ciudad rectangular discretizada en celdas.
- Agentes: taxis autónomos.
- Tareas: usuarios esperando ser recogidos.
- Obstáculos: edificios, parques, árboles, casas, accidentes o zonas de construcción.
- Colisiones: dos taxis no pueden ocupar la misma celda al mismo tiempo ni intercambiar posiciones simultáneamente.

## Versión 1

La primera versión del sistema incluye:

- Grilla de 20 x 20 celdas.
- 3 taxis.
- 5 usuarios.
- Obstáculos urbanos estáticos.
- Movimiento en cuatro direcciones: arriba, abajo, izquierda y derecha.
- Planeación de rutas usando A*.
- Asignación de taxis a usuarios mediante el menor costo real de ruta.
- Control básico de colisiones.
- Interfaz gráfica en Python.

## Algoritmos principales

- A* para la búsqueda de rutas.
- Asignación greedy basada en distancia real de ruta.
- Control de colisiones por pasos de tiempo.

## Entregables

- Código fuente funcional.
- Módulo de pruebas.
- Informe en PDF escrito en LaTeX.
- Video de sustentación de máximo 10 minutos.

## Estructura del proyecto

```
smart_ride_planner/
├── main.py              # Punto de entrada principal de la aplicación
├── models.py            # Definición de entidades: Taxi, Usuario, Obstáculo
├── city_grid.py         # Representación y gestión de la grilla de ciudad
├── pathfinding.py       # Algoritmo A* para búsqueda de rutas
├── assignment.py        # Asignación greedy de taxis a usuarios
├── collision_manager.py # Control y prevención de colisiones entre agentes
├── simulation.py        # Motor de simulación por pasos de tiempo
├── gui.py               # Interfaz gráfica con tkinter
├── tests.py             # Módulo de pruebas unitarias
└── README.md            # Documentación del proyecto
```

## Requisitos

- Python 3.10+
- tkinter (incluido en la instalación estándar de Python)

## Cómo ejecutar

```bash
python main.py
```
