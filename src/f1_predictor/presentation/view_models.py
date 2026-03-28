"""Presentation helpers for formatted UI state."""

from __future__ import annotations

from dataclasses import dataclass

from f1_predictor.domain.models import PredictionResult


@dataclass(frozen=True)
class PredictionViewModel:
    headline: str
    status_text: str
    context_text: str
    explanation_text: str
    source_label: str
    source_tone: str
    confidence_label: str
    confidence_tone: str
    strategy_text: str
    table_rows: list[tuple[str, str, str]]
    actual_result_title: str
    actual_result_rows: list[tuple[str, str]]
    actual_result_note: str
    error_text: str = ""


def build_empty_state() -> PredictionViewModel:
    return PredictionViewModel(
        headline="Select a Grand Prix to generate pre-race winner odds.",
        status_text="Ready when you are. Choose a season, live race weekend, and strategy.",
        context_text="Live data will use the selected qualifying session when it is available.",
        explanation_text=(
            "The app compares qualifying pace, recent form, track fit, pit stops, "
            "and reliability to build an explainable forecast."
        ),
        source_label="Live schedule loaded",
        source_tone="neutral",
        confidence_label="Confidence will appear here",
        confidence_tone="neutral",
        strategy_text="Strategy will appear here after the first run.",
        table_rows=[],
        actual_result_title="Actual race result",
        actual_result_rows=[],
        actual_result_note="When an official race result exists, the podium will appear here.",
    )


def build_loading_state(strategy_name: str) -> PredictionViewModel:
    return PredictionViewModel(
        headline="Running your race-weekend forecast...",
        status_text="Fetching the best available data and scoring the grid.",
        context_text="Loading live qualifying data and checking whether official race results already exist.",
        explanation_text=(
            "We are loading live FastF1 qualifying information for the selected weekend."
        ),
        source_label="Preparing data",
        source_tone="neutral",
        confidence_label="Calculating confidence",
        confidence_tone="neutral",
        strategy_text=f"Strategy selected: {strategy_name}",
        table_rows=[],
        actual_result_title="Actual race result",
        actual_result_rows=[],
        actual_result_note="Checking whether an official race result is already available.",
    )


def build_error_state(message: str) -> PredictionViewModel:
    return PredictionViewModel(
        headline="We could not complete that prediction.",
        status_text="Try another Grand Prix or rerun when more live data is available.",
        context_text="Your selections are still in place, so you can retry without starting over.",
        explanation_text=(
            "The app stayed responsive and preserved your selections so you can try another weekend quickly."
        ),
        source_label="Prediction unavailable",
        source_tone="error",
        confidence_label="No forecast confidence",
        confidence_tone="error",
        strategy_text="No result was generated.",
        table_rows=[],
        actual_result_title="Actual race result",
        actual_result_rows=[],
        actual_result_note="No official comparison is shown when the forecast cannot be generated.",
        error_text=message,
    )


def build_result_state(result: PredictionResult) -> PredictionViewModel:
    source_tone = "live" if "FastF1" in result.data_source else "neutral"
    table_rows = [
        (str(index), driver, f"{probability:.1f}%")
        for index, (driver, probability) in enumerate(
            result.driver_probabilities.items(),
            start=1,
        )
    ]
    actual_result_rows, actual_result_note = _build_actual_result_rows(result)
    actual_status = (
        "Official race result available for comparison."
        if result.actual_podium
        else "Official race result is not available yet for this weekend."
    )
    return PredictionViewModel(
        headline=f"{result.predicted_winner} leads this forecast.",
        status_text=(
            f"Generated at {result.generated_at.strftime('%d %b %Y, %H:%M %Z')} "
            "using the best available data."
        ),
        context_text=(
            f"Session used: {result.session_label}. {actual_status} {result.confidence_reason}"
        ),
        explanation_text=" ".join(result.top_features_or_factors),
        source_label=result.data_source,
        source_tone=source_tone,
        confidence_label=f"{result.confidence_label} confidence",
        confidence_tone=_confidence_tone(result.confidence_label),
        strategy_text=f"Strategy used: {result.strategy_name}",
        table_rows=table_rows,
        actual_result_title="Actual race result",
        actual_result_rows=actual_result_rows,
        actual_result_note=actual_result_note,
    )


def _build_actual_result_rows(
    result: PredictionResult,
) -> tuple[list[tuple[str, str]], str]:
    if not result.actual_podium:
        return (
            [],
            "No official podium is available yet for this Grand Prix, so there is nothing to compare.",
        )

    rows = [
        ("P1", result.actual_podium[0]),
        ("P2", result.actual_podium[1]),
        ("P3", result.actual_podium[2]),
    ]
    comparison = result.historical_comparison
    if comparison is None:
        predicted_top_three = tuple(list(result.driver_probabilities.keys())[:3])
        podium_overlap = len(set(predicted_top_three) & set(result.actual_podium))
        winner_match = result.predicted_winner == result.actual_podium[0]
    else:
        podium_overlap = comparison.podium_overlap
        winner_match = comparison.winner_match
    if winner_match:
        note = (
            "Strong validation: the predicted winner matched the actual P1, "
            f"and {podium_overlap}/3 predicted podium drivers finished on the podium."
        )
    elif comparison or podium_overlap:
        note = (
            f"The forecast missed P1, but {podium_overlap}/3 predicted podium drivers "
            "still reached the actual podium."
        )
    else:
        note = (
            f"The forecast favored {result.predicted_winner}, but the actual winner was "
            f"{result.actual_podium[0]}."
        )
    return rows, note


def _confidence_tone(confidence_label: str) -> str:
    normalized = confidence_label.lower()
    if "high" in normalized:
        return "live"
    if "low" in normalized:
        return "error"
    return "neutral"
