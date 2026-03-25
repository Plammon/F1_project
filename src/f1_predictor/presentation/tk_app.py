"""Tkinter desktop interface for the prediction demo."""

from __future__ import annotations

import tkinter as tk
from threading import Thread
from tkinter import ttk

from f1_predictor.application.controller import PredictionController
from f1_predictor.data.repository import RaceDataRepository
from f1_predictor.domain.models import PredictionInput, PredictionResult


class F1PredictorApp(tk.Tk):
    def __init__(self, controller: PredictionController) -> None:
        super().__init__()
        self.controller = controller
        self.title("F1 Predictor")
        self.geometry("920x620")
        self.configure(bg="#f6f4ef")
        self.resizable(True, True)

        self._season_var = tk.StringVar()
        self._grand_prix_var = tk.StringVar()
        self._strategy_var = tk.StringVar()
        self._status_var = tk.StringVar(
            value="Choose a race weekend to generate pre-race winner odds."
        )
        self._winner_var = tk.StringVar(value="Predicted winner: -")
        self._source_var = tk.StringVar(value="Data source: -")
        self._factors_var = tk.StringVar(value="Why this result: -")

        self._build_layout()
        self._populate_filters()

    def _build_layout(self) -> None:
        header = tk.Frame(self, bg="#0f172a", padx=24, pady=24)
        header.pack(fill="x")
        tk.Label(
            header,
            text="F1 Predictor",
            fg="#f8fafc",
            bg="#0f172a",
            font=("Segoe UI", 24, "bold"),
        ).pack(anchor="w")
        tk.Label(
            header,
            text="Pre-race winner odds for casual Formula 1 fans",
            fg="#cbd5e1",
            bg="#0f172a",
            font=("Segoe UI", 12),
        ).pack(anchor="w", pady=(6, 0))

        controls = tk.Frame(self, bg="#f6f4ef", padx=24, pady=18)
        controls.pack(fill="x")

        self._season_combo = self._add_combo(controls, "Season", self._season_var, 0)
        self._grand_prix_combo = self._add_combo(
            controls, "Grand Prix", self._grand_prix_var, 1
        )
        self._strategy_combo = self._add_combo(
            controls, "Strategy", self._strategy_var, 2
        )
        self._season_combo.bind("<<ComboboxSelected>>", self._on_season_changed)

        ttk.Button(
            controls,
            text="Run Prediction",
            command=self.run_prediction,
        ).grid(row=1, column=2, sticky="ew", padx=8, pady=(10, 0))

        summary = tk.Frame(self, bg="#f6f4ef", padx=24, pady=8)
        summary.pack(fill="x")
        for value in (
            self._winner_var,
            self._source_var,
            self._factors_var,
            self._status_var,
        ):
            tk.Label(
                summary,
                textvariable=value,
                bg="#f6f4ef",
                fg="#1f2937",
                font=("Segoe UI", 11),
                anchor="w",
                justify="left",
                wraplength=860,
            ).pack(fill="x", pady=2)

        results_frame = tk.Frame(self, bg="#f6f4ef", padx=24, pady=12)
        results_frame.pack(fill="both", expand=True)

        columns = ("driver", "probability")
        self._tree = ttk.Treeview(
            results_frame, columns=columns, show="headings", height=12
        )
        self._tree.heading("driver", text="Driver")
        self._tree.heading("probability", text="Win Probability")
        self._tree.column("driver", width=320)
        self._tree.column("probability", width=160, anchor="center")
        self._tree.pack(fill="both", expand=True)

    def _add_combo(
        self,
        parent: tk.Widget,
        label: str,
        variable: tk.StringVar,
        column: int,
    ) -> ttk.Combobox:
        frame = tk.Frame(parent, bg="#f6f4ef")
        frame.grid(row=0, column=column, sticky="ew", padx=8)
        parent.grid_columnconfigure(column, weight=1)
        tk.Label(
            frame,
            text=label,
            bg="#f6f4ef",
            fg="#334155",
            font=("Segoe UI", 11, "bold"),
        ).pack(anchor="w", pady=(0, 4))
        combo = ttk.Combobox(frame, textvariable=variable, state="readonly")
        combo.pack(fill="x")
        return combo

    def _populate_filters(self) -> None:
        seasons = self.controller.available_seasons()
        self._season_combo["values"] = seasons
        self._strategy_combo["values"] = self.controller.available_strategies()
        if seasons:
            self._season_var.set(seasons[0])
            self._on_season_changed()
        if self._strategy_combo["values"]:
            self._strategy_var.set(self._strategy_combo["values"][0])

    def _on_season_changed(self, *_args) -> None:
        season = self._season_var.get()
        grand_prix_options = self.controller.available_grand_prix(season)
        self._grand_prix_combo["values"] = grand_prix_options
        if grand_prix_options:
            self._grand_prix_var.set(grand_prix_options[0])

    def run_prediction(self) -> None:
        self._status_var.set("Running prediction...")
        worker = Thread(target=self._run_prediction_worker, daemon=True)
        worker.start()

    def _run_prediction_worker(self) -> None:
        try:
            prediction_input = PredictionInput(
                season=self._season_var.get(),
                grand_prix=self._grand_prix_var.get(),
                selected_strategy=self._strategy_var.get(),
            )
            result = self.controller.run_prediction(prediction_input)
            self.after(0, lambda: self.render_result(result))
        except Exception as exc:
            message = str(exc)
            self.after(0, lambda: self._handle_prediction_error(message))

    def _handle_prediction_error(self, message: str) -> None:
        self._winner_var.set("Predicted winner: -")
        self._source_var.set("Data source: unavailable")
        self._factors_var.set("Why this result: unavailable because prediction failed.")
        self._status_var.set(f"Prediction failed: {message}")

    def render_result(self, result: PredictionResult) -> None:
        self._winner_var.set(f"Predicted winner: {result.predicted_winner}")
        self._source_var.set(f"Data source: {result.data_source}")
        self._factors_var.set(
            "Why this result: " + " ".join(result.top_features_or_factors)
        )
        self._status_var.set(
            f"Generated at {result.generated_at.strftime('%Y-%m-%d %H:%M:%S %Z')}."
        )

        for item in self._tree.get_children():
            self._tree.delete(item)
        for driver, probability in result.driver_probabilities.items():
            self._tree.insert("", "end", values=(driver, f"{probability}%"))

    def launch_app(self) -> None:
        self.mainloop()


def launch_app(repository: RaceDataRepository) -> None:
    controller = PredictionController(repository)
    app = F1PredictorApp(controller)
    app.launch_app()
