from collections import Counter
from datetime import datetime
import re

from sqlalchemy import func

from app.database.database import SessionLocal
from app.database.models import Article


NORTHEAST_STATES = {
    "Assam": ["assam", "guwahati", "dibrugarh", "nagaon", "lumding"],
    "Arunachal Pradesh": ["arunachal", "itanagar"],
    "Manipur": ["manipur", "imphal", "kangpokpi"],
    "Meghalaya": ["meghalaya", "shillong"],
    "Mizoram": ["mizoram", "aizawl"],
    "Nagaland": ["nagaland", "kohima", "dimapur"],
    "Tripura": ["tripura", "agartala"],
    "Sikkim": ["sikkim", "gangtok"],
}


def get_articles():
    db = SessionLocal()

    try:
        return (
            db.query(Article)
            .filter(
                Article.category.isnot(None),
                Article.category != "Not Relevant",
            )
            .all()
            )
    finally:
        db.close()


def get_overall_statistics():
    articles = get_articles()

    if not articles:
        return {
            "total_articles": 0,
            "average_article_score": 0,
            "average_relevance_score": 0,
            "average_security_score": 0,
            "date_range": None,
        }

    dates = [
        article.published_date
        for article in articles
        if article.published_date
    ]

    return {
        "total_articles": len(articles),

        "average_article_score": round(
            sum(a.article_score or 0 for a in articles) / len(articles),
            2,
        ),

        "average_relevance_score": round(
            sum(a.relevance_score or 0 for a in articles) / len(articles),
            2,
        ),

        "average_security_score": round(
            sum(a.security_score or 0 for a in articles) / len(articles),
            2,
        ),

        "date_range": {
            "start": min(dates).strftime("%Y-%m-%d") if dates else None,
            "end": max(dates).strftime("%Y-%m-%d") if dates else None,
        },
    }


def get_category_statistics():
    articles = get_articles()

    counter = Counter(
        article.category
        for article in articles
        if article.category
    )

    total = sum(counter.values())

    return [
        {
            "category": category,
            "count": count,
            "percentage": round((count / total) * 100, 2) if total else 0,
        }
        for category, count in counter.most_common()
    ]


def get_source_statistics():
    articles = get_articles()

    counter = Counter(
        article.source
        for article in articles
        if article.source
    )

    total = sum(counter.values())

    return [
        {
            "source": source,
            "count": count,
            "percentage": round((count / total) * 100, 2) if total else 0,
        }
        for source, count in counter.most_common()
    ]


def get_date_statistics():
    articles = get_articles()

    counter = Counter(
        article.published_date.strftime("%Y-%m-%d")
        for article in articles
        if article.published_date
    )

    return [
        {
            "date": date,
            "count": count,
        }
        for date, count in sorted(counter.items())
    ]


def get_state_statistics():
    articles = get_articles()

    state_counts = Counter()

    for article in articles:
        text = (
            f"{article.title or ''} "
            f"{article.content or ''}"
        ).lower()

        for state, keywords in NORTHEAST_STATES.items():
            if any(
                re.search(rf"\b{re.escape(keyword)}\b", text)
                for keyword in keywords
            ):
                state_counts[state] += 1

    return [
        {
            "state": state,
            "count": count,
        }
        for state, count in state_counts.most_common()
    ]


def get_top_articles(limit=10):
    articles = get_articles()

    articles.sort(
        key=lambda article: article.article_score or 0,
        reverse=True,
    )

    return [
        {
            "id": article.id,
            "title": article.title,
            "source": article.source,
            "category": article.category,
            "article_score": article.article_score or 0,
            "northeast_score": article.northeast_score or 0,
            "security_score": article.security_score or 0,
            "published_date": (
                article.published_date.strftime("%Y-%m-%d")
                if article.published_date
                else None
            ),
        }
        for article in articles[:limit]
    ]


def generate_analytics():
    """
    Generate the complete analytics dataset used
    by charts and the magazine generator.
    """

    return {
        "overall": get_overall_statistics(),
        "categories": get_category_statistics(),
        "sources": get_source_statistics(),
        "dates": get_date_statistics(),
        "states": get_state_statistics(),
        "top_articles": get_top_articles(),
    }


if __name__ == "__main__":
    import json

    analytics = generate_analytics()

    print(
        json.dumps(
            analytics,
            indent=4,
            ensure_ascii=False,
            default=str,
        )
    )