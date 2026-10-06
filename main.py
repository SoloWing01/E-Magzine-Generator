"""
Northeast Sentinel AI
=====================

End-to-end pipeline controller.

Pipeline:

Phase 0
    Configuration

Phase 1
    Scrapling web collection

Phase 2
    Cleaning / validation / date filtering

Phase 3
    SQLite database

Phase 4
    Northeast relevance

Phase 5
    NLP classification

Phase 6
    Article scoring

Phase 7
    Deduplication

Phase 8
    Sentence Transformer embeddings

Phase 9
    Chroma vector store

Phase 10
    RAG + Mistral + grounding

Phase 11–12
    Image search / download / CLIP relevance

Phase 13
    Analytics / charts

Phase 14–15
    Editorial generation / magazine composition

Phase 16
    PDF generation

Phase 17
    PDF quality assurance
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from datetime import datetime


# ======================================================================
# PROJECT ROOT
# ======================================================================

PROJECT_ROOT = Path(
    __file__
).resolve().parent

PYTHON = sys.executable


# ======================================================================
# HEADER
# ======================================================================

def print_header(title: str) -> None:

    print()
    print("=" * 70)
    print(title)
    print("=" * 70)


# ======================================================================
# RUN STAGE
# ======================================================================

def run_stage(
    stage_name: str,
    module_name: str,
) -> None:

    print_header(
        stage_name
    )

    print(
        f"Module: {module_name}"
    )

    print(
        f"Python: {PYTHON}"
    )

    print(
        f"Working directory: "
        f"{PROJECT_ROOT}"
    )

    start_time = datetime.now()

    result = subprocess.run(
        [
            PYTHON,
            "-m",
            module_name,
        ],
        cwd=PROJECT_ROOT,
        check=False,
    )

    elapsed = (
        datetime.now()
        - start_time
    ).total_seconds()

    print()

    print(
        f"{stage_name} finished "
        f"in {elapsed:.2f} seconds."
    )

    if result.returncode != 0:

        print()
        print(
            "=" * 70
        )

        print(
            f"{stage_name} FAILED"
        )

        print(
            f"Exit code: "
            f"{result.returncode}"
        )

        print(
            "=" * 70
        )

        raise RuntimeError(
            f"{stage_name} failed "
            f"with exit code "
            f"{result.returncode}."
        )

    print(
        f"{stage_name} PASSED"
    )


# ======================================================================
# MAIN PIPELINE
# ======================================================================

def main():

    print_header(
        "NORTHEAST SENTINEL AI"
    )

    print(
        "End-to-end automated "
        "magazine generation pipeline"
    )

    print(
        f"Project root: "
        f"{PROJECT_ROOT}"
    )

    print(
        f"Python executable: "
        f"{PYTHON}"
    )

    pipeline_start = datetime.now()

    try:

        # ==============================================================
        # PHASE 3 — DATABASE
        # ==============================================================

        run_stage(
            "PHASE 3 — DATABASE INITIALIZATION",
            "app.database.init_db",
        )

        # ==============================================================
        # PHASE 1 — SCRAPING
        # ==============================================================

        run_stage(
            "PHASE 1 — WEB SCRAPING",
            "app.scraper.collection_pipeline",
        )

        # ==============================================================
        # PHASE 4 — NORTHEAST RELEVANCE
        # ==============================================================

        run_stage(
            "PHASE 4 — NORTHEAST RELEVANCE",
            "app.nlp.relevance",
        )

        # ==============================================================
        # PHASE 5 — CLASSIFICATION
        # ==============================================================

        run_stage(
            "PHASE 5 — ARTICLE CLASSIFICATION",
            "app.nlp.classifier",
        )

        # ==============================================================
        # PHASE 6 — SCORING
        # ==============================================================

        run_stage(
            "PHASE 6 — ARTICLE SCORING",
            "app.scoring.scoring_pipeline",
        )

        # ==============================================================
        # PHASE 7 — DEDUPLICATION
        # ==============================================================

        run_stage(
            "PHASE 7 — DEDUPLICATION",
            "app.preprocessing.deduplicator",
        )

        # ==============================================================
        # PHASE 8 — EMBEDDINGS
        # ==============================================================

        run_stage(
            "PHASE 8 — ARTICLE EMBEDDINGS",
            "app.embeddings.embedder",
        )

        # ==============================================================
        # PHASE 9 — CHROMA
        # ==============================================================

        run_stage(
            "PHASE 9 — CHROMA VECTOR INDEXING",
            "app.vectorstore.chroma_store",
        )

        # ==============================================================
        # PHASE 10 — RAG
        # ==============================================================

        run_stage(
            "PHASE 10 — RAG + GROUNDING",
            "app.rag.generator",
        )

        # ==============================================================
        # PHASE 11–12 — IMAGES
        # ==============================================================

        run_stage(
            "PHASE 11–12 — IMAGE SEARCH + RELEVANCE",
            "app.images.pipeline",
        )

        # ==============================================================
        # PHASE 13 — ANALYTICS
        # ==============================================================

        run_stage(
            "PHASE 13 — ANALYTICS + CHARTS",
            "app.analytics.run_analytics",
        )

        # ==============================================================
        # PHASE 14–15 — EDITORIAL + MAGAZINE
        # ==============================================================

        run_stage(
            "PHASE 14–15 — EDITORIAL + MAGAZINE",
            "app.magazine.render_magazine",
        )

        # ==============================================================
        # PHASE 16 — PDF
        # ==============================================================

        run_stage(
            "PHASE 16 — PDF GENERATION",
            "app.magazine.templates.pdf_generator",
        )

        # ==============================================================
        # PHASE 17 — PDF QA
        # ==============================================================

        run_stage(
            "PHASE 17 — PDF QUALITY ASSURANCE",
            "app.qa.phase17_pdf_qa",
        )

        # ==============================================================
        # PIPELINE COMPLETE
        # ==============================================================

        elapsed = (
            datetime.now()
            - pipeline_start
        ).total_seconds()

        print_header(
            "NORTHEAST SENTINEL AI — PIPELINE COMPLETE"
        )

        print(
            "All enabled phases completed successfully."
        )

        print(
            f"Total execution time: "
            f"{elapsed:.2f} seconds"
        )

        print()
        print(
            "Final output:"
        )

        print(
            "  data/output/"
        )

        print(
            "    editorial_content.json"
        )

        print(
            "    magazine_data.json"
        )

        print(
            "    northeast_sentinel_magazine.html"
        )

        print(
            "    northeast_sentinel_magazine.pdf"
        )

        print()
        print(
            "Phase 17 PDF QA: PASSED"
        )

    except KeyboardInterrupt:

        print()
        print(
            "=" * 70
        )

        print(
            "PIPELINE INTERRUPTED"
        )

        print(
            "=" * 70
        )

        sys.exit(130)

    except Exception as exc:

        print()
        print(
            "=" * 70
        )

        print(
            "NORTHEAST SENTINEL AI — PIPELINE FAILED"
        )

        print(
            "=" * 70
        )

        print(
            f"Error type: "
            f"{type(exc).__name__}"
        )

        print(
            f"Error: {exc}"
        )

        print(
            "=" * 70
        )

        sys.exit(1)


# ======================================================================
# ENTRY POINT
# ======================================================================

if __name__ == "__main__":

    main()