"""
Northeast Sentinel
==================

Main orchestration entry point for the complete
automated e-magazine generation pipeline.

Pipeline:

1. Database initialization
2. Web scraping / article collection
3. Relevance detection
4. Article classification
5. Article scoring
6. Deduplication
7. Embedding generation
8. ChromaDB vector store
9. RAG / editorial generation
10. Image processing
11. Analytics
12. Magazine HTML generation
13. PDF generation

Run:

    python main.py

The Streamlit UI can separately be started with:

    streamlit run app/ui/app.py
"""

from __future__ import annotations

import subprocess
import sys
import time
from pathlib import Path


# ============================================================
# PROJECT CONFIGURATION
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parent

PYTHON = sys.executable


# ============================================================
# OUTPUT PATHS
# ============================================================

DATA_DIR = PROJECT_ROOT / "data"

OUTPUT_DIR = DATA_DIR / "output"

MAGAZINE_JSON = (
    OUTPUT_DIR / "magazine_data.json"
)

MAGAZINE_HTML = (
    OUTPUT_DIR / "northeast_sentinel_magazine.html"
)

MAGAZINE_PDF = (
    OUTPUT_DIR / "northeast_sentinel_magazine.pdf"
)

CHART_DIR = (
    DATA_DIR / "charts"
)

IMAGE_DIR = (
    DATA_DIR / "images"
)

DATABASE_FILE = (
    DATA_DIR / "northeast_sentinel.db"
)

CHROMA_DIR = (
    PROJECT_ROOT / "chroma_db"
)


# ============================================================
# TERMINAL COLORS
# ============================================================

RESET = "\033[0m"

BOLD = "\033[1m"

RED = "\033[91m"

GREEN = "\033[92m"

YELLOW = "\033[93m"

BLUE = "\033[94m"

CYAN = "\033[96m"


# ============================================================
# PIPELINE STAGES
# ============================================================

PIPELINE = [

    # --------------------------------------------------------
    # PHASE 3
    # DATABASE
    # --------------------------------------------------------

    {
        "phase": "Phase 3",
        "name": "Database Initialization",
        "module": "app.database.init_db",
    },

    # --------------------------------------------------------
    # PHASE 1 / 2
    # SCRAPING
    # --------------------------------------------------------

    {
        "phase": "Phase 1",
        "name": "Article Collection / Web Scraping",
        "module": "app.scraper.collection_pipeline",
    },

    # --------------------------------------------------------
    # PHASE 4
    # NORTHEAST RELEVANCE
    # --------------------------------------------------------

    {
        "phase": "Phase 4",
        "name": "Northeast Relevance Detection",
        "module": "app.nlp.relevance",
    },

    # --------------------------------------------------------
    # PHASE 5
    # CLASSIFICATION
    # --------------------------------------------------------

    {
        "phase": "Phase 5",
        "name": "Article Classification",
        "module": "app.nlp.classifier",
    },

    # --------------------------------------------------------
    # PHASE 6
    # SCORING
    # --------------------------------------------------------

    {
        "phase": "Phase 6",
        "name": "Article Scoring",
        "module": "app.scoring.scoring_pipeline",
    },

    # --------------------------------------------------------
    # PHASE 7
    # DEDUPLICATION
    # --------------------------------------------------------

    {
        "phase": "Phase 7",
        "name": "Article Deduplication",
        "module": "app.preprocessing.deduplicator",
    },

    # --------------------------------------------------------
    # PHASE 8
    # EMBEDDINGS
    # --------------------------------------------------------

    {
        "phase": "Phase 8",
        "name": "Embedding Generation",
        "module": "app.embeddings.embedder",
    },

    # --------------------------------------------------------
    # PHASE 9
    # VECTOR DATABASE
    # --------------------------------------------------------

    {
        "phase": "Phase 9",
        "name": "ChromaDB Vector Store",
        "module": "app.vectorstore.chroma_store",
    },

    # --------------------------------------------------------
    # PHASE 10
    # RAG
    # --------------------------------------------------------

    {
        "phase": "Phase 10",
        "name": "RAG / Editorial Generation",
        "module": "app.rag.generator",
    },

    # --------------------------------------------------------
    # PHASE 11 / 12
    # IMAGES
    # --------------------------------------------------------

    {
        "phase": "Phase 11-12",
        "name": "Image Processing",
        "module": "app.images.pipeline",
    },

    # --------------------------------------------------------
    # PHASE 13
    # ANALYTICS
    # --------------------------------------------------------

    {
        "phase": "Phase 13",
        "name": "Analytics and Chart Generation",
        "module": "app.analytics.run_analytics",
    },

    # --------------------------------------------------------
    # PHASE 14 / 15
    # MAGAZINE
    # --------------------------------------------------------

    {
        "phase": "Phase 14-15",
        "name": "Magazine HTML Generation",
        "module": "app.magazine.render_magazine",
    },

    # --------------------------------------------------------
    # PHASE 16
    # PDF
    # --------------------------------------------------------

    {
        "phase": "Phase 16",
        "name": "PDF Generation",
        "module": "app.magazine.templates.pdf_generator",
    },
]


# ============================================================
# UTILITY FUNCTIONS
# ============================================================

def print_banner():
    """Display application banner."""

    print()

    print(
        "=" * 76
    )

    print(
        f"{BOLD}{CYAN}"
        "NORTHEAST SENTINEL"
        f"{RESET}"
    )

    print(
        "Automated AI-Powered E-Magazine Generation System"
    )

    print(
        "=" * 76
    )

    print()


def print_stage(
    index: int,
    total: int,
    stage: dict,
):
    """Display current pipeline stage."""

    print()

    print(
        "-" * 76
    )

    print(
        f"{BOLD}{BLUE}"
        f"[{index}/{total}] "
        f"{stage['phase']} — "
        f"{stage['name']}"
        f"{RESET}"
    )

    print(
        "-" * 76
    )


def run_module(
    module_name: str,
) -> tuple[bool, float]:
    """
    Execute a Python module using:

        python -m module_name
    """

    command = [
        PYTHON,
        "-m",
        module_name,
    ]

    print(
        f"{CYAN}"
        "Command:"
        f"{RESET} "
        f"{' '.join(command)}"
    )

    start = time.perf_counter()

    try:

        result = subprocess.run(
            command,
            cwd=PROJECT_ROOT,
            check=False,
        )

    except KeyboardInterrupt:

        print()

        print(
            f"{YELLOW}"
            "Pipeline interrupted by user."
            f"{RESET}"
        )

        return False, 0.0

    except Exception as exc:

        print()

        print(
            f"{RED}"
            "Could not start module:"
            f"{RESET}"
        )

        print(exc)

        return False, 0.0

    elapsed = (
        time.perf_counter() - start
    )

    if result.returncode == 0:

        print()

        print(
            f"{GREEN}"
            f"✓ Module completed successfully"
            f" ({elapsed:.2f}s)"
            f"{RESET}"
        )

        return True, elapsed

    print()

    print(
        f"{RED}"
        f"✗ Module failed"
        f" (exit code {result.returncode})"
        f"{RESET}"
    )

    return False, elapsed


def check_path(
    path: Path,
) -> bool:
    """Check whether a file/directory exists."""

    return path.exists()


def print_output_status():

    print()

    print(
        "=" * 76
    )

    print(
        f"{BOLD}"
        "FINAL OUTPUT STATUS"
        f"{RESET}"
    )

    print(
        "=" * 76
    )

    outputs = [

        (
            "SQLite Database",
            DATABASE_FILE,
        ),

        (
            "ChromaDB",
            CHROMA_DIR,
        ),

        (
            "Magazine JSON",
            MAGAZINE_JSON,
        ),

        (
            "Magazine HTML",
            MAGAZINE_HTML,
        ),

        (
            "Magazine PDF",
            MAGAZINE_PDF,
        ),

        (
            "Charts",
            CHART_DIR,
        ),

        (
            "Images",
            IMAGE_DIR,
        ),
    ]

    all_good = True

    for name, path in outputs:

        if check_path(path):

            print(
                f"{GREEN}"
                f"✓ {name}"
                f"{RESET}"
            )

            print(
                f"    {path}"
            )

        else:

            print(
                f"{RED}"
                f"✗ {name} — NOT FOUND"
                f"{RESET}"
            )

            print(
                f"    Expected: {path}"
            )

            all_good = False

    return all_good


def print_summary(
    successful: int,
    failed: int,
    total_time: float,
):

    print()

    print(
        "=" * 76
    )

    print(
        f"{BOLD}"
        "PIPELINE SUMMARY"
        f"{RESET}"
    )

    print(
        "=" * 76
    )

    print(
        f"Successful stages : "
        f"{GREEN}{successful}{RESET}"
    )

    print(
        f"Failed stages    : "
        f"{RED}{failed}{RESET}"
    )

    print(
        f"Total runtime    : "
        f"{total_time:.2f} seconds"
    )

    print()


# ============================================================
# MAIN PIPELINE
# ============================================================

def main() -> int:

    pipeline_start = (
        time.perf_counter()
    )

    print_banner()

    print(
        f"{CYAN}"
        "Project root:"
        f"{RESET}"
    )

    print(
        PROJECT_ROOT
    )

    print()

    print(
        f"{CYAN}"
        "Python interpreter:"
        f"{RESET}"
    )

    print(
        PYTHON
    )

    print()

    print(
        f"{CYAN}"
        "Pipeline stages:"
        f"{RESET} "
        f"{len(PIPELINE)}"
    )

    print()

    successful = 0

    failed = 0

    # --------------------------------------------------------
    # RUN PIPELINE
    # --------------------------------------------------------

    for index, stage in enumerate(
        PIPELINE,
        start=1,
    ):

        print_stage(
            index,
            len(PIPELINE),
            stage,
        )

        success, _ = run_module(
            stage["module"]
        )

        if success:

            successful += 1

        else:

            failed += 1

            print()

            print(
                f"{RED}{BOLD}"
                "PIPELINE STOPPED"
                f"{RESET}"
            )

            print()

            print(
                f"Failed stage:"
            )

            print(
                f"  {stage['phase']} — "
                f"{stage['name']}"
            )

            print()

            print(
                "Fix the error above and "
                "run the pipeline again."
            )

            total_time = (
                time.perf_counter()
                - pipeline_start
            )

            print_summary(
                successful,
                failed,
                total_time,
            )

            return 1

    # --------------------------------------------------------
    # OUTPUT VALIDATION
    # --------------------------------------------------------

    outputs_ok = (
        print_output_status()
    )

    total_time = (
        time.perf_counter()
        - pipeline_start
    )

    print_summary(
        successful,
        failed,
        total_time,
    )

    # --------------------------------------------------------
    # FINAL RESULT
    # --------------------------------------------------------

    if outputs_ok:

        print(
            "=" * 76
        )

        print(
            f"{GREEN}{BOLD}"
            "PIPELINE COMPLETED SUCCESSFULLY"
            f"{RESET}"
        )

        print(
            "=" * 76
        )

        print()

        print(
            "Generated magazine:"
        )

        print(
            f"  HTML: {MAGAZINE_HTML}"
        )

        print(
            f"  PDF : {MAGAZINE_PDF}"
        )

        print()

        return 0

    print(
        "=" * 76
    )

    print(
        f"{YELLOW}{BOLD}"
        "PIPELINE COMPLETED WITH OUTPUT WARNINGS"
        f"{RESET}"
    )

    print(
        "=" * 76
    )

    return 1


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":

    raise SystemExit(
        main()
    )