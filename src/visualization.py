import matplotlib.pyplot as plt
import seaborn as sns

from config import PLOTS_DIR


def create_frontier_figure(portfolios, opt_ret: float, opt_vol: float):
    """Build a Monte Carlo efficient frontier figure."""
    fig, ax = plt.subplots(figsize=(10, 6))
    scatter = ax.scatter(
        portfolios["volatility"], portfolios["return"],
        c=portfolios["sharpe"], cmap="viridis", s=8, alpha=0.55,
    )
    ax.scatter([opt_vol], [opt_ret], marker="*", s=280, color="red", label="Optimized Portfolio")
    fig.colorbar(scatter, ax=ax, label="Sharpe Ratio")
    ax.set_title("Efficient Frontier (Monte Carlo)")
    ax.set_xlabel("Annual Volatility")
    ax.set_ylabel("Annual Return")
    ax.legend(loc="best")
    fig.subplots_adjust(top=0.90, right=0.88)
    return fig


def create_correlation_figure(returns):
    """Build a correlation heatmap figure."""
    corr = returns.corr()
    n = len(corr)
    fig_size = max(8, n * 0.55)
    fig, ax = plt.subplots(figsize=(fig_size, fig_size * 0.75))
    sns.heatmap(
        corr, annot=(n <= 15), cmap="coolwarm", fmt=".2f",
        square=True, ax=ax, linewidths=0.3 if n <= 20 else 0,
    )
    ax.set_title("Correlation Heatmap")
    ax.tick_params(axis="x", rotation=45)
    fig.tight_layout()
    return fig


def create_dashboard_overview_figure(returns, portfolios, cleaned_weights, ret, vol, sharpe, nifty_return):
    """Build a static overview figure for README screenshots."""
    fig = plt.figure(figsize=(14, 9))
    grid = fig.add_gridspec(2, 2, height_ratios=[1, 3], hspace=0.28, wspace=0.22)

    metrics_ax = fig.add_subplot(grid[0, :])
    metrics_ax.axis("off")
    metrics_text = (
        f"Expected Return: {ret * 100:.2f}%    "
        f"Volatility: {vol * 100:.2f}%    "
        f"Sharpe Ratio: {sharpe:.2f}    "
        f"Nifty Return: {nifty_return * 100:.2f}%"
    )
    metrics_ax.text(0.01, 0.65, "Nifty Portfolio Optimizer Dashboard Overview",
                    fontsize=16, fontweight="bold", va="center")
    metrics_ax.text(0.01, 0.25, metrics_text, fontsize=12, va="center")

    frontier_ax = fig.add_subplot(grid[1, 0])
    scatter = frontier_ax.scatter(
        portfolios["volatility"], portfolios["return"],
        c=portfolios["sharpe"], cmap="viridis", s=7, alpha=0.5,
    )
    frontier_ax.scatter([vol], [ret], marker="*", s=220, color="red")
    frontier_ax.set_title("Efficient Frontier")
    frontier_ax.set_xlabel("Annual Volatility")
    frontier_ax.set_ylabel("Annual Return")
    fig.colorbar(scatter, ax=frontier_ax, label="Sharpe Ratio")

    pie_ax = fig.add_subplot(grid[1, 1])
    non_zero_weights = {k: v for k, v in cleaned_weights.items() if v > 0}
    labels = list(non_zero_weights.keys())
    values = list(non_zero_weights.values())
    wedges, _ = pie_ax.pie(
        values, labels=None, startangle=90,
        explode=[0.03] * len(values),
        wedgeprops={"width": 0.45, "edgecolor": "white", "linewidth": 1.5},
    )
    legend_labels = [f"{ticker}: {weight:.1%}" for ticker, weight in zip(labels, values)]
    pie_ax.legend(wedges, legend_labels, title="Allocation", loc="center left", bbox_to_anchor=(1.0, 0.5))
    pie_ax.set_title("Portfolio Allocation")
    pie_ax.axis("equal")

    fig.subplots_adjust(top=0.90, right=0.88, hspace=0.30, wspace=0.25)
    return fig


def plot_allocation_pie(weights):
    """Create a donut-style allocation chart."""
    non_zero_weights = {k: v for k, v in weights.items() if v > 0}
    labels = list(non_zero_weights.keys())
    values = list(non_zero_weights.values())

    fig, ax = plt.subplots(figsize=(8, 6))
    wedges, _ = ax.pie(
        values, labels=None, startangle=90,
        explode=[0.03] * len(values),
        wedgeprops={"width": 0.45, "edgecolor": "white", "linewidth": 1.5},
    )
    legend_labels = [f"{ticker}: {weight:.1%}" for ticker, weight in zip(labels, values)]
    ax.legend(wedges, legend_labels, title="Allocation", loc="center left", bbox_to_anchor=(1.0, 0.5))
    ax.set_title("Portfolio Allocation")
    ax.axis("equal")
    fig.tight_layout()
    return fig


def save_plot(fig, file_name: str):
    """Persist a matplotlib figure in the plots directory."""
    PLOTS_DIR.mkdir(parents=True, exist_ok=True)
    fig.savefig(PLOTS_DIR / file_name, dpi=200)
    plt.close(fig)
