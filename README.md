# AirBind — Money Muling Detection Engine

AI-assisted financial crime detection system for identifying money muling, fraud rings, and transaction layering patterns.

---

## Overview

AirBind is a financial crime detection system designed to identify money muling and related fraud patterns from transaction data. It analyzes transaction networks using graph algorithms and AI-assisted forensic analysis to detect fraud rings, smurfing behavior, and shell account chains. The system produces risk-scored results with interactive visualizations and exportable investigation reports.

---

## Features

- **CSV-based transaction ingestion** — Simple upload workflow for transaction datasets
- **Graph-based fraud detection** — Detects cycles, smurfing patterns, and shell account chains using NetworkX
- **Risk scoring** — Each account receives a cumulative score (0–100) based on detected patterns
- **Interactive network visualization** — D3.js-powered transaction graph explorer
- **AI-assisted forensic analysis** — LLaMA 3.3-powered summaries and per-account explanations via Groq API
- **Exportable reports** — JSON and PDF investigation report generation

---

## Detection Capabilities

| Pattern | Description |
|---|---|
| **Circular Fund Routing** | Identifies cyclical money flows indicating layering activity |
| **Smurfing (Structuring)** | Detects fan-in and fan-out transaction patterns below reporting thresholds |
| **Shell Chains** | Identifies multi-hop fund movement through low-activity accounts |

Each account receives a cumulative risk score from **0–100** based on detected patterns and fraud ring participation.

---

## Technology Stack

| Layer | Technologies |
|---|---|
| **Backend** | Flask, SQLAlchemy |
| **Database** | SQLite (dev), PostgreSQL-ready |
| **Frontend** | Bootstrap 5, Jinja2, D3.js |
| **Graph Analysis** | NetworkX |
| **Data Processing** | Pandas |
| **Reporting** | ReportLab, Matplotlib |
| **AI Integration** | Groq API (LLaMA 3.3) |

---

## Project Structure

```
.
├── run.py
├── requirements.txt
├── app/
│   ├── models/        # ORM models
│   ├── services/      # Detection, AI, and reporting logic
│   ├── api/           # Flask routes
│   └── templates/     # Jinja2 UI templates
├── instance/          # SQLite database
└── uploads/           # Temporary CSV storage
```

---

## Quick Start

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Start the application
python run.py
```

Access the application at **http://localhost:5000** and upload a CSV file to begin analysis.

---

## AI-Assisted Analysis

AirBind enhances investigations with AI-generated insights powered by the Groq API (LLaMA 3.3):

- **Executive summaries** of detected risks across the transaction network
- **Per-account forensic explanations** for flagged entities
- **Interactive query-based analysis** using cached results to minimize API usage

> AI explanations are generated only for top-risk accounts to control API costs.

---

## Limitations

- SQLite is intended for **development and testing only** — use PostgreSQL for production
- Large datasets (**>10K transactions**) may require longer processing time
- **Concurrent CSV processing is not supported** — a task queue is recommended for production deployments

---

## License

Developed for the **RIFT 2026 Hackathon** — Graph Theory / Financial Crime Detection Track.
