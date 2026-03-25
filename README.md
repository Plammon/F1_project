# F1 Predictor

F1 Predictor is a Python desktop application for casual Formula 1 fans who want a quick, understandable estimate of pre-race winner odds before a Grand Prix weekend. The project is organized as a layered architecture and is supported by midterm-deliverable artefacts for COMP 3304.

## Team

- Baris AYDIN
- Yusuf KORKMAZ
- Eren OZSAHIN
- Furkan UKUS
- Baran KARLUK

## Product Story

The app helps casual fans compare leading drivers before a race and understand why one driver is favored. A user selects a season, a Grand Prix, and a prediction strategy. The system loads race features, calculates winner probabilities, and presents the predicted winner with a ranked breakdown.

## Architecture

The prototype follows a layered architecture with strict top-down dependencies:

- Presentation layer: Tkinter desktop dashboard
- Application layer: prediction controller and workflow orchestration
- Domain layer: prediction entities and Strategy-based scoring algorithms
- Data layer: resilient repository that prefers live FastF1 access and falls back to local mock data

## Design Pattern

The primary design pattern is Strategy. The user can switch between alternative prediction approaches without changing the controller, UI, or repository code:

- `BalancedStrategy`
- `QualifyingBiasStrategy`
- `ConsistencyBiasStrategy`

## Project Structure

```text
src/f1_predictor/
  application/
  data/
  domain/
  presentation/
data/
tests/
docs/
scripts/
```

## Running the App

### Quickest option on Windows

Double-click `run_app.bat`

### Python setup

1. Install dependencies:

```bash
pip install -r requirements.txt
```

2. Run the desktop prototype:

```bash
python scripts/run_app.py
```

3. Run the test suite:

```bash
python -m unittest discover -s tests -v
```

4. Build the diagrams and midterm artefacts:

```bash
python scripts/build_deliverables.py
```

### Optional editable install

If you want the package available as `python -m f1_predictor`, run:

```bash
pip install -e .
python -m f1_predictor
```

## Building a Windows EXE

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

3. The packaged app will be created at:

```text
dist/F1Predictor/F1Predictor.exe
```

## Deliverables Included

- Midterm report source: `docs/report/midterm_report.md`
- Midterm report PDF: `docs/report/TeamDNF_MidtermReport.pdf`
- Presentation outline: `docs/slides/midterm_presentation_outline.md`
- Presentation deck: `docs/slides/TeamDNF_MidtermPresentation.pptx`
- Mermaid UML and architecture diagrams: `docs/diagrams/`
- Jira-ready backlog and sprint material: `docs/jira_backlog.md`, `docs/jira_sprint.md`

## Notes

- Live FastF1 access is optional. If it is unavailable, the app automatically uses bundled mock data so the demo still works.
- The app now supports both normal Python runs and a PyInstaller-based Windows executable build.
- The repository was initialized locally and linked to the public course GitHub repository as `origin`.
