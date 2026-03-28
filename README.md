# F1 Predictor

F1 Predictor is a Windows-first Python desktop application for casual Formula 1 fans who want a quick, explainable estimate of pre-race winner odds before a Grand Prix weekend. The final product uses live FastF1 schedule and qualifying data, compares multiple prediction strategies, and shows how the forecast compares to official race results when they exist.

## Team

- Baris AYDIN
- Yusuf KORKMAZ
- Eren OZSAHIN
- Furkan UKUS
- Baran KARLUK

## What The App Does

- Loads Grand Prix weekends from the live FastF1 schedule
- Lets you choose a season, race weekend, and prediction strategy
- Generates ranked winner probabilities for the field
- Explains the top factors behind the forecast in plain English
- Shows a confidence label for the current forecast
- Compares the prediction with the official podium when race results are available
- Tracks simple validation metrics across the completed races you check in the app

## Architecture

The app keeps the layered architecture from the course project:

- Presentation layer: Tkinter desktop dashboard
- Application layer: prediction controller and workflow orchestration
- Domain layer: prediction entities and Strategy-based scoring algorithms
- Data layer: FastF1-backed live race data repository

## Design Pattern

The main design pattern is Strategy. The user can switch between alternative prediction approaches without changing the controller, UI, or repository code:

- `BalancedStrategy`
- `QualifyingBiasStrategy`
- `ConsistencyBiasStrategy`

## Project Structure

```text
assets/
scripts/
src/f1_predictor/
  application/
  data/
  domain/
  presentation/
tests/
```

## Install And Run

### Windows quick start

Double-click `run_app.bat`

### Python setup

1. Install dependencies:

```bash
pip install -r requirements.txt
```

2. Run the desktop app:

```bash
python scripts/run_app.py
```

3. Run the tests:

```bash
python -m unittest discover -s tests -v
```

### Optional editable install

```bash
pip install -e .
python -m f1_predictor
```

## Build The Windows EXE

1. Install dependencies:

```bash
pip install -r requirements.txt
```

2. Build the executable:

```bash
python scripts/build_windows_exe.py
```

Or double-click:

```text
build_exe.bat
```

3. The packaged release will be created at:

```text
dist/F1Predictor/F1Predictor.exe
```

The EXE build now includes:

- app version metadata
- a custom application icon
- a clean release folder
- a runtime README next to the executable

## Live Data Availability

The product now uses live FastF1 data as its only end-user data source.

That means:

- the visible race list comes from the live FastF1 schedule
- forecasts use live qualifying session data
- official podium comparisons appear only when race results exist
- if FastF1 cannot provide enough data, the app shows a clear message instead of falling back silently

Typical live-data message:

`We do not have enough live qualifying data for this race weekend right now. Please try another Grand Prix or try again later.`

## Prediction Notes

The forecast is still a heuristics-based MVP, but it is more credible than the earlier prototype because it now:

- uses all available qualifying results instead of only a tiny subset
- factors in recent completed race performance
- rewards reliability and positions gained over recent races
- blends current pace with track-history context when available
- adjusts confidence when data coverage is weaker

## Logging And Cache

- Runtime logs are written to `logs/f1_predictor.log`
- FastF1 cache data is stored in `cache/fastf1`

These folders are created automatically when you run the app.

## Known Limitations

- Some race weekends may not have enough live qualifying data yet
- Future races do not have official podiums to compare against
- Prediction quality still depends on the completeness of the live data FastF1 can provide
- The Windows build is not code-signed, so SmartScreen warnings may still appear on other machines
