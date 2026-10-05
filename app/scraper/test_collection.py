from app.scraper.collection_pipeline import (
    CollectionPipeline,
)


def main():

    pipeline = CollectionPipeline()

    pipeline.collect(
        "https://assamtribune.com/"
    )


if __name__ == "__main__":
    main()