# SmartRide Planner — Notas del proyecto

## Estado actual

El sistema implementa una simulación de planeación de movimiento multiagente en una grilla de 20x20. Los agentes se representan como taxis y las tareas como usuarios con diferentes prioridades.

## Componentes principales

- Interfaz gráfica en Tkinter.
- Generación aleatoria de escenarios.
- Algoritmos de ruta: A*, Dijkstra, BFS y Greedy Best-First.
- Criterios de asignación: taxi más cercano y usuario prioritario.
- Manejo de colisiones entre agentes.
- Replaneación dinámica ante bloqueos persistentes.
- Suite de pruebas con 28 casos.

## Validación

Antes de subir el proyecto se ejecutó:

python tests.py

Resultado esperado:

28 OK | 0 ERROR | Total: 28

## Pendientes de entrega

- Informe en LaTeX.
- Capturas de la interfaz.
- Guion para video de sustentación.
