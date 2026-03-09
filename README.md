# 🏎️ F1 Race Prediction App

A desktop application that predicts Formula 1 race outcomes using AI and real telemetry data from the FastF1 API.

> **COMP 3304 — Lab 4**

---

## Architecture

The app follows a **Layered Architecture** with strict top-down dependencies:

```
┌─────────────────────────────┐
│    Desktop UI & Dashboard   │  ← Presentation Layer
└──────────────┬──────────────┘
               │ User Actions
┌──────────────▼──────────────┐
│    Main App Controller      │  ← Application Layer
└──────────────┬──────────────┘
               │ Triggers Prediction
┌──────────────▼──────────────┐
│  Prediction Engine & AI     │  ← Domain Layer
│  └─ Feature Engineering     │
└──────────────┬──────────────┘
               │ Requests Data
┌──────────────▼──────────────┐
│  Data Repository & Cache    │  ← Data Layer
│  └─ FastF1 Client           │
└──────────────┬──────────────┘
               │ Downloads
┌──────────────▼──────────────┐
│  F1 Live Timing APIs        │  ← External Services
└─────────────────────────────┘
```

Each layer only depends on the layer directly below it, ensuring changes in one tier don't ripple through the rest of the system.

---

## Key Quality Attributes

| Attribute | Problem | Solution |
|---|---|---|
| **Performance** | FastF1 telemetry files are massive and slow to process | Heavy data fetching and AI inference run asynchronously in lower layers, keeping the UI responsive |
| **Maintainability** | F1 rules, tracks, and models change frequently | Strict layer boundaries allow swapping AI models (e.g., Scikit-learn → XGBoost) without touching the UI |
| **Testability** | Predictions must be validated without manual UI interaction | Decoupled layers enable headless automated testing of the AI model against historical data |