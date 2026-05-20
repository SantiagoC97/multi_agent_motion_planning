"""
gui.py
======
Interfaz gráfica del SmartRide Planner usando Tkinter.
"""

import tkinter as tk
from simulation import Simulation
from models import CellType, Position

# ---------------------------------------------------------------------------
# Constantes de diseño
# ---------------------------------------------------------------------------
CELL_SIZE = 28
GRID_SIZE = 20
CANVAS_W  = CELL_SIZE * GRID_SIZE
CANVAS_H  = CELL_SIZE * GRID_SIZE
PANEL_W   = 240
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
        "basic",
        "city_complete",
        "obstacles",
        "high_demand_zone",
        "priority_users",
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
        panel = tk.Frame(self.root, bg=C_BG, width=PANEL_W)
        panel.pack(side=tk.RIGHT, fill=tk.Y, padx=(0, 8), pady=10)
        panel.pack_propagate(False)

        # ── Título ──────────────────────────────────────────────────────
        tk.Label(panel, text="SmartRide", bg=C_BG,
                 fg="#7C4DFF", font=("Arial", 15, "bold")).pack(pady=(10, 0))
        tk.Label(panel, text="PLANNER", bg=C_BG,
                 fg="#B39DDB", font=("Arial", 8, "bold")).pack()
        tk.Frame(panel, bg="#7C4DFF", height=2).pack(fill=tk.X, padx=16, pady=6)

        # ── Estadísticas ─────────────────────────────────────────────────
        stats = tk.Frame(panel, bg=C_PANEL_CARD, bd=1, relief="ridge")
        stats.pack(fill=tk.X, padx=12, pady=2)
        self._lbl_tick      = self._stat_row(stats, "Tick")
        self._lbl_completed = self._stat_row(stats, "Completados")
        self._lbl_pending   = self._stat_row(stats, "Pendientes")

        # ── Selector de escenario ─────────────────────────────────────────
        tk.Frame(panel, bg="#3D3D5C", height=1).pack(fill=tk.X, padx=16, pady=5)
        tk.Label(panel, text="ESCENARIO", bg=C_BG,
                 fg=C_TEXT_DIM, font=("Arial", 7, "bold")).pack(anchor="w", padx=14)

        self.selected_scenario = tk.StringVar(value="city_complete")

        om_frame = tk.Frame(panel, bg="#252540", bd=1, relief="ridge")
        om_frame.pack(fill=tk.X, padx=12, pady=(2, 1))
        om = tk.OptionMenu(om_frame, self.selected_scenario, *self.SCENARIOS)
        om.config(
            bg="#252540", fg=C_TEXT,
            activebackground="#7C4DFF", activeforeground="white",
            font=("Arial", 8), relief="flat",
            highlightthickness=0, bd=0,
        )
        om["menu"].config(
            bg="#252540", fg=C_TEXT,
            activebackground="#7C4DFF", activeforeground="white",
            font=("Arial", 8),
        )
        om.pack(fill=tk.X)

        self._lbl_scenario = tk.Label(
            panel, text="Activo: city_complete",
            bg=C_BG, fg="#7C4DFF", font=("Arial", 7, "italic"),
        )
        self._lbl_scenario.pack(anchor="w", padx=14, pady=(1, 2))

        # ── Botones ───────────────────────────────────────────────────────
        tk.Frame(panel, bg="#3D3D5C", height=1).pack(fill=tk.X, padx=16, pady=4)
        btn_cfg = dict(font=("Arial", 9, "bold"), relief="flat", cursor="hand2", pady=6)

        self._btn_go = tk.Button(
            panel, text="▶  Iniciar", bg=C_BTN_GO, fg="white",
            command=self._toggle_run, **btn_cfg,
        )
        self._btn_go.pack(fill=tk.X, padx=12, pady=2)

        tk.Button(
            panel, text="⏭  Paso a paso", bg=C_BTN_STEP, fg="white",
            command=self._step_once, **btn_cfg,
        ).pack(fill=tk.X, padx=12, pady=2)

        tk.Button(
            panel, text="↺  Reiniciar", bg=C_BTN_RESET, fg="white",
            command=self._restart, **btn_cfg,
        ).pack(fill=tk.X, padx=12, pady=2)

        # ── Estado taxis ──────────────────────────────────────────────────
        tk.Frame(panel, bg="#3D3D5C", height=1).pack(fill=tk.X, padx=16, pady=5)
        tk.Label(panel, text="TAXIS", bg=C_BG,
                 fg=C_TEXT_DIM, font=("Arial", 7, "bold")).pack(anchor="w", padx=14)

        self._taxi_frame = tk.Frame(panel, bg=C_BG)
        self._taxi_frame.pack(fill=tk.X, padx=10, pady=2)

        # ── Leyenda ───────────────────────────────────────────────────────
        tk.Frame(panel, bg="#3D3D5C", height=1).pack(fill=tk.X, padx=16, pady=5)
        tk.Label(panel, text="LEYENDA", bg=C_BG,
                 fg=C_TEXT_DIM, font=("Arial", 7, "bold")).pack(anchor="w", padx=14)

        leg = tk.Frame(panel, bg=C_BG)
        leg.pack(fill=tk.X, padx=12, pady=2)
        for color, label in [
            (C_ROAD,    "Calle"),
            (C_BUILDING,"Edificio"),
            (C_TAXI_BODY, "Taxi"),
            (C_USER_P1, "Usuario P1 (normal)"),
            (C_USER_P2, "Usuario P2 (importante)"),
            (C_USER_P3, "Usuario P3 (urgente)"),
            (C_ROUTE,   "Ruta"),
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

    def _update_panel(self) -> None:
        state = self.simulation.get_state()
        self._lbl_tick.config(text=str(state["tick_count"]))
        total = max(state["completed_tasks"] + state["pending_users"], 1)
        self._lbl_completed.config(text=f"{state['completed_tasks']} / {total}")
        self._lbl_pending.config(text=str(state["pending_users"]))
        self._lbl_scenario.config(text=f"Activo: {self.simulation.scenario_name}")

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
        if not self._running:
            return
        if self.simulation.is_finished():
            self._running = False
            self._btn_go.config(text="✓  Finalizado", bg="#616161")
            self._draw()
            return
        self.simulation.step()
        self._draw()
        self._after_id = self.root.after(TICK_MS, self._auto_step)

    def _step_once(self) -> None:
        if not self.simulation.is_finished():
            self.simulation.step()
            self._draw()

    def _restart(self) -> None:
        if self._running:
            self._running = False
            if self._after_id:
                self.root.after_cancel(self._after_id)
                self._after_id = None
        self.simulation = Simulation(scenario_name=self.selected_scenario.get())
        self._btn_go.config(text="▶  Iniciar", bg=C_BTN_GO)
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
