from config import DEFAULT_STOCKS
from src.utils import running_in_streamlit, run_pipeline
from src.dashboard import get_streamlit_inputs, render_dashboard


def main():
    if running_in_streamlit():
        stocks, start, end, max_weight, num_portfolios = get_streamlit_inputs()
    else:
        stocks, start, end, max_weight, num_portfolios = DEFAULT_STOCKS, "2020-01-01", "2025-01-01", 0.30, 5000

    data, returns, cleaned_weights, frontier, basket_return, nifty_return, ret, vol, sharpe = run_pipeline(
        stocks=stocks, start=start, end=end, max_weight=max_weight, num_portfolios=num_portfolios,
    )

    if running_in_streamlit():
        render_dashboard(
            data=data, returns=returns, cleaned_weights=cleaned_weights, frontier=frontier,
            basket_return=basket_return, nifty_return=nifty_return,
            ret=ret, vol=vol, sharpe=sharpe, max_weight=max_weight, num_portfolios=num_portfolios,
        )


if __name__ == "__main__":
    main()
