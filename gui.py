"""
gui.py
======
Interfaz gráfica del SmartRide Planner usando Tkinter.
"""

import tkinter as tk
from simulation import Simulation
from models import CellType, Position
from pathfinding import (
    ROUTE_ASTAR,
    ROUTE_ALGORITHM_LABELS,
    ROUTE_ALGORITHM_VALUE_BY_LABEL,
)
from decision_policy import (
    STRATEGY_DISTANCE,
    STRATEGY_PRIORITY,
    STRATEGY_WAITING,
    STRATEGY_WEIGHTED,
    STRATEGY_LABELS,
)

# ---------------------------------------------------------------------------
# Constantes de diseño
# ---------------------------------------------------------------------------
CELL_SIZE = 32
GRID_SIZE = 20
CANVAS_W  = CELL_SIZE * GRID_SIZE
CANVAS_H  = CELL_SIZE * GRID_SIZE
PANEL_W   = 600
TICK_MS   = 350

# Paleta
C_ROAD       = "#C8CBD0"
C_ROAD_LINE  = "#B0B3B8"
C_BUILDING   = "#4A4A5E"
C_WIN        = "#90CAF9"
C_TAXI_BODY  = "#FFD600"
C_TAXI_OUT   = "#222222"
C_TAXI_WIN   = "#B3E5FC"
C_TAXI_WHEEL = "#333333"
C_USER_P1    = "#1565C0"   # azul   - prioridad 1
C_USER_P2    = "#6A1B9A"   # morado - prioridad 2
C_USER_P3    = "#C62828"   # rojo   - prioridad 3
C_ROUTE      = "#B3E5FC"
C_BG         = "#1A1A2E"
C_PANEL_CARD = "#12122A"
C_TEXT       = "#FFFFFF"
C_TEXT_DIM   = "#9090AA"
C_BTN_GO     = "#00C853"
C_BTN_PAUSE  = "#FF6D00"
C_BTN_STEP   = "#2979FF"
C_BTN_RESET  = "#D32F2F"


# ---------------------------------------------------------------------------
# Clase principal
# ---------------------------------------------------------------------------

class SmartRideGUI:
    SCENARIOS = [
        "city_complete",
        "obstacles",
        "high_demand_zone",
    ]

    SCENARIO_LABELS = {
        "city_complete": "Ciudad completa",
        "obstacles": "Ciudad con obstáculos",
        "high_demand_zone": "Zona de alta demanda",
    }

    SCENARIO_VALUE_BY_LABEL = {
        "Ciudad completa": "city_complete",
        "Ciudad con obstáculos": "obstacles",
        "Zona de alta demanda": "high_demand_zone",
    }

    TAXI_OPTIONS = ["1", "2", "3"]

    USER_OPTIONS = ["1", "2", "3", "4", "5", "6", "7", "8", "9"]


    # Métodos de decisión disponibles en la interfaz.
    STRATEGY_OPTIONS = [
        STRATEGY_LABELS[STRATEGY_DISTANCE],
        STRATEGY_LABELS[STRATEGY_PRIORITY],
    ]

    # Conversión entre lo que ve el usuario y lo que usa la lógica interna.
    STRATEGY_VALUE_BY_LABEL = {
        STRATEGY_LABELS[STRATEGY_DISTANCE]: STRATEGY_DISTANCE,
        STRATEGY_LABELS[STRATEGY_PRIORITY]: STRATEGY_PRIORITY,
        STRATEGY_LABELS[STRATEGY_WAITING]: STRATEGY_WAITING,
        STRATEGY_LABELS[STRATEGY_WEIGHTED]: STRATEGY_WEIGHTED,
    }

    ROUTE_OPTIONS = [
        ROUTE_ALGORITHM_LABELS[ROUTE_ASTAR],
        ROUTE_ALGORITHM_LABELS["dijkstra"],
        ROUTE_ALGORITHM_LABELS["bfs"],
        ROUTE_ALGORITHM_LABELS["greedy"],
    ]

    # Color de usuario según prioridad
    _USER_COLOR = {1: C_USER_P1, 2: C_USER_P2, 3: C_USER_P3}

    def __init__(self) -> None:
        self.simulation = Simulation()
        self._running   = False
        self._after_id  = None

        self._build_window()
        self._build_canvas()
        self._build_panel()
        self._draw()

    # ------------------------------------------------------------------
    # Construcción de la ventana
    # ------------------------------------------------------------------

    def _build_window(self) -> None:
        self.root = tk.Tk()
        self.root.title("SmartRide Planner — Simulación Urbana")
        self.root.resizable(False, False)
        self.root.configure(bg=C_BG)

        total_w = CANVAS_W + PANEL_W + 36
        total_h = CANVAS_H + 20
        sw = self.root.winfo_screenwidth()
        sh = self.root.winfo_screenheight()
        ox = (sw - total_w) // 2
        oy = max((sh - total_h) // 2, 0)
        self.root.geometry(f"{total_w}x{total_h}+{ox}+{oy}")

    def _build_canvas(self) -> None:
        frame = tk.Frame(self.root, bg="#0D0D1A", bd=2, relief="ridge")
        frame.pack(side=tk.LEFT, padx=(10, 4), pady=10)
        self.canvas = tk.Canvas(
            frame, width=CANVAS_W, height=CANVAS_H,
            bg=C_ROAD, highlightthickness=0,
        )
        self.canvas.pack()

    # ------------------------------------------------------------------
    # Panel lateral
    # ------------------------------------------------------------------

    def _build_panel(self) -> None:
        """
        Construye el panel lateral derecho con scroll vertical.
        """

        # ============================================================
        # CONTENEDOR CON SCROLL
        # ============================================================

        panel_container = tk.Frame(self.root, bg=C_BG, width=PANEL_W)
        panel_container.pack(side=tk.RIGHT, fill=tk.Y, padx=(0, 8), pady=10)
        panel_container.pack_propagate(False)

        panel_canvas = tk.Canvas(
            panel_container,
            bg=C_BG,
            highlightthickness=0,
            width=PANEL_W - 18,
        )

        panel_scrollbar = tk.Scrollbar(
            panel_container,
            orient="vertical",
            command=panel_canvas.yview,
        )

        panel = tk.Frame(panel_canvas, bg=C_BG)

        panel_window = panel_canvas.create_window(
            (0, 0),
            window=panel,
            anchor="nw",
        )

        def _on_panel_configure(_event) -> None:
            panel_canvas.configure(scrollregion=panel_canvas.bbox("all"))

        def _on_canvas_configure(event) -> None:
            panel_canvas.itemconfig(panel_window, width=event.width)

        def _on_mousewheel(event) -> None:
            panel_canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

        panel.bind("<Configure>", _on_panel_configure)
        panel_canvas.bind("<Configure>", _on_canvas_configure)
        panel_canvas.configure(yscrollcommand=panel_scrollbar.set)

        panel_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        panel_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        panel_canvas.bind_all("<MouseWheel>", _on_mousewheel)

        # ============================================================
        # TÍTULO
        # ============================================================

        tk.Label(
            panel,
            text="SmartRide",
            bg=C_BG,
            fg="#7C4DFF",
            font=("Arial", 15, "bold"),
        ).pack(pady=(8, 0))

        tk.Label(
            panel,
            text="PLANNER",
            bg=C_BG,
            fg="#B39DDB",
            font=("Arial", 8, "bold"),
        ).pack()

        tk.Frame(
            panel,
            bg="#7C4DFF",
            height=2,
        ).pack(fill=tk.X, padx=16, pady=5)

        # ============================================================
        # ESTADÍSTICAS
        # ============================================================

        stats = tk.Frame(panel, bg=C_PANEL_CARD, bd=1, relief="ridge")
        stats.pack(fill=tk.X, padx=12, pady=2)

        self._lbl_tick = self._stat_row(stats, "Tick")
        self._lbl_completed = self._stat_row(stats, "Completados")
        self._lbl_pending = self._stat_row(stats, "Pendientes")

        # ============================================================
        # ESCENARIO
        # ============================================================

        tk.Frame(panel, bg="#3D3D5C", height=1).pack(
            fill=tk.X, padx=16, pady=5
        )

        tk.Label(
            panel,
            text="ESCENARIO",
            bg=C_BG,
            fg=C_TEXT_DIM,
            font=("Arial", 7, "bold"),
        ).pack(anchor="w", padx=14)

        self.selected_scenario = tk.StringVar(value="Ciudad completa")

        scenario_frame = tk.Frame(
            panel,
            bg="#252540",
            bd=1,
            relief="ridge",
        )
        scenario_frame.pack(fill=tk.X, padx=12, pady=(2, 1))

        scenario_menu = tk.OptionMenu(
            scenario_frame,
            self.selected_scenario,
            *list(self.SCENARIO_VALUE_BY_LABEL.keys()),
        )

        scenario_menu.config(
            bg="#252540",
            fg=C_TEXT,
            activebackground="#7C4DFF",
            activeforeground="white",
            font=("Arial", 8),
            relief="flat",
            highlightthickness=0,
            bd=0,
        )

        scenario_menu["menu"].config(
            bg="#252540",
            fg=C_TEXT,
            activebackground="#7C4DFF",
            activeforeground="white",
            font=("Arial", 8),
        )

        scenario_menu.pack(fill=tk.X)

        self._lbl_scenario = tk.Label(
            panel,
            text="Activo: Ciudad completa",
            bg=C_BG,
            fg="#7C4DFF",
            font=("Arial", 7, "italic"),
        )
        self._lbl_scenario.pack(anchor="w", padx=14, pady=(1, 2))



        # ============================================================
        # ALGORITMO DE RUTA
        # ============================================================

        tk.Frame(panel, bg="#3D3D5C", height=1).pack(
            fill=tk.X, padx=16, pady=5
        )

        tk.Label(
            panel,
            text="ALGORITMO DE RUTA",
            bg=C_BG,
            fg=C_TEXT_DIM,
            font=("Arial", 7, "bold"),
        ).pack(anchor="w", padx=14)

        self.selected_route_algorithm = tk.StringVar(value="A*")

        route_frame = tk.Frame(
            panel,
            bg="#252540",
            bd=1,
            relief="ridge",
        )
        route_frame.pack(fill=tk.X, padx=12, pady=(2, 1))

        route_menu = tk.OptionMenu(
            route_frame,
            self.selected_route_algorithm,
            *self.ROUTE_OPTIONS,
        )

        route_menu.config(
            bg="#252540",
            fg=C_TEXT,
            activebackground="#7C4DFF",
            activeforeground="white",
            font=("Arial", 8),
            relief="flat",
            highlightthickness=0,
            bd=0,
        )

        route_menu["menu"].config(
            bg="#252540",
            fg=C_TEXT,
            activebackground="#7C4DFF",
            activeforeground="white",
            font=("Arial", 8),
        )

        route_menu.pack(fill=tk.X)

        self._lbl_route_algorithm = tk.Label(
            panel,
            text="Ruta: A*",
            bg=C_BG,
            fg="#7C4DFF",
            font=("Arial", 7, "italic"),
        )
        self._lbl_route_algorithm.pack(anchor="w", padx=14, pady=(1, 2))





        # ============================================================
        # MÉTODO DE DECISIÓN
        # ============================================================

        tk.Frame(panel, bg="#3D3D5C", height=1).pack(
            fill=tk.X, padx=16, pady=5
        )

        tk.Label(
            panel,
            text="CRITERIO DE ASIGNACIÓN",
            bg=C_BG,
            fg=C_TEXT_DIM,
            font=("Arial", 7, "bold"),
        ).pack(anchor="w", padx=14)

        self.selected_strategy = tk.StringVar(
            value=STRATEGY_LABELS[STRATEGY_DISTANCE]
        )

        strategy_frame = tk.Frame(
            panel,
            bg="#252540",
            bd=1,
            relief="ridge",
        )
        strategy_frame.pack(fill=tk.X, padx=12, pady=(2, 1))

        strategy_menu = tk.OptionMenu(
            strategy_frame,
            self.selected_strategy,
            *self.STRATEGY_OPTIONS,
        )

        strategy_menu.config(
            bg="#252540",
            fg=C_TEXT,
            activebackground="#7C4DFF",
            activeforeground="white",
            font=("Arial", 8),
            relief="flat",
            highlightthickness=0,
            bd=0,
        )

        strategy_menu["menu"].config(
            bg="#252540",
            fg=C_TEXT,
            activebackground="#7C4DFF",
            activeforeground="white",
            font=("Arial", 8),
        )

        strategy_menu.pack(fill=tk.X)

        self._lbl_strategy = tk.Label(
            panel,
            text=f"Método: {self.selected_strategy.get()}",
            bg=C_BG,
            fg="#7C4DFF",
            font=("Arial", 7, "italic"),
        )
        self._lbl_strategy.pack(anchor="w", padx=14, pady=(1, 2))

        # ============================================================
        # CONFIGURACIÓN
        # ============================================================

        tk.Frame(panel, bg="#3D3D5C", height=1).pack(
            fill=tk.X, padx=16, pady=5
        )

        tk.Label(
            panel,
            text="CONFIGURACIÓN",
            bg=C_BG,
            fg=C_TEXT_DIM,
            font=("Arial", 7, "bold"),
        ).pack(anchor="w", padx=14)

        config_card = tk.Frame(panel, bg=C_PANEL_CARD, bd=1, relief="ridge")
        config_card.pack(fill=tk.X, padx=12, pady=2)

        # ---------- Taxis ----------
        taxi_row = tk.Frame(config_card, bg=C_PANEL_CARD)
        taxi_row.pack(fill=tk.X, padx=8, pady=(5, 2))

        tk.Label(
            taxi_row,
            text="Taxis (máx. 3)",
            bg=C_PANEL_CARD,
            fg=C_TEXT_DIM,
            font=("Arial", 8),
        ).pack(side=tk.LEFT)

        self.selected_num_taxis = tk.StringVar(value="3")

        taxi_menu = tk.OptionMenu(
            taxi_row,
            self.selected_num_taxis,
            *self.TAXI_OPTIONS,
        )

        taxi_menu.config(
            bg="#252540",
            fg=C_TEXT,
            activebackground="#7C4DFF",
            activeforeground="white",
            font=("Arial", 8),
            relief="flat",
            highlightthickness=0,
            bd=0,
            width=4,
        )

        taxi_menu["menu"].config(
            bg="#252540",
            fg=C_TEXT,
            activebackground="#7C4DFF",
            activeforeground="white",
            font=("Arial", 8),
        )

        taxi_menu.pack(side=tk.RIGHT)

        # ---------- Usuarios ----------
        user_row = tk.Frame(config_card, bg=C_PANEL_CARD)
        user_row.pack(fill=tk.X, padx=8, pady=(2, 5))

        tk.Label(
            user_row,
            text="Usuarios (1-9)",
            bg=C_PANEL_CARD,
            fg=C_TEXT_DIM,
            font=("Arial", 8),
        ).pack(side=tk.LEFT)

        self.selected_num_users = tk.StringVar(value="5")

        user_menu = tk.OptionMenu(
            user_row,
            self.selected_num_users,
            *self.USER_OPTIONS,
        )

        user_menu.config(
            bg="#252540",
            fg=C_TEXT,
            activebackground="#7C4DFF",
            activeforeground="white",
            font=("Arial", 8),
            relief="flat",
            highlightthickness=0,
            bd=0,
            width=4,
        )

        user_menu["menu"].config(
            bg="#252540",
            fg=C_TEXT,
            activebackground="#7C4DFF",
            activeforeground="white",
            font=("Arial", 8),
        )

        user_menu.pack(side=tk.RIGHT)

        self._lbl_config_help = tk.Label(
            config_card,
            text="Los cambios aplican al reiniciar.",
            bg=C_PANEL_CARD,
            fg=C_TEXT_DIM,
            font=("Arial", 7, "italic"),
            justify="left",
        )
        self._lbl_config_help.pack(anchor="w", padx=8, pady=(0, 5))

        # ============================================================
        # BOTONES
        # ============================================================

        tk.Frame(panel, bg="#3D3D5C", height=1).pack(
            fill=tk.X, padx=16, pady=5
        )

        btn_cfg = dict(
            font=("Arial", 9, "bold"),
            relief="flat",
            cursor="hand2",
            pady=6,
        )

        self._btn_go = tk.Button(
            panel,
            text="▶  Iniciar",
            bg=C_BTN_GO,
            fg="white",
            command=self._toggle_run,
            **btn_cfg,
        )
        self._btn_go.pack(fill=tk.X, padx=12, pady=2)

        tk.Button(
            panel,
            text="⏭  Paso a paso",
            bg=C_BTN_STEP,
            fg="white",
            command=self._step_once,
            **btn_cfg,
        ).pack(fill=tk.X, padx=12, pady=2)

        tk.Button(
            panel,
            text="↺  Reiniciar",
            bg=C_BTN_RESET,
            fg="white",
            command=self._restart,
            **btn_cfg,
        ).pack(fill=tk.X, padx=12, pady=2)

        # Se conserva para compatibilidad con métodos anteriores.
        self._taxi_frame = tk.Frame(panel, bg=C_BG)

        # ============================================================
        # DECISIÓN DEL SISTEMA
        # ============================================================

        tk.Frame(panel, bg="#3D3D5C", height=1).pack(
            fill=tk.X, padx=16, pady=5
        )

        tk.Label(
            panel,
            text="DECISIÓN DEL SISTEMA",
            bg=C_BG,
            fg=C_TEXT_DIM,
            font=("Arial", 7, "bold"),
        ).pack(anchor="w", padx=14)

        decision_card = tk.Frame(panel, bg=C_PANEL_CARD, bd=1, relief="ridge")
        decision_card.pack(fill=tk.X, padx=12, pady=2)

        self._lbl_method_help = tk.Label(
            decision_card,
            text="Menor distancia: usa d = pasos de la ruta A*.",
            bg=C_PANEL_CARD,
            fg=C_TEXT_DIM,
            font=("Arial", 7),
            justify="left",
            wraplength=500,
        )
        self._lbl_method_help.pack(anchor="w", padx=8, pady=(5, 2))

        self._lbl_right_of_way = tk.Label(
            decision_card,
            text="Derecho de paso: -",
            bg=C_PANEL_CARD,
            fg="#FFD600",
            font=("Arial", 7, "bold"),
            justify="left",
            wraplength=500,
        )
        self._lbl_right_of_way.pack(anchor="w", padx=8, pady=(2, 5))

        # ============================================================
        # TABLA DE TAXIS
        # ============================================================

        tk.Frame(panel, bg="#3D3D5C", height=1).pack(
            fill=tk.X, padx=16, pady=5
        )

        tk.Label(
            panel,
            text="TAXIS / POSICIÓN / DESTINO",
            bg=C_BG,
            fg=C_TEXT_DIM,
            font=("Arial", 7, "bold"),
        ).pack(anchor="w", padx=14)

        taxis_card = tk.Frame(panel, bg=C_PANEL_CARD, bd=1, relief="ridge")
        taxis_card.pack(fill=tk.X, padx=12, pady=2)

        self._lbl_taxis_table = tk.Label(
            taxis_card,
            text="Sin datos",
            bg=C_PANEL_CARD,
            fg=C_TEXT,
            font=("Consolas", 7),
            justify="left",
            anchor="w",
            wraplength=500,
        )
        self._lbl_taxis_table.pack(anchor="w", padx=8, pady=5)

        # ============================================================
        # TABLA DE USUARIOS
        # ============================================================

        tk.Frame(panel, bg="#3D3D5C", height=1).pack(
            fill=tk.X, padx=16, pady=5
        )

        tk.Label(
            panel,
            text="USUARIOS / PRIORIDAD / ESPERA",
            bg=C_BG,
            fg=C_TEXT_DIM,
            font=("Arial", 7, "bold"),
        ).pack(anchor="w", padx=14)

        users_card = tk.Frame(panel, bg=C_PANEL_CARD, bd=1, relief="ridge")
        users_card.pack(fill=tk.X, padx=12, pady=2)

        self._lbl_users_table = tk.Label(
            users_card,
            text="Sin datos",
            bg=C_PANEL_CARD,
            fg=C_TEXT,
            font=("Consolas", 7),
            justify="left",
            anchor="w",
            wraplength=500,
        )
        self._lbl_users_table.pack(anchor="w", padx=8, pady=5)

        # ============================================================
        # LEYENDA
        # ============================================================

        tk.Frame(panel, bg="#3D3D5C", height=1).pack(
            fill=tk.X, padx=16, pady=5
        )

        tk.Label(
            panel,
            text="LEYENDA",
            bg=C_BG,
            fg=C_TEXT_DIM,
            font=("Arial", 7, "bold"),
        ).pack(anchor="w", padx=14)

        leg = tk.Frame(panel, bg=C_BG)
        leg.pack(fill=tk.X, padx=12, pady=2)

        for color, label in [
            (C_ROAD, "Calle"),
            (C_BUILDING, "Edificio / obstáculo"),
            (C_TAXI_BODY, "Taxi / agente"),
            (C_USER_P1, "Azul = Normal / prioridad 1"),
            (C_USER_P2, "Morado = Importante / prioridad 2"),
            (C_USER_P3, "Rojo = Urgente / prioridad 3"),
            (C_ROUTE, "Ruta planeada"),
        ]:
            self._legend_row(leg, color, label)

    # ------------------------------------------------------------------
    # Widgets auxiliares
    # ------------------------------------------------------------------

    def _stat_row(self, parent: tk.Frame, label: str) -> tk.Label:
        row = tk.Frame(parent, bg=C_PANEL_CARD)
        row.pack(fill=tk.X, padx=8, pady=3)
        tk.Label(row, text=label, bg=C_PANEL_CARD,
                 fg=C_TEXT_DIM, font=("Arial", 8)).pack(side=tk.LEFT)
        val = tk.Label(row, text="0", bg=C_PANEL_CARD,
                       fg=C_TEXT, font=("Arial", 9, "bold"))
        val.pack(side=tk.RIGHT)
        return val

    def _legend_row(self, parent: tk.Frame, color: str, text: str) -> None:
        row = tk.Frame(parent, bg=C_BG)
        row.pack(fill=tk.X, pady=1)
        tk.Frame(row, bg=color, width=11, height=11,
                 bd=1, relief="solid").pack(side=tk.LEFT, padx=(0, 5))
        tk.Label(row, text=text, bg=C_BG,
                 fg=C_TEXT_DIM, font=("Arial", 7)).pack(side=tk.LEFT)

    # ------------------------------------------------------------------
    # Dibujo principal
    # ------------------------------------------------------------------
    def _get_selected_strategy(self) -> str:
        """
        Retorna la estrategia interna seleccionada en la GUI.

        La interfaz muestra etiquetas legibles para el usuario, pero
        Simulation necesita el nombre interno de la estrategia.
        """
        selected_label = self.selected_strategy.get()

        return self.STRATEGY_VALUE_BY_LABEL.get(
            selected_label,
            STRATEGY_DISTANCE,
        )


    def _get_selected_num_taxis(self) -> int:
        """
        Retorna el número de taxis seleccionado por el usuario.

        El proyecto usa máximo 3 taxis para mantener claridad visual.
        """
        try:
            value = int(self.selected_num_taxis.get())
        except Exception:
            value = 3

        return max(1, min(value, 3))




    def _get_selected_num_users(self) -> int:
        """
        Retorna el número de usuarios seleccionado por el usuario.
        """
        try:
            value = int(self.selected_num_users.get())
        except Exception:
            value = 5

        return max(1, min(value, 9))



    def _get_selected_scenario(self) -> str:
        """
        Retorna el nombre interno del escenario seleccionado.

        La GUI muestra nombres legibles, pero Simulation usa nombres internos.
        """
        selected_label = self.selected_scenario.get()

        return self.SCENARIO_VALUE_BY_LABEL.get(
            selected_label,
            "city_complete",
        )


    def _get_selected_route_algorithm(self) -> str:
        """
        Retorna el algoritmo interno seleccionado para calcular rutas.
        """
        selected_label = self.selected_route_algorithm.get()

        return ROUTE_ALGORITHM_VALUE_BY_LABEL.get(
            selected_label,
            ROUTE_ASTAR,
    )




    def _draw(self) -> None:
        self.canvas.delete("all")

        # Mapa posición → kind de obstáculo
        obs_kind: dict[Position, str] = {}
        for obs in self.simulation.city_grid.obstacles:
            for cell in obs.cells:
                obs_kind[cell] = obs.kind

        # Celdas de ruta activas
        route_cells: dict[Position, str] = {}
        for taxi in self.simulation.city_grid.taxis:
            for pos in taxi.route:
                route_cells[pos] = C_ROUTE

        # ---- Celdas ------------------------------------------------
        for r in range(GRID_SIZE):
            for c in range(GRID_SIZE):
                pos = Position(r, c)
                x0, y0 = c * CELL_SIZE, r * CELL_SIZE
                x1, y1 = x0 + CELL_SIZE, y0 + CELL_SIZE

                if self.simulation.city_grid.get_cell_type(pos) == CellType.OBSTACLE:
                    self._draw_building(x0, y0, x1, y1)
                else:
                    self._draw_road(x0, y0, x1, y1)
                    if pos in route_cells:
                        self._draw_route(x0, y0, x1, y1)

        # ---- Usuarios ----------------------------------------------
        for user in self.simulation.city_grid.users:
            if not user.completed:
                color = self._USER_COLOR.get(user.priority, C_USER_P1)
                self._draw_user(user.position, color)

        # ---- Taxis -------------------------------------------------
        for taxi in self.simulation.city_grid.taxis:
            self._draw_taxi(taxi.position, taxi.id)

        # ---- Panel -------------------------------------------------
        self._update_panel()

    # ------------------------------------------------------------------
    # Celdas base
    # ------------------------------------------------------------------

    def _draw_road(self, x0, y0, x1, y1) -> None:
        self.canvas.create_rectangle(
            x0, y0, x1, y1, fill=C_ROAD, outline=C_ROAD_LINE, width=1)

    def _draw_route(self, x0, y0, x1, y1) -> None:
        p = 5
        self.canvas.create_rectangle(
            x0+p, y0+p, x1-p, y1-p, fill=C_ROUTE, outline="", width=0)

    def _draw_building(self, x0, y0, x1, y1) -> None:
        self.canvas.create_rectangle(
            x0, y0, x1, y1, fill=C_BUILDING, outline="#333344", width=1)
        ws, gap = 5, 4
        for wr in range(2):
            for wc in range(2):
                wx = x0 + gap + wc * (ws + gap)
                wy = y0 + gap + wr * (ws + gap)
                if wx + ws < x1 - 1 and wy + ws < y1 - 1:
                    self.canvas.create_rectangle(
                        wx, wy, wx+ws, wy+ws, fill=C_WIN, outline="")

    # ------------------------------------------------------------------
    # Agentes
    # ------------------------------------------------------------------

    def _draw_user(self, pos: Position, color: str) -> None:
        cx = pos.col * CELL_SIZE + CELL_SIZE // 2
        cy = pos.row * CELL_SIZE + CELL_SIZE // 2
        r  = CELL_SIZE // 4
        self.canvas.create_oval(
            cx-r, cy-r-4, cx+r, cy+r-4,
            fill=color, outline="white", width=1)
        self.canvas.create_polygon(
            cx-3, cy+r-4, cx+3, cy+r-4, cx, cy+r+5,
            fill=color, outline="")
        self.canvas.create_oval(
            cx-3, cy-7, cx+3, cy-1, fill="white", outline="")

    def _draw_taxi(self, pos: Position, tid: int) -> None:
        """Taxi siempre dibujado en amarillo."""
        cx = pos.col * CELL_SIZE + CELL_SIZE // 2
        cy = pos.row * CELL_SIZE + CELL_SIZE // 2
        hw = CELL_SIZE // 2 - 3
        hh = CELL_SIZE // 2 - 4
        x0, y0 = cx - hw, cy - hh
        x1, y1 = cx + hw, cy + hh

        # Cuerpo
        self.canvas.create_rectangle(
            x0, y0+5, x1, y1, fill=C_TAXI_BODY, outline=C_TAXI_OUT, width=1)
        # Techo
        rp = 5
        self.canvas.create_rectangle(
            x0+rp, y0, x1-rp, y0+7, fill=C_TAXI_BODY, outline=C_TAXI_OUT, width=1)
        # Parabrisas
        self.canvas.create_rectangle(
            x0+rp+1, y0+1, x1-rp-1, y0+6, fill=C_TAXI_WIN, outline="")
        # Ruedas
        wr = 3
        for wx, wy in [
            (x0+4, y1-2), (x1-4, y1-2),
            (x0+4, y0+6), (x1-4, y0+6),
        ]:
            self.canvas.create_oval(
                wx-wr, wy-wr, wx+wr, wy+wr, fill=C_TAXI_WHEEL, outline="")
        # ID
        self.canvas.create_text(
            cx, cy+3, text=str(tid), font=("Arial", 7, "bold"), fill=C_TAXI_OUT)

    # ------------------------------------------------------------------
    # Panel lateral
    # ------------------------------------------------------------------
    def _format_users_decision_table(self, user_rows: list[dict]) -> str:
        """
        Construye una tabla compacta de usuarios.

        Muestra:
            - ID del usuario,
            - posición,
            - color,
            - prioridad,
            - tiempo de espera,
            - taxi asignado.
        """
        if not user_rows:
            return "No hay usuarios pendientes."

        lines = [
            "U  Pos      Color  Prioridad   W  Taxi",
            "-- -------- ------ ---------- -- ----",
        ]

        for row in user_rows[:8]:
            user_id = row["user_id"]
            position = row["position"]
            color = row["priority_color"][:6]
            priority = row["priority_label"][:10]
            waiting = row["waiting_time"]
            taxi = row["assigned_taxi"]

            lines.append(
                f"U{user_id:<1} {position:<8} {color:<6} "
                f"{priority:<10} {waiting:<2} {taxi:<4}"
            )

        return "\n".join(lines)



    def _format_taxis_decision_table(self, taxi_rows: list[dict]) -> str:
        """
        Construye una tabla compacta de taxis.

        Muestra:
            - ID del taxi,
            - posición actual,
            - usuario objetivo,
            - coordenada destino,
            - distancia restante,
            - score.
        """
        if not taxi_rows:
            return "No hay taxis activos."

        lines = [
            "T  Pos      Obj Destino  Dist Score",
            "-- -------- --- -------- ---- ------",
        ]

        for row in taxi_rows[:5]:
            taxi_id = row["taxi_id"]
            position = row["position"]
            target = row["target_user"]
            target_position = row["target_position"]
            distance = row["remaining_distance"]
            score = row["score"]

            lines.append(
                f"T{taxi_id:<1} {position:<8} {target:<3} "
                f"{target_position:<8} {str(distance):<4} {score}"
            )

        return "\n".join(lines)




    def _update_panel(self) -> None:
        state = self.simulation.get_state()
        self._lbl_tick.config(text=str(state["tick_count"]))
        total = max(state.get("total_tasks", 1), 1)
        self._lbl_completed.config(text=f"{state['completed_tasks']} / {total}")
        self._lbl_pending.config(text=str(state["pending_users"]))
        self._lbl_scenario.config(text=f"Activo: {self.simulation.scenario_name}")
        self._lbl_strategy.config(text=f"Método: {self.selected_strategy.get()}")
        self._lbl_route_algorithm.config(
        text=f"Ruta: {self.selected_route_algorithm.get()}"
        )
        selected_taxis = self._get_selected_num_taxis()
        selected_users = self._get_selected_num_users()

        self._lbl_config_help.config(
            text=(
                f"Seleccionado: {selected_taxis} taxis | {selected_users} usuarios\n"
                f"Activo: {state['total_taxis']} taxis | "
                f"Usuarios iniciales: {state.get('total_tasks', 0)}\n"
                f"Para aplicar cambios: Reiniciar"
            )
        )
        decision_snapshot = self.simulation.get_decision_snapshot()

        self._lbl_method_help.config(
            text=(
                f"{decision_snapshot['route_algorithm_explanation']}\n"
                f"{decision_snapshot['strategy_explanation']}"
            )
        )

        self._lbl_right_of_way.config(
            text=f"Derecho de paso: {decision_snapshot['right_of_way']}"
        )

        taxis_table_text = self._format_taxis_decision_table(
            decision_snapshot["taxi_rows"]
        )

        users_table_text = self._format_users_decision_table(
            decision_snapshot["user_rows"]
        )

        self._lbl_taxis_table.config(text=taxis_table_text)
        self._lbl_users_table.config(text=users_table_text)

        for w in self._taxi_frame.winfo_children():
            w.destroy()

        status_fg = {
            "available": "#00C853",
            "assigned":  "#FFAB00",
            "waiting":   "#2979FF",
            "completed": "#9E9EAE",
        }

        for taxi in self.simulation.city_grid.taxis:
            card = tk.Frame(self._taxi_frame, bg=C_PANEL_CARD, bd=1, relief="ridge")
            card.pack(fill=tk.X, pady=1)

            # Franja amarilla fija
            tk.Frame(card, bg=C_TAXI_BODY, width=4).pack(side=tk.LEFT, fill=tk.Y)

            pos_txt = f"({taxi.position.row},{taxi.position.col})"
            if taxi.target_user_id is not None:
                pos_txt += f" → U{taxi.target_user_id}"
            status = taxi.status.upper()[:6]
            line = f"Taxi #{taxi.id} | {status} | {pos_txt}"

            tk.Label(card, text=line, bg=C_PANEL_CARD,
                     fg=status_fg.get(taxi.status, C_TEXT),
                     font=("Arial", 7), anchor="w").pack(
                         side=tk.LEFT, fill=tk.X, expand=True, padx=4, pady=2)

    # ------------------------------------------------------------------
    # Control de simulación
    # ------------------------------------------------------------------

    def _toggle_run(self) -> None:
        if self._running:
            self._running = False
            if self._after_id:
                self.root.after_cancel(self._after_id)
                self._after_id = None
            self._btn_go.config(text="▶  Iniciar", bg=C_BTN_GO)
        else:
            if self.simulation.is_finished():
                return
            self._running = True
            self._btn_go.config(text="⏸  Pausar", bg=C_BTN_PAUSE)
            self._auto_step()

    def _auto_step(self) -> None:
        """
        Ejecuta la simulación automática.

        Antes de cada tick sincroniza:
            - criterio de asignación,
            - algoritmo de ruta.
        """
        if not self._running:
            return

        if self.simulation.is_finished():
            self._running = False
            self._btn_go.config(text="✓  Finalizado", bg="#616161")
            self._draw()
            return

        self.simulation.assignment_strategy = self._get_selected_strategy()
        self.simulation.route_algorithm = self._get_selected_route_algorithm()

        self.simulation.step()
        self._draw()

        self._after_id = self.root.after(TICK_MS, self._auto_step)

    def _step_once(self) -> None:
        """
        Ejecuta un solo tick de simulación.

        Antes de avanzar, sincroniza:
            - criterio de asignación,
            - algoritmo de ruta.
        """
        if self.simulation.is_finished():
            return

        self.simulation.assignment_strategy = self._get_selected_strategy()
        self.simulation.route_algorithm = self._get_selected_route_algorithm()

        self.simulation.step()
        self._draw()

    def _restart(self) -> None:
        """
        Reinicia la simulación usando la configuración seleccionada.
        """
        if self._after_id is not None:
            self.root.after_cancel(self._after_id)
            self._after_id = None

        self._running = False
        self._btn_go.config(text="▶  Iniciar", bg=C_BTN_GO)

        scenario = self._get_selected_scenario()
        scenario_label = self.selected_scenario.get()
        strategy = self._get_selected_strategy()
        num_taxis = self._get_selected_num_taxis()
        num_users = self._get_selected_num_users()
        route_algorithm = self._get_selected_route_algorithm()

        self.simulation = Simulation(
            scenario_name=scenario,
            randomize=True,
            assignment_strategy=strategy,
            route_algorithm=route_algorithm,
            num_taxis=num_taxis,
            num_users=num_users,
        )

        self._lbl_scenario.config(text=f"Activo: {scenario_label}")
        self._lbl_strategy.config(text=f"Método: {self.selected_strategy.get()}")
        self._lbl_route_algorithm.config(
            text=f"Ruta: {self.selected_route_algorithm.get()}"
        )

        self._draw()

    # ------------------------------------------------------------------
    # Utilidades
    # ------------------------------------------------------------------

    def run(self) -> None:
        self.root.mainloop()


# ---------------------------------------------------------------------------

if __name__ == "__main__":
    app = SmartRideGUI()
    app.run()
