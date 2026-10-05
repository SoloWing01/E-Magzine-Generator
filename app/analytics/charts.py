from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns

from app.analytics.statistics import generate_analytics
from app.config.settings import settings


CHART_DIR = Path(settings.CHART_DIR)
CHART_DIR.mkdir(parents=True, exist_ok=True)


def save_chart(fig, filename):
    path = CHART_DIR / filename

    fig.tight_layout()
    fig.savefig(
        path,
        dpi=200,
        bbox_inches="tight",
    )
    plt.close(fig)

    return str(path)


def category_chart(analytics):
    data = analytics["categories"]

    if not data:
        return None

    df = pd.DataFrame(data)

    fig, ax = plt.subplots(figsize=(10, 6))

    sns.barplot(
        data=df,
        x="category",
        y="count",
        hue="category",
        palette="Set2",
        legend=False,
        ax=ax,
    )

    ax.set_title(
        "Article Distribution by Category",
        fontsize=16,
        fontweight="bold",
    )

    ax.set_xlabel("Category")
    ax.set_ylabel("Number of Articles")

    ax.tick_params(axis="x", rotation=20)

    for container in ax.containers:
        ax.bar_label(
            container,
            fontsize=10,
            padding=3,
        )

    return save_chart(
        fig,
        "articles_by_category.png",
    )


def source_chart(analytics):
    data = analytics["sources"]

    if not data:
        return None

    df = pd.DataFrame(data)

    fig, ax = plt.subplots(figsize=(10, 6))

    sns.barplot(
        data=df,
        y="source",
        x="count",
        hue="source",
        palette="viridis",
        legend=False,
        ax=ax,
    )

    ax.set_title(
        "Article Contribution by Source",
        fontsize=16,
        fontweight="bold",
    )

    ax.set_xlabel("Number of Articles")
    ax.set_ylabel("Source")

    for container in ax.containers:
        ax.bar_label(
            container,
            fontsize=10,
            padding=3,
        )

    return save_chart(
        fig,
        "articles_by_source.png",
    )


def date_chart(analytics):
    data = analytics["dates"]

    if not data:
        return None

    df = pd.DataFrame(data)
    df["date"] = pd.to_datetime(df["date"])

    fig, ax = plt.subplots(figsize=(11, 6))

    sns.lineplot(
        data=df,
        x="date",
        y="count",
        marker="o",
        linewidth=2.5,
        ax=ax,
    )

    ax.set_title(
        "Article Publication Timeline",
        fontsize=16,
        fontweight="bold",
    )

    ax.set_xlabel("Publication Date")
    ax.set_ylabel("Number of Articles")

    for x, y in zip(df["date"], df["count"]):
        ax.annotate(
            str(y),
            (x, y),
            xytext=(0, 8),
            textcoords="offset points",
            ha="center",
            fontsize=9,
        )

    fig.autofmt_xdate()

    return save_chart(
        fig,
        "articles_over_time.png",
    )


def state_chart(analytics):
    data = analytics["states"]

    if not data:
        return None

    df = pd.DataFrame(data)

    fig, ax = plt.subplots(figsize=(10, 6))

    sns.barplot(
        data=df,
        y="state",
        x="count",
        hue="state",
        palette="Spectral",
        legend=False,
        ax=ax,
    )

    ax.set_title(
        "Northeast State Coverage",
        fontsize=16,
        fontweight="bold",
    )

    ax.set_xlabel("Number of Articles")
    ax.set_ylabel("State")

    for container in ax.containers:
        ax.bar_label(
            container,
            fontsize=10,
            padding=3,
        )

    return save_chart(
        fig,
        "northeast_state_coverage.png",
    )

def generate_all_charts():
    analytics = generate_analytics()

    charts = {
        "category": category_chart(analytics),
        "source": source_chart(analytics),
        "date": date_chart(analytics),
        "state": state_chart(analytics),
    }

    return charts


if __name__ == "__main__":
    charts = generate_all_charts()

    print("\nGenerated charts:")

    for name, path in charts.items():
        print(f"{name}: {path}")