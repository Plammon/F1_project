"""Tkinter desktop interface for the finished live-data predictor."""

from __future__ import annotations

import logging
import tkinter as tk
from threading import Thread
from tkinter import ttk

from f1_predictor import __version__
from f1_predictor.application.controller import PredictionController
from f1_predictor.data.repository import RaceDataRepository
from f1_predictor.domain.models import (
    HistoricalComparison,
    PredictionInput,
    PredictionResult,
    RaceWeekendOption,
)
from f1_predictor.paths import resolve_path
from f1_predictor.presentation.view_models import (
    PredictionViewModel,
    build_empty_state,
    build_error_state,
    build_loading_state,
    build_result_state,
)

logger = logging.getLogger(__name__)


class F1PredictorApp(tk.Tk):
    def __init__(self, controller: PredictionController) -> None:
        super().__init__()
        self.controller = controller
        self._weekends: list[RaceWeekendOption] = self.controller.available_weekends()
        self._weekends_by_season = self._group_weekends(self._weekends)
        self._historical_checks: dict[tuple[str, str], HistoricalComparison] = {}
        self._controls_locked = False

        self._configure_window_identity()
        self.geometry("1180x800")
        self.minsize(1020, 700)
        self.configure(bg="#eef1ea")

        self._season_var = tk.StringVar()
        self._grand_prix_var = tk.StringVar()
        self._grand_prix_filter_var = tk.StringVar()
        self._strategy_var = tk.StringVar()
        self._support_mode_var = tk.StringVar(value="Waiting for live schedule")
        self._error_var = tk.StringVar(value="")
        self._actual_result_note_var = tk.StringVar(value="")
        self._validation_summary_var = tk.StringVar(
            value="Historical validation updates after you check a completed race."
        )

        self._build_styles()
        self._build_shell()
        self._populate_filters()
        self._apply_view_model(build_empty_state())
        self._render_validation_history()

    def _configure_window_identity(self) -> None:
        self.title(f"F1 Predictor Desktop v{__version__}")
        icon_path = resolve_path("assets", "f1_predictor.ico")
        if icon_path.exists():
            try:
                self.iconbitmap(default=str(icon_path))
            except tk.TclError:
                logger.info("Window icon could not be applied from %s", icon_path)

    def _build_styles(self) -> None:
        style = ttk.Style(self)
        style.theme_use("clam")
        style.configure(
            "Telemetry.TCombobox",
            fieldbackground="#fbfaf7",
            background="#fbfaf7",
            foreground="#132033",
            borderwidth=0,
            padding=8,
        )
        style.configure(
            "Telemetry.Treeview",
            background="#fbfaf7",
            fieldbackground="#fbfaf7",
            foreground="#132033",
            rowheight=34,
            borderwidth=0,
            font=("Segoe UI", 11),
        )
        style.configure(
            "Telemetry.Treeview.Heading",
            background="#dbe3f2",
            foreground="#132033",
            relief="flat",
            font=("Segoe UI", 10, "bold"),
            padding=8,
        )
        style.configure(
            "Telemetry.Horizontal.TProgressbar",
            troughcolor="#d8e2d5",
            background="#d6572b",
            borderwidth=0,
            lightcolor="#d6572b",
            darkcolor="#d6572b",
        )
        style.map(
            "Telemetry.Treeview",
            background=[("selected", "#dfe8ff")],
            foreground=[("selected", "#132033")],
        )

    def _build_shell(self) -> None:
        self.columnconfigure(0, weight=1)
        self.rowconfigure(2, weight=1)

        self._build_header()
        self._build_control_bar()
        self._build_content_area()

    def _build_header(self) -> None:
        header = tk.Frame(self, bg="#101a2b", padx=26, pady=22)
        header.grid(row=0, column=0, sticky="ew", padx=18, pady=(18, 12))
        header.columnconfigure(0, weight=1)

        text_block = tk.Frame(header, bg="#101a2b")
        text_block.grid(row=0, column=0, sticky="w")

        tk.Label(
            text_block,
            text="F1 Predictor",
            bg="#101a2b",
            fg="#f6f7fb",
            font=("Segoe UI Semibold", 26),
        ).grid(row=0, column=0, sticky="w")
        tk.Label(
            text_block,
            text=f"Windows desktop release v{__version__}",
            bg="#20304a",
            fg="#dce5f5",
            font=("Segoe UI", 10, "bold"),
            padx=10,
            pady=6,
        ).grid(row=0, column=1, sticky="w", padx=(12, 0))
        tk.Label(
            text_block,
            text=(
                "A live-data desktop forecast for casual Formula 1 fans. "
                "Compare strategies, review real podiums, and keep track of how the forecast performs."
            ),
            bg="#101a2b",
            fg="#cad4e8",
            font=("Segoe UI", 11),
            wraplength=760,
            justify="left",
        ).grid(row=1, column=0, columnspan=2, sticky="w", pady=(8, 0))

        tk.Label(
            header,
            text="Live FastF1 schedule | Strategy comparison | Historical validation",
            bg="#101a2b",
            fg="#89d6b7",
            font=("Segoe UI", 10, "bold"),
        ).grid(row=0, column=1, sticky="e")

    def _build_control_bar(self) -> None:
        controls = tk.Frame(self, bg="#dfe7df", padx=20, pady=18)
        controls.grid(row=1, column=0, sticky="ew", padx=18, pady=(0, 12))
        for column in range(4):
            controls.columnconfigure(column, weight=1)

        self._season_combo = self._build_filter(controls, "Season", self._season_var, 0)
        self._grand_prix_frame = self._build_grand_prix_panel(controls, 1)
        self._strategy_combo = self._build_filter(
            controls,
            "Prediction Strategy",
            self._strategy_var,
            2,
        )
        self._season_combo.bind("<<ComboboxSelected>>", self._on_season_changed)
        self._grand_prix_combo.bind("<<ComboboxSelected>>", self._on_grand_prix_changed)
        self._strategy_combo.bind("<<ComboboxSelected>>", self._update_run_button_state)
        self._grand_prix_filter_var.trace_add(
            "write",
            lambda *_args: self._on_grand_prix_filter_changed(),
        )

        action_panel = tk.Frame(controls, bg="#dfe7df")
        action_panel.grid(row=0, column=3, sticky="nsew", padx=10)
        tk.Label(
            action_panel,
            text="Live Data Status",
            bg="#dfe7df",
            fg="#2b3b50",
            font=("Segoe UI", 10, "bold"),
        ).pack(anchor="w", pady=(0, 6))
        self._support_mode_badge = tk.Label(
            action_panel,
            textvariable=self._support_mode_var,
            bg="#edf6ef",
            fg="#1c6b49",
            font=("Segoe UI", 10, "bold"),
            padx=12,
            pady=8,
        )
        self._support_mode_badge.pack(anchor="w", fill="x")
        self._run_button = tk.Button(
            action_panel,
            text="Run Prediction",
            command=self.run_prediction,
            bg="#d6572b",
            fg="#ffffff",
            activebackground="#c34d24",
            activeforeground="#ffffff",
            relief="flat",
            font=("Segoe UI", 11, "bold"),
            cursor="hand2",
            padx=12,
            pady=12,
        )
        self._run_button.pack(anchor="w", fill="x", pady=(12, 0))

        self._progress_label = tk.Label(
            action_panel,
            text="Fetching live data and calculating forecast...",
            bg="#dfe7df",
            fg="#516071",
            font=("Segoe UI", 9),
            justify="left",
            wraplength=220,
        )
        self._progress_bar = ttk.Progressbar(
            action_panel,
            mode="indeterminate",
            style="Telemetry.Horizontal.TProgressbar",
            length=220,
        )

    def _build_filter(
        self,
        parent: tk.Widget,
        label: str,
        variable: tk.StringVar,
        column: int,
    ) -> ttk.Combobox:
        frame = tk.Frame(parent, bg="#dfe7df")
        frame.grid(row=0, column=column, sticky="nsew", padx=10)
        tk.Label(
            frame,
            text=label,
            bg="#dfe7df",
            fg="#2b3b50",
            font=("Segoe UI", 10, "bold"),
        ).pack(anchor="w", pady=(0, 6))
        combo = ttk.Combobox(
            frame,
            textvariable=variable,
            state="readonly",
            style="Telemetry.TCombobox",
            font=("Segoe UI", 11),
        )
        combo.pack(fill="x")
        return combo

    def _build_grand_prix_panel(self, parent: tk.Widget, column: int) -> tk.Frame:
        frame = tk.Frame(parent, bg="#dfe7df")
        frame.grid(row=0, column=column, sticky="nsew", padx=10)
        tk.Label(
            frame,
            text="Grand Prix",
            bg="#dfe7df",
            fg="#2b3b50",
            font=("Segoe UI", 10, "bold"),
        ).pack(anchor="w", pady=(0, 6))
        self._grand_prix_filter_entry = tk.Entry(
            frame,
            textvariable=self._grand_prix_filter_var,
            relief="flat",
            bg="#fbfaf7",
            fg="#132033",
            font=("Segoe UI", 10),
            insertbackground="#132033",
        )
        self._grand_prix_filter_entry.pack(fill="x", pady=(0, 8))
        self._grand_prix_filter_entry.insert(0, "")
        self._grand_prix_combo = ttk.Combobox(
            frame,
            textvariable=self._grand_prix_var,
            state="readonly",
            style="Telemetry.TCombobox",
            font=("Segoe UI", 11),
        )
        self._grand_prix_combo.pack(fill="x")
        return frame

    def _build_content_area(self) -> None:
        content = tk.Frame(self, bg="#eef1ea")
        content.grid(row=2, column=0, sticky="nsew", padx=18, pady=(0, 18))
        content.columnconfigure(0, weight=7)
        content.columnconfigure(1, weight=5)
        content.rowconfigure(0, weight=1)

        left = tk.Frame(content, bg="#eef1ea")
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
        left.rowconfigure(1, weight=1)
        left.columnconfigure(0, weight=1)

        right = tk.Frame(content, bg="#eef1ea")
        right.grid(row=0, column=1, sticky="nsew", padx=(10, 0))
        right.columnconfigure(0, weight=1)

        self._build_summary_panel(left)
        self._build_table_panel(left)
        self._build_story_panel(right)

    def _build_summary_panel(self, parent: tk.Widget) -> None:
        card = tk.Frame(parent, bg="#fbfaf7", padx=22, pady=20)
        card.grid(row=0, column=0, sticky="ew", pady=(0, 12))
        card.columnconfigure(0, weight=1)
        card.columnconfigure(1, weight=0)
        card.columnconfigure(2, weight=0)

        self._headline_label = tk.Label(
            card,
            text="",
            bg="#fbfaf7",
            fg="#101a2b",
            font=("Georgia", 21, "bold"),
            justify="left",
            wraplength=520,
        )
        self._headline_label.grid(row=0, column=0, sticky="w")

        self._source_badge = tk.Label(
            card,
            text="",
            bg="#edf6ef",
            fg="#1c6b49",
            font=("Segoe UI", 10, "bold"),
            padx=12,
            pady=8,
        )
        self._source_badge.grid(row=0, column=1, sticky="e", padx=(12, 8))

        self._confidence_badge = tk.Label(
            card,
            text="",
            bg="#edf1f4",
            fg="#516071",
            font=("Segoe UI", 10, "bold"),
            padx=12,
            pady=8,
        )
        self._confidence_badge.grid(row=0, column=2, sticky="e")

        self._status_label = tk.Label(
            card,
            text="",
            bg="#fbfaf7",
            fg="#506075",
            font=("Segoe UI", 10),
            wraplength=760,
            justify="left",
        )
        self._status_label.grid(row=1, column=0, columnspan=3, sticky="w", pady=(10, 4))

        self._context_label = tk.Label(
            card,
            text="",
            bg="#fbfaf7",
            fg="#68788c",
            font=("Segoe UI", 10),
            wraplength=760,
            justify="left",
        )
        self._context_label.grid(row=2, column=0, columnspan=3, sticky="w")

        self._strategy_label = tk.Label(
            card,
            text="",
            bg="#fbfaf7",
            fg="#d6572b",
            font=("Segoe UI", 10, "bold"),
        )
        self._strategy_label.grid(row=3, column=0, columnspan=3, sticky="w", pady=(8, 0))

        self._error_banner = tk.Label(
            card,
            textvariable=self._error_var,
            bg="#fde8e7",
            fg="#9a251c",
            font=("Segoe UI", 10, "bold"),
            padx=12,
            pady=10,
            wraplength=760,
            justify="left",
        )
        self._error_banner.grid(row=4, column=0, columnspan=3, sticky="ew", pady=(14, 0))
        self._error_banner.grid_remove()

    def _build_table_panel(self, parent: tk.Widget) -> None:
        card = tk.Frame(parent, bg="#fbfaf7", padx=18, pady=18)
        card.grid(row=1, column=0, sticky="nsew")
        card.rowconfigure(1, weight=1)
        card.columnconfigure(0, weight=1)

        tk.Label(
            card,
            text="Forecast Table",
            bg="#fbfaf7",
            fg="#101a2b",
            font=("Segoe UI", 13, "bold"),
        ).grid(row=0, column=0, sticky="w", pady=(0, 12))

        columns = ("rank", "driver", "probability")
        self._tree = ttk.Treeview(
            card,
            columns=columns,
            show="headings",
            style="Telemetry.Treeview",
        )
        self._tree.heading("rank", text="#")
        self._tree.heading("driver", text="Driver")
        self._tree.heading("probability", text="Win Probability")
        self._tree.column("rank", width=56, anchor="center", stretch=False)
        self._tree.column("driver", width=310, anchor="w")
        self._tree.column("probability", width=160, anchor="center", stretch=False)
        self._tree.grid(row=1, column=0, sticky="nsew")

        scrollbar = ttk.Scrollbar(card, orient="vertical", command=self._tree.yview)
        self._tree.configure(yscrollcommand=scrollbar.set)
        scrollbar.grid(row=1, column=1, sticky="ns")

    def _build_story_panel(self, parent: tk.Widget) -> None:
        card = tk.Frame(parent, bg="#101a2b", padx=22, pady=22)
        card.grid(row=0, column=0, sticky="nsew")
        card.columnconfigure(0, weight=1)

        tk.Label(
            card,
            text="What This Forecast Means",
            bg="#101a2b",
            fg="#ffffff",
            font=("Segoe UI", 15, "bold"),
        ).grid(row=0, column=0, sticky="w")

        self._explanation_label = tk.Label(
            card,
            text="",
            bg="#101a2b",
            fg="#dce5f5",
            font=("Segoe UI", 11),
            justify="left",
            wraplength=360,
        )
        self._explanation_label.grid(row=1, column=0, sticky="w", pady=(14, 18))

        tk.Label(
            card,
            text="How to read it",
            bg="#101a2b",
            fg="#89d6b7",
            font=("Segoe UI", 11, "bold"),
        ).grid(row=2, column=0, sticky="w")

        tips_text = (
            "- Balanced is the safest all-round model.\n"
            "- Qualifying Bias leans harder on Saturday pace.\n"
            "- Consistency Bias rewards reliability and stable recent form.\n"
            "- Confidence drops when the leading drivers are too close or the live data is incomplete."
        )
        tk.Label(
            card,
            text=tips_text,
            bg="#101a2b",
            fg="#dce5f5",
            font=("Segoe UI", 10),
            justify="left",
            wraplength=360,
        ).grid(row=3, column=0, sticky="w", pady=(10, 18))

        self._catalog_note = tk.Label(
            card,
            text="",
            bg="#101a2b",
            fg="#a9b9d4",
            font=("Segoe UI", 9),
            justify="left",
            wraplength=360,
        )
        self._catalog_note.grid(row=4, column=0, sticky="w")
        self._build_actual_result_panel(card)
        self._build_validation_panel(card)

    def _build_actual_result_panel(self, parent: tk.Widget) -> None:
        panel = tk.Frame(parent, bg="#16253c", padx=16, pady=16)
        panel.grid(row=5, column=0, sticky="ew", pady=(18, 0))
        panel.columnconfigure(0, weight=1)
        panel.columnconfigure(1, weight=1)

        self._actual_result_title_label = tk.Label(
            panel,
            text="Actual race result",
            bg="#16253c",
            fg="#ffffff",
            font=("Segoe UI", 12, "bold"),
        )
        self._actual_result_title_label.grid(row=0, column=0, columnspan=2, sticky="w")

        self._actual_result_rows: list[tuple[tk.Label, tk.Label]] = []
        for index in range(3):
            place_label = tk.Label(
                panel,
                text="",
                bg="#16253c",
                fg="#89d6b7",
                font=("Segoe UI", 10, "bold"),
            )
            name_label = tk.Label(
                panel,
                text="",
                bg="#16253c",
                fg="#dce5f5",
                font=("Segoe UI", 10),
                justify="left",
                wraplength=250,
            )
            pady = (10 if index == 0 else 6, 0)
            place_label.grid(row=index + 1, column=0, sticky="w", pady=pady)
            name_label.grid(row=index + 1, column=1, sticky="w", pady=pady)
            self._actual_result_rows.append((place_label, name_label))

        self._actual_result_note_label = tk.Label(
            panel,
            textvariable=self._actual_result_note_var,
            bg="#16253c",
            fg="#a9b9d4",
            font=("Segoe UI", 9),
            justify="left",
            wraplength=320,
        )
        self._actual_result_note_label.grid(row=4, column=0, columnspan=2, sticky="w", pady=(12, 0))

    def _build_validation_panel(self, parent: tk.Widget) -> None:
        panel = tk.Frame(parent, bg="#16253c", padx=16, pady=16)
        panel.grid(row=6, column=0, sticky="ew", pady=(18, 0))
        panel.columnconfigure(0, weight=1)

        tk.Label(
            panel,
            text="Validation So Far",
            bg="#16253c",
            fg="#ffffff",
            font=("Segoe UI", 12, "bold"),
        ).grid(row=0, column=0, sticky="w")

        self._validation_summary_label = tk.Label(
            panel,
            textvariable=self._validation_summary_var,
            bg="#16253c",
            fg="#dce5f5",
            font=("Segoe UI", 10),
            justify="left",
            wraplength=340,
        )
        self._validation_summary_label.grid(row=1, column=0, sticky="w", pady=(10, 8))

        self._validation_row_labels: list[tk.Label] = []
        for index in range(3):
            label = tk.Label(
                panel,
                text="",
                bg="#16253c",
                fg="#a9b9d4",
                font=("Segoe UI", 9),
                justify="left",
                wraplength=340,
            )
            label.grid(row=index + 2, column=0, sticky="w", pady=(4, 0))
            self._validation_row_labels.append(label)

    def _group_weekends(
        self,
        weekends: list[RaceWeekendOption],
    ) -> dict[str, list[RaceWeekendOption]]:
        grouped: dict[str, list[RaceWeekendOption]] = {}
        for weekend in weekends:
            grouped.setdefault(weekend.season, []).append(weekend)
        for season in grouped:
            grouped[season] = sorted(grouped[season], key=lambda option: option.grand_prix)
        return grouped

    def _populate_filters(self) -> None:
        seasons = sorted(self._weekends_by_season.keys())
        self._season_combo["values"] = seasons
        self._strategy_combo["values"] = self.controller.available_strategies()
        if self._strategy_combo["values"]:
            self._strategy_var.set(self._strategy_combo["values"][0])

        if seasons:
            self._season_var.set(seasons[0])
            self._refresh_grand_prix_options()
            self._catalog_note.configure(
                text=(
                    f"Live schedule loaded: {len(self._weekends)} race weekends across "
                    f"{len(seasons)} seasons. Use the race filter to jump to a Grand Prix quickly."
                )
            )
        else:
            self._catalog_note.configure(
                text=(
                    "Live schedule is currently unavailable. Check your internet connection "
                    "and FastF1 access, then restart or try again later."
                )
            )
            self._set_support_mode("Live data unavailable")

        self._update_run_button_state()

    def _on_season_changed(self, *_args) -> None:
        self._refresh_grand_prix_options()

    def _on_grand_prix_filter_changed(self) -> None:
        self._refresh_grand_prix_options()

    def _refresh_grand_prix_options(self) -> None:
        season = self._season_var.get()
        weekend_options = self._weekends_by_season.get(season, [])
        filter_text = self._grand_prix_filter_var.get().strip().lower()

        grands_prix = [
            option.grand_prix
            for option in weekend_options
            if not filter_text or filter_text in option.grand_prix.lower()
        ]
        current_selection = self._grand_prix_var.get()
        self._grand_prix_combo["values"] = grands_prix

        if current_selection in grands_prix:
            self._grand_prix_var.set(current_selection)
        elif grands_prix:
            self._grand_prix_var.set(grands_prix[0])
        else:
            self._grand_prix_var.set("")

        self._on_grand_prix_changed()

    def _on_grand_prix_changed(self, *_args) -> None:
        season = self._season_var.get()
        grand_prix = self._grand_prix_var.get()
        weekend = self._find_weekend(season, grand_prix)
        if weekend is not None:
            self._set_support_mode(weekend.support_mode)
        elif self._weekends:
            self._set_support_mode("Selection required")
        else:
            self._set_support_mode("Live data unavailable")
        self._update_run_button_state()

    def _find_weekend(self, season: str, grand_prix: str) -> RaceWeekendOption | None:
        for weekend in self._weekends_by_season.get(season, []):
            if weekend.grand_prix == grand_prix:
                return weekend
        return None

    def run_prediction(self) -> None:
        if not self._has_valid_selection():
            return
        selected_strategy = self._strategy_var.get() or "Balanced"
        self._set_controls_enabled(False)
        self._show_progress()
        self._apply_view_model(build_loading_state(selected_strategy))
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
            logger.exception("Prediction failed for %s %s", self._season_var.get(), self._grand_prix_var.get())
            message = str(exc)
            self.after(0, lambda: self._handle_prediction_error(message))

    def _handle_prediction_error(self, message: str) -> None:
        self._hide_progress()
        self._set_controls_enabled(True)
        self._apply_view_model(build_error_state(message))

    def render_result(self, result: PredictionResult) -> None:
        self._hide_progress()
        self._set_controls_enabled(True)
        self._apply_view_model(build_result_state(result))
        if result.historical_comparison:
            self._record_historical_comparison(result.historical_comparison)
        self._render_validation_history()

    def _record_historical_comparison(self, comparison: HistoricalComparison) -> None:
        key = (comparison.season, comparison.grand_prix)
        self._historical_checks[key] = comparison

    def _render_validation_history(self) -> None:
        checks = list(self._historical_checks.values())
        if not checks:
            self._validation_summary_var.set(
                "Historical validation updates after you check a completed race."
            )
            for label in self._validation_row_labels:
                label.configure(text="")
            return

        winner_hits = sum(1 for check in checks if check.winner_match)
        avg_podium_overlap = sum(check.podium_overlap for check in checks) / len(checks)
        self._validation_summary_var.set(
            f"Checked completed races: {len(checks)} | Winner accuracy: "
            f"{round(winner_hits / len(checks) * 100)}% | "
            f"Average podium overlap: {avg_podium_overlap:.1f}/3"
        )

        recent_checks = list(reversed(checks[-3:]))
        for index, label in enumerate(self._validation_row_labels):
            if index >= len(recent_checks):
                label.configure(text="")
                continue
            comparison = recent_checks[index]
            verdict = "winner hit" if comparison.winner_match else "winner miss"
            label.configure(
                text=(
                    f"{comparison.season} {comparison.grand_prix}: {verdict}, "
                    f"{comparison.podium_overlap}/3 podium overlap."
                )
            )

    def _set_controls_enabled(self, enabled: bool) -> None:
        self._controls_locked = not enabled
        state = "readonly" if enabled else "disabled"
        self._season_combo.configure(state=state)
        self._grand_prix_combo.configure(state=state)
        self._strategy_combo.configure(state=state)
        self._grand_prix_filter_entry.configure(
            state="normal" if enabled else "disabled"
        )
        self._update_run_button_state()

    def _update_run_button_state(self, *_args) -> None:
        enabled = self._has_valid_selection() and not self._controls_locked
        self._run_button.configure(
            state="normal" if enabled else "disabled",
            cursor="hand2" if enabled else "arrow",
            bg="#d6572b" if enabled else "#cccfda",
        )

    def _has_valid_selection(self) -> bool:
        return bool(
            self._weekends
            and self._season_var.get()
            and self._grand_prix_var.get()
            and self._strategy_var.get()
        )

    def _show_progress(self) -> None:
        self._progress_label.pack(anchor="w", fill="x", pady=(10, 4))
        self._progress_bar.pack(anchor="w", fill="x")
        self._progress_bar.start(12)

    def _hide_progress(self) -> None:
        self._progress_bar.stop()
        self._progress_bar.pack_forget()
        self._progress_label.pack_forget()

    def _apply_view_model(self, view_model: PredictionViewModel) -> None:
        self._headline_label.configure(text=view_model.headline)
        self._status_label.configure(text=view_model.status_text)
        self._context_label.configure(text=view_model.context_text)
        self._strategy_label.configure(text=view_model.strategy_text)
        self._source_badge.configure(
            text=view_model.source_label,
            bg=self._badge_background(view_model.source_tone),
            fg=self._badge_foreground(view_model.source_tone),
        )
        self._confidence_badge.configure(
            text=view_model.confidence_label,
            bg=self._badge_background(view_model.confidence_tone),
            fg=self._badge_foreground(view_model.confidence_tone),
        )
        self._explanation_label.configure(text=view_model.explanation_text)
        self._actual_result_title_label.configure(text=view_model.actual_result_title)
        self._actual_result_note_var.set(view_model.actual_result_note)

        actual_has_data = bool(view_model.actual_result_rows)
        self._actual_result_title_label.configure(
            fg="#ffffff" if actual_has_data else "#9fb0c9"
        )
        self._actual_result_note_label.configure(
            fg="#dce5f5" if actual_has_data else "#a9b9d4"
        )

        if view_model.error_text:
            self._error_var.set(view_model.error_text)
            self._error_banner.grid()
        else:
            self._error_var.set("")
            self._error_banner.grid_remove()

        for item in self._tree.get_children():
            self._tree.delete(item)
        for row in view_model.table_rows:
            self._tree.insert("", "end", values=row)

        for index, widgets in enumerate(self._actual_result_rows):
            place_label, name_label = widgets
            if index < len(view_model.actual_result_rows):
                place, name = view_model.actual_result_rows[index]
                place_label.configure(text=place)
                name_label.configure(text=name)
            else:
                place_label.configure(text="")
                name_label.configure(text="")

    def _set_support_mode(self, text: str) -> None:
        self._support_mode_var.set(text)
        tone = self._support_mode_tone(text)
        self._support_mode_badge.configure(
            bg=self._badge_background(tone),
            fg=self._badge_foreground(tone),
        )

    def _support_mode_tone(self, text: str) -> str:
        normalized = text.lower()
        if "unavailable" in normalized or "no race" in normalized or "required" in normalized:
            return "error"
        if "completed" in normalized:
            return "neutral"
        return "live"

    def _badge_background(self, tone: str) -> str:
        return {
            "live": "#e6f5ee",
            "error": "#fde8e7",
            "neutral": "#edf1f4",
        }.get(tone, "#edf1f4")

    def _badge_foreground(self, tone: str) -> str:
        return {
            "live": "#1c6b49",
            "error": "#9a251c",
            "neutral": "#516071",
        }.get(tone, "#516071")

    def launch_app(self) -> None:
        self.mainloop()


def launch_app(repository: RaceDataRepository) -> None:
    controller = PredictionController(repository)
    app = F1PredictorApp(controller)
    app.launch_app()
