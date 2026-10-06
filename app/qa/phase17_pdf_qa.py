"""
Northeast Sentinel AI
Phase 17 — PDF Quality Assurance

Usage:
    python -m app.qa.phase17_pdf_qa

Validates:
    1. Required files exist
    2. magazine_data.json is valid
    3. Phase 15 logical page plan contains 50 pages
    4. PDF exists and has a valid PDF header
    5. PDF can be opened with pypdf
    6. Physical PDF page count is exactly 50
    7. PDF pages contain readable text
    8. Important magazine content is present
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

from pypdf import PdfReader

from app.config.settings import settings


# ======================================================================
# PATHS
# ======================================================================

PROJECT_ROOT = Path(__file__).resolve().parents[2]

OUTPUT_DIR = Path(settings.OUTPUT_DIR)

if not OUTPUT_DIR.is_absolute():
    OUTPUT_DIR = PROJECT_ROOT / OUTPUT_DIR

PDF_PATH = (
    OUTPUT_DIR
    / "northeast_sentinel_magazine.pdf"
)

MAGAZINE_DATA_PATH = (
    OUTPUT_DIR
    / "magazine_data.json"
)

HTML_PATH = (
    OUTPUT_DIR
    / "northeast_sentinel_magazine.html"
)

EXPECTED_PAGES = 50


# ======================================================================
# HELPERS
# ======================================================================

def header(title: str) -> None:
    print()
    print("=" * 70)
    print(title)
    print("=" * 70)


# ======================================================================
# QA CLASS
# ======================================================================

class PDFQualityAssurance:

    def __init__(
        self,
        pdf_path: Path = PDF_PATH,
        magazine_data_path: Path = MAGAZINE_DATA_PATH,
        html_path: Path = HTML_PATH,
        expected_pages: int = EXPECTED_PAGES,
    ):

        self.pdf_path = Path(pdf_path)

        self.magazine_data_path = Path(
            magazine_data_path
        )

        self.html_path = Path(
            html_path
        )

        self.expected_pages = int(
            expected_pages
        )

        self.reader: PdfReader | None = None

        self.logical_pages = 0

        self.physical_pages = 0

        self.page_plan: list[Any] = []

        self.page_records: list[dict[str, Any]] = []

        self.errors: list[str] = []

        self.warnings: list[str] = []

    # ==================================================================
    # FILE VALIDATION
    # ==================================================================

    def validate_files(self) -> None:

        header(
            "PHASE 17 — PDF QUALITY ASSURANCE"
        )

        print(
            "Checking required files..."
        )

        print(
            f"PDF      : {self.pdf_path}"
        )

        print(
            f"Magazine : {self.magazine_data_path}"
        )

        print(
            f"HTML     : {self.html_path}"
        )

        if not self.pdf_path.exists():

            raise FileNotFoundError(
                f"PDF does not exist:\n"
                f"{self.pdf_path}"
            )

        if not self.magazine_data_path.exists():

            raise FileNotFoundError(
                "magazine_data.json does not exist:\n"
                f"{self.magazine_data_path}"
            )

        if not self.html_path.exists():

            self.warnings.append(
                "Magazine HTML file does not exist."
            )

        print(
            "Required file check: PASSED"
        )

    # ==================================================================
    # MAGAZINE DATA
    # ==================================================================

    def load_magazine_data(self) -> None:

        header(
            "MAGAZINE DATA VALIDATION"
        )

        with self.magazine_data_path.open(
            "r",
            encoding="utf-8",
        ) as file:

            data = json.load(file)

        if not isinstance(
            data,
            dict,
        ):

            raise ValueError(
                "magazine_data.json must contain "
                "a JSON object."
            )

        print(
            "Top-level keys:"
        )

        print(
            list(data.keys())
        )

        # --------------------------------------------------------------
        # Phase 15 stores the logical page structure in page_plan.
        # --------------------------------------------------------------

        if "page_plan" not in data:

            raise ValueError(
                "Could not find 'page_plan' "
                "in magazine_data.json."
            )

        self.page_plan = data[
            "page_plan"
        ]

        if not isinstance(
            self.page_plan,
            list,
        ):

            raise ValueError(
                "'page_plan' must be a list."
            )

        self.logical_pages = len(
            self.page_plan
        )

        print(
            f"Logical pages from page_plan: "
            f"{self.logical_pages}"
        )

        if self.logical_pages != self.expected_pages:

            raise ValueError(
                "\n"
                "LOGICAL PAGE COUNT MISMATCH\n"
                f"Expected : {self.expected_pages}\n"
                f"Actual   : {self.logical_pages}\n"
            )

        print(
            "Logical page count: PASSED"
        )

        # --------------------------------------------------------------
        # Check Phase 15 validation metadata if available.
        # --------------------------------------------------------------

        validation = data.get(
            "validation",
            {}
        )

        if isinstance(
            validation,
            dict,
        ):

            print()
            print(
                "Phase 15 validation metadata:"
            )

            for key, value in validation.items():

                print(
                    f"  {key}: {value}"
                )

    # ==================================================================
    # PDF HEADER
    # ==================================================================

    def validate_pdf_header(self) -> None:

        header(
            "PDF FILE VALIDATION"
        )

        with self.pdf_path.open(
            "rb"
        ) as file:

            pdf_header = file.read(
                5
            )

        print(
            f"PDF header: {pdf_header!r}"
        )

        if pdf_header != b"%PDF-":

            raise ValueError(
                "Invalid PDF header."
            )

        print(
            "PDF header: PASSED"
        )

    # ==================================================================
    # LOAD PDF
    # ==================================================================

    def load_pdf(self) -> None:

        header(
            "PDF READER VALIDATION"
        )

        self.reader = PdfReader(
            str(self.pdf_path)
        )

        self.physical_pages = len(
            self.reader.pages
        )

        print(
            f"Physical PDF pages: "
            f"{self.physical_pages}"
        )

        print(
            "PDF reader validation: PASSED"
        )

    # ==================================================================
    # PAGE COUNT
    # ==================================================================

    def validate_page_count(self) -> None:

        header(
            "PHYSICAL PAGE COUNT VALIDATION"
        )

        print(
            f"Expected pages : "
            f"{self.expected_pages}"
        )

        print(
            f"Logical pages  : "
            f"{self.logical_pages}"
        )

        print(
            f"Physical pages : "
            f"{self.physical_pages}"
        )

        difference = (
            self.physical_pages
            - self.expected_pages
        )

        print(
            f"Difference     : "
            f"{difference:+d}"
        )

        if self.physical_pages != self.expected_pages:

            raise ValueError(
                "\n"
                "PDF PAGE COUNT MISMATCH\n"
                f"Expected : {self.expected_pages}\n"
                f"Actual   : {self.physical_pages}\n"
                f"Difference: {difference:+d}\n"
            )

        print(
            "Physical PDF page count: PASSED"
        )

    # ==================================================================
    # PAGE TEXT INSPECTION
    # ==================================================================

    def inspect_pages(self) -> None:

        header(
            "PDF PAGE CONTENT INSPECTION"
        )

        if self.reader is None:

            raise RuntimeError(
                "PDF reader has not been initialized."
            )

        self.page_records = []

        empty_pages = []

        for number, page in enumerate(
            self.reader.pages,
            start=1,
        ):

            try:

                text = (
                    page.extract_text()
                    or ""
                )

                normalized = " ".join(
                    text.split()
                )

                character_count = len(
                    normalized
                )

                record = {
                    "page": number,
                    "characters": character_count,
                    "text": normalized,
                }

                self.page_records.append(
                    record
                )

                if character_count < 10:

                    empty_pages.append(
                        number
                    )

            except Exception as exc:

                self.errors.append(
                    f"Page {number}: "
                    f"text extraction failed: "
                    f"{exc}"
                )

        print(
            f"Pages inspected: "
            f"{len(self.page_records)}"
        )

        if empty_pages:

            self.warnings.append(
                "Pages with very little "
                "extractable text: "
                f"{empty_pages}"
            )

            print(
                "Warning: pages with very little "
                "extractable text:"
            )

            print(
                empty_pages
            )

        else:

            print(
                "Text extraction check: PASSED"
            )

    # ==================================================================
    # CONTENT SANITY
    # ==================================================================

    def validate_content_sanity(self) -> None:

        header(
            "CONTENT SANITY CHECK"
        )

        if not self.page_records:

            raise ValueError(
                "No PDF page records available."
            )

        full_text = "\n".join(
            record["text"]
            for record in self.page_records
        )

        checks = {
            "Securing the Northeast": (
                "Securing the Northeast"
                in full_text
            ),

            "Indian Army": (
                "Indian Army"
                in full_text
            ),

            "The Assam Tribune": (
                "The Assam Tribune"
                in full_text
            ),

            "End of Edition": (
                "End of Edition"
                in full_text
            ),
        }

        failed = []

        for name, passed in checks.items():

            status = (
                "PASSED"
                if passed
                else "FAILED"
            )

            print(
                f"{name:<25}: {status}"
            )

            if not passed:

                failed.append(
                    name
                )

        if failed:

            self.warnings.append(
                "Content markers not found: "
                + ", ".join(failed)
            )

        else:

            print(
                "Content sanity: PASSED"
            )

    # ==================================================================
    # PAGE MAPPING
    # ==================================================================

    def print_page_mapping(self) -> None:

        header(
            "PDF PAGE MAPPING"
        )

        for record in self.page_records:

            preview = record[
                "text"
            ][:160]

            print(
                f"{record['page']:03d} | "
                f"{preview}"
            )

    # ==================================================================
    # FILE INFORMATION
    # ==================================================================

    def print_file_info(self) -> None:

        header(
            "PDF FILE INFORMATION"
        )

        size_bytes = (
            self.pdf_path.stat().st_size
        )

        size_mb = (
            size_bytes
            / (1024 * 1024)
        )

        print(
            f"PDF size: "
            f"{size_mb:.2f} MB"
        )

        if size_bytes <= 0:

            raise ValueError(
                "PDF file is empty."
            )

        print(
            "PDF file size: PASSED"
        )

    # ==================================================================
    # FINAL SUMMARY
    # ==================================================================

    def summary(self) -> None:

        header(
            "PHASE 17 — QA SUMMARY"
        )

        print(
            f"Logical HTML pages : "
            f"{self.logical_pages}"
        )

        print(
            f"Physical PDF pages : "
            f"{self.physical_pages}"
        )

        print(
            f"Expected pages     : "
            f"{self.expected_pages}"
        )

        print(
            f"PDF file           : "
            f"{self.pdf_path}"
        )

        print(
            f"Errors             : "
            f"{len(self.errors)}"
        )

        print(
            f"Warnings           : "
            f"{len(self.warnings)}"
        )

        if self.warnings:

            print()
            print(
                "WARNINGS:"
            )

            for warning in self.warnings:

                print(
                    f" - {warning}"
                )

        if self.errors:

            print()
            print(
                "ERRORS:"
            )

            for error in self.errors:

                print(
                    f" - {error}"
                )

    # ==================================================================
    # RUN
    # ==================================================================

    def run(self) -> bool:

        try:

            self.validate_files()

            self.load_magazine_data()

            self.validate_pdf_header()

            self.load_pdf()

            self.validate_page_count()

            self.inspect_pages()

            self.validate_content_sanity()

            self.print_file_info()

            self.summary()

            if self.errors:

                print()
                print(
                    "=" * 70
                )

                print(
                    "PHASE 17 FAILED"
                )

                print(
                    "=" * 70
                )

                return False

            print()
            print(
                "=" * 70
            )

            print(
                "PHASE 17 — PDF QA PASSED"
            )

            print(
                "=" * 70
            )

            return True

        except Exception as exc:

            self.summary()

            print()
            print(
                "=" * 70
            )

            print(
                "PHASE 17 FAILED"
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

            return False


# ======================================================================
# MAIN
# ======================================================================

def main() -> int:

    qa = PDFQualityAssurance()

    passed = qa.run()

    if passed:

        print()
        print(
            "PHASE 17 COMPLETE"
        )

        return 0

    print()
    print(
        "PHASE 17 FAILED"
    )

    return 1


if __name__ == "__main__":

    sys.exit(
        main()
    )