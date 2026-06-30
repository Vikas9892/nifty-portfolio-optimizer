import pandas as pd

from .visualization import create_correlation_figure, create_frontier_figure, plot_allocation_pie


def render_dashboard(
    data, returns, cleaned_weights, frontier,
    basket_return, nifty_return, ret, vol, sharpe,
    max_weight, num_portfolios,
):
    """Render the Streamlit dashboard."""
    import streamlit as st

    st.set_page_config(page_title="Nifty Portfolio Optimizer", layout="wide")
    st.title("Nifty Portfolio Optimizer")
    st.caption("Mean-variance optimization over the Nifty 50 universe with Ledoit-Wolf covariance shrinkage.")

    col1, col2, col3, col4, col5 = st.columns(5)
    col1.metric("Expected Return", f"{ret * 100:.2f}%")
    col2.metric("Volatility", f"{vol * 100:.2f}%")
    col3.metric("Sharpe Ratio", f"{sharpe:.2f}")
    col4.metric("Nifty 50 Return", f"{nifty_return * 100:.2f}%")
    col5.metric("vs Benchmark", f"{(basket_return - nifty_return) * 100:+.2f}%")

    st.subheader("Portfolio Summary")
    st.markdown(
        f"""
Stocks in basket: **{len(data.columns)}**
Stocks with non-zero weight: **{sum(1 for v in cleaned_weights.values() if v > 0)}**
Simulation count: **{num_portfolios:,}**
Max weight cap: **{max_weight * 100:.0f}%**
Covariance model: **Ledoit-Wolf Shrinkage**
Optimization method: **Maximum Sharpe Ratio**
"""
    )
    st.caption(f"Realized annualized basket return: {basket_return:.2%}")

    left, right = st.columns([1.2, 1])
    with left:
        st.subheader("Optimal Weights")
        weights_frame = pd.DataFrame(list(cleaned_weights.items()), columns=["Ticker", "Weight"])
        weights_frame = weights_frame[weights_frame["Weight"] > 0].sort_values("Weight", ascending=False)
        weights_frame["Weight"] = weights_frame["Weight"].map(lambda x: f"{x:.2%}")
        st.dataframe(weights_frame, use_container_width=True)
    with right:
        st.subheader("Portfolio Allocation")
        st.pyplot(plot_allocation_pie(cleaned_weights), clear_figure=True)

    st.subheader("Correlation Heatmap")
    st.pyplot(create_correlation_figure(returns), clear_figure=True)

    st.subheader("Efficient Frontier")
    st.pyplot(create_frontier_figure(frontier, ret, vol), clear_figure=True)

    st.subheader("Daily Returns Snapshot")
    st.dataframe(returns.head(15), use_container_width=True)


def get_streamlit_inputs():
    """Collect interactive dashboard controls."""
    import streamlit as st
    from config import NIFTY_50, NIFTY_50_STOCKS, DEFAULT_STOCKS

    st.sidebar.header("Controls")

    st.sidebar.subheader("Stock Universe")
    selected_stocks = []
    with st.sidebar.expander("Pick stocks by sector", expanded=False):
        for sector, tickers in NIFTY_50.items():
            defaults_in_sector = [t for t in tickers if t in DEFAULT_STOCKS]
            chosen = st.multiselect(sector, tickers, default=defaults_in_sector, key=f"sector_{sector}")
            selected_stocks.extend(chosen)

    st.sidebar.subheader("Or pick from full list")
    flat_selected = st.sidebar.multiselect(
        "All Nifty 50 stocks",
        NIFTY_50_STOCKS,
        default=[],
        help="Selections here are added on top of sector picks above.",
    )
    selected_stocks = list(dict.fromkeys(selected_stocks + flat_selected))

    if not selected_stocks:
        selected_stocks = DEFAULT_STOCKS

    st.sidebar.markdown("---")
    start_date = st.sidebar.date_input("Start date", value=pd.Timestamp("2020-01-01"))
    end_date = st.sidebar.date_input("End date", value=pd.Timestamp("2025-01-01"))
    max_weight = st.sidebar.slider("Max weight per stock", min_value=0.10, max_value=0.50, value=0.30, step=0.01)
    num_portfolios = st.sidebar.slider("Monte Carlo portfolios", min_value=1000, max_value=10000, value=5000, step=500)

    if len(selected_stocks) < 2:
        st.error("Please select at least 2 stocks.")
        st.stop()

    if start_date >= end_date:
        st.error("Start date must be earlier than end date.")
        st.stop()

    return selected_stocks, str(start_date), str(end_date), max_weight, num_portfolios
