import json

from app.analytics.statistics import generate_analytics
from app.analytics.charts import generate_all_charts


def main():
    print("=" * 60)
    print("NORTHEAST SENTINEL AI - ANALYTICS")
    print("=" * 60)

    analytics = generate_analytics()

    print("\nOVERALL")
    print("-" * 40)

    print(
        json.dumps(
            analytics["overall"],
            indent=4,
            default=str,
        )
    )

    print("\nCATEGORIES")
    print("-" * 40)

    for item in analytics["categories"]:
        print(
            f"{item['category']}: "
            f"{item['count']} "
            f"({item['percentage']}%)"
        )

    print("\nSOURCES")
    print("-" * 40)

    for item in analytics["sources"]:
        print(
            f"{item['source']}: "
            f"{item['count']} "
            f"({item['percentage']}%)"
        )

    print("\nNORTHEAST STATES")
    print("-" * 40)

    for item in analytics["states"]:
        print(
            f"{item['state']}: "
            f"{item['count']}"
        )

    print("\nTOP ARTICLES")
    print("-" * 40)

    for article in analytics["top_articles"]:
        print(
            f"{article['article_score']:>3} | "
            f"{article['title']}"
        )

    print("\nGenerating charts...")

    charts = generate_all_charts()

    for name, path in charts.items():
        print(f"{name}: {path}")

    print("\nAnalytics completed.")


if __name__ == "__main__":
    main()