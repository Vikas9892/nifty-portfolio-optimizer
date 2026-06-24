# Nifty Portfolio Optimizer

Nifty Portfolio Optimizer is a resume-focused portfolio analysis project built with Python, PyPortfolioOpt, and Streamlit. It downloads historical prices for a small basket of Indian large-cap stocks, computes daily returns, optimizes the portfolio for maximum Sharpe ratio, runs a Monte Carlo simulation, and compares the resulting basket against the Nifty 50 benchmark.

The project is intentionally practical: it shows a complete end-to-end workflow from raw market data to portfolio construction, visual diagnostics, and an interactive dashboard.

## Highlights

- Downloads historical price data with `yfinance`.
- Computes daily returns and annualized expected returns.
- Builds a covariance matrix and optimizes the portfolio with `PyPortfolioOpt`.
- Generates a Monte Carlo efficient frontier with 10,000 random portfolios.
- Saves a correlation heatmap and frontier plot for portfolio analysis.
- Compares the optimized basket against the Nifty 50 benchmark.
- Renders the results in a Streamlit-ready dashboard.

## Assets

Running the app creates reusable outputs in the repository:

- `data/nifty_close_prices.csv` for downloaded close prices.
- `plots/efficient_frontier.png` for the Monte Carlo frontier scatter plot.
- `plots/correlation_heatmap.png` for the correlation matrix visualization.

## Tech Stack

- Python
- PyPortfolioOpt
- Pandas
- NumPy
- Matplotlib
- Seaborn
- yfinance
- Streamlit

## Project Structure

```text
nifty-portfolio-optimizer/
├── app.py
├── requirements.txt
├── data/
├── plots/
└── README.md
```

## Setup

### 1. Clone the repository

```bash
git clone https://github.com/Vikas9892/nifty-portfolio-optimizer.git
cd nifty-portfolio-optimizer
```

### 2. Create a virtual environment

```bash
python -m venv .venv
```

Activate it:

```bash
.venv\Scripts\activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

## How to Run

### Command-line mode

Run the script directly to download data, compute returns, optimize the portfolio, and save the plots:

```bash
python app.py
```

### Streamlit dashboard

Launch the interactive dashboard with:

```bash
streamlit run app.py
```

## Data Used

The project uses a small basket of Indian large-cap stocks:

- RELIANCE.NS
- TCS.NS
- INFY.NS
- HDFCBANK.NS
- ICICIBANK.NS

The benchmark is the Nifty 50 index via `^NSEI`.

## What the App Does

1. Downloads daily close prices from 2020-01-01 to 2025-01-01.
2. Converts close prices to daily returns.
3. Computes historical mean returns and sample covariance.
4. Optimizes portfolio weights for maximum Sharpe ratio.
5. Simulates 10,000 random portfolios to approximate the frontier.
6. Saves frontier and correlation visualizations to the `plots/` folder.
7. Compares the optimized portfolio return with the Nifty benchmark.

## Output Preview

The dashboard shows:

- Selected stocks
- Optimal weights
- Sharpe ratio and benchmark comparison
- Efficient frontier chart
- Correlation heatmap
- Portfolio allocation pie chart
- Daily returns snapshot

### Dashboard Overview

![Dashboard Overview](plots/dashboard_overview.png)

### Efficient Frontier

![Efficient Frontier](plots/efficient_frontier.png)

### Correlation Heatmap

![Correlation Heatmap](plots/correlation_heatmap.png)

### Portfolio Allocation

![Portfolio Allocation](plots/portfolio_allocation.png)

## Features

- Sharpe Ratio Optimization
- Monte Carlo Portfolio Simulation
- Efficient Frontier Visualization
- Correlation Analysis
- Nifty 50 Benchmarking
- Portfolio Weight Constraints

## Notes

- The app is designed as a compact but resume-worthy portfolio project rather than a production trading system.
- Yahoo Finance data availability can change; if the download fails, rerun the script later.
- The Monte Carlo frontier uses random sampling, so the scatter plot can vary slightly between runs.

## License

This project inherits the repository license.
