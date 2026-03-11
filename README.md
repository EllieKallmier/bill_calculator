# Bill Calculator

[![Open in molab](https://marimo.io/molab-shield.svg)](https://molab.marimo.io/github/EllieKallmier/bill_calculator/blob/main/bill_calculator_notebook.py)

An interactive [marimo](https://marimo.io) notebook for calculating and comparing residential electricity bills under different tariff structures. Designed for energy economics education and exploration.

## Features

- **Load Profile Analysis** — Load sample half-hourly consumption and rooftop PV generation data for a full year
- **Tariff Comparison** — Select from real Australian network tariffs (flat rate, time-of-use, demand charges) or define custom tariffs
- **Solar PV Modelling** — Compare bills with and without solar to quantify savings
- **Battery Storage Simulation** — Add a battery using a simple self-consumption maximisation algorithm
- **Interactive Visualisations** — Explore load profiles and bill breakdowns with zoomable Altair charts
- **Export Results** — Download bill calculations and load data as CSV for further analysis

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
