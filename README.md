# Bill Calculator

[![Open in molab](https://marimo.io/molab-shield.svg)](https://molab.marimo.io/github/EllieKallmier/bill_calculator/blob/main/bill_calculator_notebook.py)

An interactive [marimo](https://marimo.io) notebook for calculating and comparing residential electricity bills under different tariff structures.

## Features

- **Load Profile Analysis** — Use sample profiles or upload your own CSV files with consumption and PV generation data
- **Custom Data Upload** — Upload multiple CSV files with automatic datetime parsing, validation, and format detection
- **Tariff Comparison** — Select from a preset list of tariffs (flat rate, time-of-use, demand charges) or define custom tariffs
- **Solar PV Modelling** — Compare bills with and without solar to quantify savings
- **Battery Storage Simulation** — Add a battery using a simple self-consumption maximisation algorithm
- **Interactive Visualisations** — Explore load profiles and bill breakdowns with zoomable Altair charts
- **Export Results** — Download bill calculations and load data as CSV for further analysis

## Uploading Your Own Data

You can upload your own load profile data as CSV files. Required format:

| Column        | Description                           | Required |
| ------------- | ------------------------------------- | -------- |
| `TS`          | Timestamp (various formats supported) | Yes      |
| `Wh` or `kWh` | Electricity consumption per interval  | Yes      |
| `PV`          | Solar PV generation (same units)      | No       |
| `CUSTOMER_ID` | Site identifier                       | No       |

**Supported timestamp formats:**
- `2020-01-01 00:00:00` (ISO, recommended)
- `01/01/2020 00:00` (day/month/year)
- `2020-01-01T00:00:00` (ISO with T)
- `01-Jan-2020 00:00:00` (month names)

The notebook automatically detects the format, converts units, and validates your data.

## Getting Started

Click the **Open in molab** badge above to run the notebook directly in your browser — no installation required.

To run locally:

```bash
# Install marimo
pip install marimo

# Run the notebook
marimo edit bill_calculator_notebook.py
```

## Possible Extensions

These are ideas for extending the notebook, suitable for students working with an AI coding assistant:

- **Add more battery dispatch strategies** — Implement time-of-use aware charging (charge during off-peak, discharge during peak) instead of simple self-consumption
- **Wholesale price optimisation** — Fetch historical spot prices and optimise battery dispatch to maximise arbitrage value
- **Electric vehicle modelling** — Add an EV charging profile with configurable charging windows and smart charging logic
- **Demand response simulation** — Model load shifting (e.g., moving pool pump or hot water to solar hours) and quantify bill impacts
- **Multi-year analysis** — Extend to handle multiple years of data and model tariff escalation or degradation of solar/battery
- **Emissions calculations** — Add grid emissions intensity data to calculate avoided emissions from solar and battery
- **Sensitivity analysis** — Create parameter sweeps (e.g., varying battery size or PV capacity) and visualise the results
- **Export to PDF report** — Generate a formatted summary report with key metrics and charts
