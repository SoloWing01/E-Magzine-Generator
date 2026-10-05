from app.database.database import SessionLocal
from app.database.models import Article
from app.nlp.relevance import classifier


db = SessionLocal()

articles = db.query(Article).order_by(Article.id).all()

for article in articles:

    result = classifier.classify(
        title=article.title,
        content=article.content,
    )

    print("\n" + "=" * 80)
    print(f"ID: {article.id}")
    print(f"TITLE: {article.title}")
    print(f"RELEVANT: {result.relevant}")
    print(f"SCORE: {result.relevance_score}")
    print(f"CATEGORY: {result.category}")
    print(f"NE SCORE: {result.northeast_score}")
    print(f"SECURITY: {result.security_score}")
    print(f"DEVELOPMENT: {result.development_score}")
    print(f"SOCIETY: {result.society_score}")
    print(f"SPORTS: {result.sports_score}")
    print(
        "NE TERMS:",
        ", ".join(result.matched_northeast_terms)
    )
    print(
        "THEME TERMS:",
        ", ".join(result.matched_theme_terms)
    )
    print(f"REASON: {result.reason}")


db.close()