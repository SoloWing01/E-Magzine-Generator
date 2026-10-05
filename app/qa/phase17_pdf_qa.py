"""
Phase 17 — Automated PDF Quality Assurance

Run from the project root:

    python -m app.qa.phase17_pdf_qa

The script validates the generated magazine PDF against:
    data/output/magazine_data.json
    data/output/northeast_sentinel_magazine.html

Outputs:
    data/qa/phase17/reports/phase17_qa_report.json
    data/qa/phase17/reports/phase17_qa_report.txt
    data/qa/phase17/extracted/page_XXX.txt

This phase does not modify the magazine.
"""

from __future__ import annotations

import hashlib
import json
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Any

from bs4 import BeautifulSoup

try:
    from pypdf import PdfReader
except ImportError:
    PdfReader = None


# ---------------------------------------------------------------------
# PATHS
# ---------------------------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parents[2]

OUTPUT_DIR = PROJECT_ROOT / "data" / "output"

PDF_PATH = OUTPUT_DIR / "northeast_sentinel_magazine.pdf"
HTML_PATH = OUTPUT_DIR / "northeast_sentinel_magazine.html"
MAGAZINE_DATA_PATH = OUTPUT_DIR / "magazine_data.json"

QA_DIR = PROJECT_ROOT / "data" / "qa" / "phase17"
REPORT_DIR = QA_DIR / "reports"
EXTRACTED_DIR = QA_DIR / "extracted"
SCREENSHOT_DIR = QA_DIR / "screenshots"

TARGET_PAGES = 50

# These pages are allowed to be image-heavy / text-light.
ALLOWED_LOW_TEXT_TYPES = {
    "cover-page",
    "inside-cover",
    "section-page",
    "chart-page",
    "back-cover",
}

PLACEHOLDER_PATTERNS = [
    r"\blorem ipsum\b",
    r"\bimage unavailable\b",
    r"\bchart image unavailable\b",
    r"\bplaceholder\b",
    r"\bcoming soon\b",
    r"\bTODO\b",
    r"\bFIXME\b",
]

URL_PATTERN = re.compile(r"https?://[^\s<>\"]+", re.I)


# ---------------------------------------------------------------------
# HELPERS
# ---------------------------------------------------------------------

def normalize_text(text: str) -> str:
    """Normalize extracted text for comparisons."""
    text = text or ""
    text = re.sub(r"\s+", " ", text)
    return text.strip().lower()


def short_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


def safe_int(value: Any) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def flatten_articles(magazine: dict[str, Any]) -> list[dict[str, Any]]:
    """Return unique article records from the magazine JSON."""
    found: dict[int, dict[str, Any]] = {}

    # Primary source in the current magazine_data.json is sections -> articles.
    for section in magazine.get("sections", []):
        for article in section.get("articles", []):
            article_id = safe_int(article.get("article_id", article.get("id")))
            if article_id is not None:
                found[article_id] = article

    # Also inspect a possible top-level articles list.
    for article in magazine.get("articles", []):
        article_id = safe_int(article.get("article_id", article.get("id")))
        if article_id is not None:
            found[article_id] = article

    return list(found.values())


def get_expected_titles(magazine: dict[str, Any]) -> dict[int, str]:
    return {
        safe_int(article.get("article_id", article.get("id"))): article.get("title", "").strip()
        for article in flatten_articles(magazine)
        if safe_int(article.get("article_id", article.get("id"))) is not None
        and article.get("title")
    }


def get_expected_urls(magazine: dict[str, Any]) -> set[str]:
    urls: set[str] = set()

    for article in flatten_articles(magazine):
        if article.get("url"):
            urls.add(str(article["url"]).strip())

        for source in article.get("sources", []):
            if source.get("url"):
                urls.add(str(source["url"]).strip())

        for source in article.get("source_records", []):
            if source.get("url"):
                urls.add(str(source["url"]).strip())

    return urls


def extract_html_pages(html_path: Path) -> list[dict[str, Any]]:
    """Extract the logical magazine pages from generated HTML."""
    soup = BeautifulSoup(html_path.read_text(encoding="utf-8"), "html.parser")
    sections = soup.select("section.magazine-page")

    pages: list[dict[str, Any]] = []

    for index, section in enumerate(sections, start=1):
        classes = set(section.get("class", []))
        page_number = None

        number_node = section.select_one(".page-number")
        if number_node:
            page_number = safe_int(number_node.get_text(" ", strip=True))

        title_node = section.select_one(
            ".article-title, .section-title, .analytics-title, "
            ".editorial-title, .toc-title, .content-title, "
            ".cover-title, .back-cover h1"
        )

        article_id = None
        meta = section.select_one(".article-meta")
        if meta:
            match = re.search(
                r"\bArticle\s+(\d+)\b",
                meta.get_text(" ", strip=True),
                re.I,
            )
            if match:
                article_id = int(match.group(1))

        image_nodes = section.find_all("img")
        links = section.find_all("a", href=True)

        pages.append(
            {
                "index": index,
                "page_number": page_number or index,
                "classes": sorted(classes),
                "type": "chart" if "chart-page" in classes else (
                    "article" if "article-page" in classes else (
                        "section" if "section-page" in classes else "generic"
                    )
                ),
                "title": title_node.get_text(" ", strip=True) if title_node else "",
                "article_id": article_id,
                "is_continuation": bool(section.select_one(".continuation-label")),
                "text": section.get_text(" ", strip=True),
                "images": [
                    {
                        "src": img.get("src", ""),
                        "alt": img.get("alt", ""),
                    }
                    for img in image_nodes
                ],
                "links": [a.get("href", "").strip() for a in links],
            }
        )

    return pages


def resolve_local_asset(project_root: Path, src: str) -> Path | None:
    """Resolve a local HTML asset such as data/images/..."""
    if not src:
        return None

    if re.match(r"^(https?:|data:|file:)", src, re.I):
        return None

    # HTML is generated with paths relative to project root.
    return (project_root / src.lstrip("/")).resolve()


def compare_page_dimensions(width: float, height: float) -> bool:
    """Accept A4 in points with a small tolerance and either orientation."""
    A4_W = 595.2756
    A4_H = 841.8898
    tolerance = 4.0

    return (
        abs(width - A4_W) <= tolerance
        and abs(height - A4_H) <= tolerance
    ) or (
        abs(width - A4_H) <= tolerance
        and abs(height - A4_W) <= tolerance
    )


def report_check(
    checks: list[dict[str, Any]],
    name: str,
    passed: bool,
    message: str,
    severity: str = "error",
) -> None:
    checks.append(
        {
            "name": name,
            "passed": bool(passed),
            "severity": severity,
            "message": message,
        }
    )


# ---------------------------------------------------------------------
# HTML QA
# ---------------------------------------------------------------------

def run_html_qa(
    html_path: Path,
    magazine: dict[str, Any],
    checks: list[dict[str, Any]],
) -> dict[str, Any]:
    if not html_path.exists():
        report_check(
            checks,
            "HTML exists",
            False,
            f"Missing HTML: {html_path}",
        )
        return {}

    pages = extract_html_pages(html_path)
    expected_titles = get_expected_titles(magazine)
    expected_urls = get_expected_urls(magazine)

    report_check(
        checks,
        "HTML logical page count",
        len(pages) == TARGET_PAGES,
        f"Found {len(pages)} logical pages; expected {TARGET_PAGES}.",
    )

    page_numbers = [p["page_number"] for p in pages]
    report_check(
        checks,
        "HTML page numbering",
        page_numbers == list(range(1, len(pages) + 1)),
        "HTML page numbers are sequential.",
    )

    # Article title coverage.
    html_text = normalize_text(
        "\n".join(page["text"] for page in pages)
    )

    missing_titles = [
        (article_id, title)
        for article_id, title in expected_titles.items()
        if normalize_text(title) not in html_text
    ]

    report_check(
        checks,
        "HTML article title coverage",
        not missing_titles,
        (
            f"All {len(expected_titles)} expected article titles found."
            if not missing_titles
            else f"Missing {len(missing_titles)} article title(s): {missing_titles}"
        ),
    )

    # Image asset validation.
    image_refs = []
    missing_images = []

    for page in pages:
        for image in page["images"]:
            src = image["src"]
            image_refs.append(src)

            local_path = resolve_local_asset(PROJECT_ROOT, src)
            if local_path is not None and not local_path.exists():
                missing_images.append(
                    {
                        "page": page["page_number"],
                        "src": src,
                    }
                )

    report_check(
        checks,
        "HTML image assets",
        not missing_images,
        (
            f"Checked {len(image_refs)} image reference(s); all local assets exist."
            if not missing_images
            else f"Missing {len(missing_images)} local image asset(s): {missing_images}"
        ),
    )

    # Chart validation.
    chart_pages = [p for p in pages if p["type"] == "chart"]
    missing_charts = []

    for page in chart_pages:
        for image in page["images"]:
            local_path = resolve_local_asset(PROJECT_ROOT, image["src"])
            if local_path is not None and not local_path.exists():
                missing_charts.append(
                    {
                        "page": page["page_number"],
                        "chart": image["src"],
                    }
                )

    report_check(
        checks,
        "HTML chart assets",
        not missing_charts,
        (
            f"Checked {len(chart_pages)} chart page(s)."
            if not missing_charts
            else f"Missing chart asset(s): {missing_charts}"
        ),
    )

    # Source URLs.
    html_urls = {
        href
        for page in pages
        for href in page["links"]
        if href.startswith(("http://", "https://"))
    }

    missing_expected_urls = sorted(expected_urls - html_urls)

    report_check(
        checks,
        "HTML source URLs",
        not missing_expected_urls,
        (
            f"Found {len(html_urls)} unique HTTP(S) link(s); "
            f"all {len(expected_urls)} expected source URL(s) are present."
            if not missing_expected_urls
            else f"Missing expected source URL(s): {missing_expected_urls}"
        ),
    )

    # Placeholder detection.
    placeholder_hits = []

    for page in pages:
        text = page["text"]
        for pattern in PLACEHOLDER_PATTERNS:
            if re.search(pattern, text, re.I):
                placeholder_hits.append(
                    {
                        "page": page["page_number"],
                        "pattern": pattern,
                    }
                )

    report_check(
        checks,
        "HTML placeholder detection",
        not placeholder_hits,
        (
            "No known placeholder phrases detected."
            if not placeholder_hits
            else f"Placeholder text detected: {placeholder_hits}"
        ),
    )

    # Article page continuity.
    article_page_groups: dict[int, list[dict[str, Any]]] = {}

    for page in pages:
        if page["type"] == "article" and page["article_id"] is not None:
            article_page_groups.setdefault(page["article_id"], []).append(page)

    continuity_problems = []

    for article_id, article_pages in article_page_groups.items():
        if len(article_pages) > 1:
            first = article_pages[0]
            for continuation in article_pages[1:]:
                if not continuation["is_continuation"]:
                    continuity_problems.append(
                        f"Article {article_id}: page {continuation['page_number']} "
                        "is missing continuation marker."
                    )

    report_check(
        checks,
        "Article continuation markers",
        not continuity_problems,
        (
            "Continuation article pages are explicitly marked."
            if not continuity_problems
            else " | ".join(continuity_problems)
        ),
    )

    return {
        "logical_pages": len(pages),
        "page_types": dict(Counter(p["type"] for p in pages)),
        "article_pages": len([p for p in pages if p["type"] == "article"]),
        "chart_pages": len(chart_pages),
        "image_references": len(image_refs),
        "html_urls": sorted(html_urls),
        "expected_urls": sorted(expected_urls),
        "missing_titles": missing_titles,
        "missing_images": missing_images,
        "missing_charts": missing_charts,
        "placeholder_hits": placeholder_hits,
        "pages": pages,
    }


# ---------------------------------------------------------------------
# PDF QA
# ---------------------------------------------------------------------

def run_pdf_qa(
    pdf_path: Path,
    html_info: dict[str, Any],
    magazine: dict[str, Any],
    checks: list[dict[str, Any]],
) -> dict[str, Any]:
    if PdfReader is None:
        report_check(
            checks,
            "pypdf availability",
            False,
            "pypdf is not installed. Install it with: pip install pypdf",
        )
        return {}

    if not pdf_path.exists():
        report_check(
            checks,
            "PDF exists",
            False,
            f"Missing PDF: {pdf_path}",
        )
        return {}

    try:
        reader = PdfReader(str(pdf_path))
        pages = reader.pages
    except Exception as exc:
        report_check(
            checks,
            "PDF readable",
            False,
            f"Could not read PDF: {exc}",
        )
        return {}

    report_check(
        checks,
        "PDF readable",
        True,
        "PDF opened successfully with pypdf.",
    )

    physical_pages = len(pages)

    report_check(
        checks,
        "PDF physical page count",
        physical_pages == TARGET_PAGES,
        f"Found {physical_pages} physical pages; expected {TARGET_PAGES}.",
    )

    # A4 dimensions.
    non_a4 = []

    for index, page in enumerate(pages, start=1):
        try:
            box = page.mediabox
            width = float(box.width)
            height = float(box.height)
            if not compare_page_dimensions(width, height):
                non_a4.append(
                    {
                        "page": index,
                        "width_pt": round(width, 2),
                        "height_pt": round(height, 2),
                    }
                )
        except Exception as exc:
            non_a4.append(
                {
                    "page": index,
                    "error": str(exc),
                }
            )

    report_check(
        checks,
        "PDF A4 dimensions",
        not non_a4,
        (
            "All PDF pages use A4 dimensions."
            if not non_a4
            else f"Non-A4 page(s): {non_a4}"
        ),
    )

    # Extract text and save it page-by-page.
    EXTRACTED_DIR.mkdir(parents=True, exist_ok=True)

    page_texts: list[str] = []

    for index, page in enumerate(pages, start=1):
        try:
            text = page.extract_text() or ""
        except Exception:
            text = ""

        page_texts.append(text)

        output_file = EXTRACTED_DIR / f"page_{index:03d}.txt"
        output_file.write_text(text, encoding="utf-8")

    # Duplicate page detection.
    normalized = [normalize_text(text) for text in page_texts]
    duplicate_pairs = []

    seen: dict[str, int] = {}

    for index, text in enumerate(normalized, start=1):
        if not text:
            continue

        digest = short_hash(text)

        if digest in seen:
            duplicate_pairs.append((seen[digest], index))
        else:
            seen[digest] = index

    report_check(
        checks,
        "Exact duplicate PDF pages",
        not duplicate_pairs,
        (
            "No exact duplicate page text detected."
            if not duplicate_pairs
            else f"Exact duplicate page pair(s): {duplicate_pairs}"
        ),
        severity="warning",
    )

    # Article title detection in PDF.
    expected_titles = get_expected_titles(magazine)
    all_pdf_text = normalize_text("\n".join(page_texts))

    missing_pdf_titles = [
        (article_id, title)
        for article_id, title in expected_titles.items()
        if normalize_text(title) not in all_pdf_text
    ]

    report_check(
        checks,
        "PDF article title coverage",
        not missing_pdf_titles,
        (
            f"All {len(expected_titles)} expected article title(s) found in PDF."
            if not missing_pdf_titles
            else f"Missing PDF article title(s): {missing_pdf_titles}"
        ),
    )

    # Page-level article title mapping.
    title_occurrences = {}

    for article_id, title in expected_titles.items():
        target = normalize_text(title)
        matching_pages = [
            index
            for index, text in enumerate(normalized, start=1)
            if target and target in text
        ]
        title_occurrences[article_id] = matching_pages

    # Low-text pages.
    low_text_pages = []

    for index, text in enumerate(page_texts, start=1):
        word_count = len(re.findall(r"\b[\w’'-]+\b", text))

        page_type = None
        if html_info:
            html_pages = html_info.get("pages", [])
            if index <= len(html_pages):
                page_type = html_pages[index - 1]["type"]

        if word_count < 45 and page_type not in ALLOWED_LOW_TEXT_TYPES:
            low_text_pages.append(
                {
                    "page": index,
                    "word_count": word_count,
                    "html_type": page_type,
                }
            )

    report_check(
        checks,
        "Unexpected low-text pages",
        not low_text_pages,
        (
            "No unexpected low-text pages detected."
            if not low_text_pages
            else f"Low-text page(s): {low_text_pages}"
        ),
        severity="warning",
    )

    # Placeholder detection in PDF text.
    pdf_placeholder_hits = []

    for index, text in enumerate(page_texts, start=1):
        for pattern in PLACEHOLDER_PATTERNS:
            if re.search(pattern, text, re.I):
                pdf_placeholder_hits.append(
                    {
                        "page": index,
                        "pattern": pattern,
                    }
                )

    report_check(
        checks,
        "PDF placeholder detection",
        not pdf_placeholder_hits,
        (
            "No known placeholder phrases detected in PDF text."
            if not pdf_placeholder_hits
            else f"PDF placeholder text detected: {pdf_placeholder_hits}"
        ),
    )

    # PDF link annotations.
    pdf_links = []

    for index, page in enumerate(pages, start=1):
        try:
            annotations = page.get("/Annots", [])
            for annotation_ref in annotations:
                annotation = annotation_ref.get_object()
                action = annotation.get("/A")
                if action and action.get("/URI"):
                    pdf_links.append(
                        {
                            "page": index,
                            "url": str(action.get("/URI")),
                        }
                    )
        except Exception:
            continue

    pdf_link_urls = {item["url"] for item in pdf_links}

    expected_urls = get_expected_urls(magazine)
    missing_pdf_links = sorted(expected_urls - pdf_link_urls)

    # We treat this as a warning because some PDF generators may preserve
    # source text without creating annotations.
    report_check(
        checks,
        "PDF source link annotations",
        not missing_pdf_links,
        (
            f"Found {len(pdf_link_urls)} unique PDF link annotation(s); "
            f"all expected source URL(s) are linked."
            if not missing_pdf_links
            else (
                f"{len(missing_pdf_links)} expected source URL(s) are not "
                "present as PDF link annotations."
            )
        ),
        severity="warning",
    )

    return {
        "physical_pages": physical_pages,
        "page_text_word_counts": {
            index: len(re.findall(r"\b[\w’'-]+\b", text))
            for index, text in enumerate(page_texts, start=1)
        },
        "duplicate_pairs": duplicate_pairs,
        "missing_pdf_titles": missing_pdf_titles,
        "title_occurrences": title_occurrences,
        "low_text_pages": low_text_pages,
        "placeholder_hits": pdf_placeholder_hits,
        "pdf_links": pdf_links,
        "pdf_link_urls": sorted(pdf_link_urls),
        "missing_pdf_links": missing_pdf_links,
    }


# ---------------------------------------------------------------------
# CROSS-CHECK
# ---------------------------------------------------------------------

def run_cross_checks(
    html_info: dict[str, Any],
    pdf_info: dict[str, Any],
    magazine: dict[str, Any],
    checks: list[dict[str, Any]],
) -> None:
    if not html_info or not pdf_info:
        report_check(
            checks,
            "HTML/PDF cross-check",
            False,
            "Cross-check skipped because HTML or PDF QA data is unavailable.",
            severity="warning",
        )
        return

    html_pages = html_info.get("pages", [])
    physical_pages = pdf_info.get("physical_pages", 0)

    if len(html_pages) == physical_pages == TARGET_PAGES:
        report_check(
            checks,
            "HTML/PDF page count agreement",
            True,
            "HTML logical pages and PDF physical pages both equal 50.",
        )
    else:
        report_check(
            checks,
            "HTML/PDF page count agreement",
            False,
            (
                f"HTML={len(html_pages)}, PDF={physical_pages}, "
                f"expected={TARGET_PAGES}."
            ),
        )

    # Compare article page title coverage.
    expected_ids = set(get_expected_titles(magazine))
    html_ids = {
        page["article_id"]
        for page in html_pages
        if page["type"] == "article" and page["article_id"] is not None
    }

    missing_html_ids = sorted(expected_ids - html_ids)

    report_check(
        checks,
        "Article IDs represented in HTML",
        not missing_html_ids,
        (
            "Every expected article ID appears on at least one article page."
            if not missing_html_ids
            else f"Missing article ID(s) in HTML: {missing_html_ids}"
        ),
    )


# ---------------------------------------------------------------------
# REPORTING
# ---------------------------------------------------------------------

def build_summary(checks: list[dict[str, Any]]) -> dict[str, Any]:
    errors = [c for c in checks if not c["passed"] and c["severity"] == "error"]
    warnings = [c for c in checks if not c["passed"] and c["severity"] == "warning"]

    return {
        "result": "PASS" if not errors else "FAIL",
        "passed_checks": sum(1 for c in checks if c["passed"]),
        "failed_errors": len(errors),
        "warnings": len(warnings),
        "total_checks": len(checks),
    }


def write_reports(
    report: dict[str, Any],
) -> tuple[Path, Path]:
    REPORT_DIR.mkdir(parents=True, exist_ok=True)

    json_path = REPORT_DIR / "phase17_qa_report.json"
    txt_path = REPORT_DIR / "phase17_qa_report.txt"

    json_path.write_text(
        json.dumps(report, indent=2, ensure_ascii=False, default=str),
        encoding="utf-8",
    )

    lines = [
        "=" * 72,
        "PHASE 17 — PDF QUALITY ASSURANCE",
        "=" * 72,
        "",
        f"PDF: {report['paths']['pdf']}",
        f"HTML: {report['paths']['html']}",
        f"Magazine data: {report['paths']['magazine_data']}",
        "",
        f"RESULT: {report['summary']['result']}",
        f"Passed checks: {report['summary']['passed_checks']}",
        f"Failed errors: {report['summary']['failed_errors']}",
        f"Warnings: {report['summary']['warnings']}",
        "",
        "CHECKS",
        "-" * 72,
    ]

    for check in report["checks"]:
        status = "PASS" if check["passed"] else (
            "WARN" if check["severity"] == "warning" else "FAIL"
        )
        lines.append(f"[{status}] {check['name']}: {check['message']}")

    lines.extend(
        [
            "",
            "OUTPUTS",
            "-" * 72,
            f"Extracted page text: {EXTRACTED_DIR}",
            f"JSON report: {REPORT_DIR / 'phase17_qa_report.json'}",
            f"Text report: {REPORT_DIR / 'phase17_qa_report.txt'}",
            "",
            "=" * 72,
        ]
    )

    txt_path.write_text("\n".join(lines), encoding="utf-8")

    return json_path, txt_path


# ---------------------------------------------------------------------
# MAIN
# ---------------------------------------------------------------------

def main() -> int:
    print("=" * 72)
    print("PHASE 17 — PDF QUALITY ASSURANCE")
    print("=" * 72)
    print()

    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    EXTRACTED_DIR.mkdir(parents=True, exist_ok=True)
    SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)

    checks: list[dict[str, Any]] = []

    # Load magazine JSON.
    magazine: dict[str, Any] = {}

    if MAGAZINE_DATA_PATH.exists():
        try:
            magazine = json.loads(
                MAGAZINE_DATA_PATH.read_text(encoding="utf-8")
            )
            report_check(
                checks,
                "Magazine JSON readable",
                True,
                "magazine_data.json loaded successfully.",
            )
        except Exception as exc:
            report_check(
                checks,
                "Magazine JSON readable",
                False,
                f"Could not parse magazine_data.json: {exc}",
            )
    else:
        report_check(
            checks,
            "Magazine JSON exists",
            False,
            f"Missing: {MAGAZINE_DATA_PATH}",
        )

    # Metadata expectations.
    metadata = magazine.get("metadata", {})
    expected_articles = safe_int(metadata.get("article_count"))
    expected_source_count = safe_int(metadata.get("source_count"))
    expected_pages = safe_int(metadata.get("target_pages"))

    if expected_articles is not None:
        actual_articles = len(flatten_articles(magazine))
        report_check(
            checks,
            "Magazine article count",
            actual_articles == expected_articles,
            f"JSON declares {expected_articles} article(s); found {actual_articles}.",
        )

    if expected_source_count is not None:
        source_names = {
            article.get("source")
            for article in flatten_articles(magazine)
            if article.get("source")
        }
        report_check(
            checks,
            "Magazine source count",
            len(source_names) == expected_source_count,
            (
                f"JSON declares {expected_source_count} source(s); "
                f"found {len(source_names)} unique source name(s)."
            ),
            severity="warning",
        )

    if expected_pages is not None:
        report_check(
            checks,
            "Magazine target page count",
            expected_pages == TARGET_PAGES,
            f"JSON declares target_pages={expected_pages}; expected {TARGET_PAGES}.",
        )

    html_info = run_html_qa(
        HTML_PATH,
        magazine,
        checks,
    )

    pdf_info = run_pdf_qa(
        PDF_PATH,
        html_info,
        magazine,
        checks,
    )

    run_cross_checks(
        html_info,
        pdf_info,
        magazine,
        checks,
    )

    summary = build_summary(checks)

    report = {
        "phase": 17,
        "name": "Automated PDF Quality Assurance",
        "paths": {
            "project_root": str(PROJECT_ROOT),
            "pdf": str(PDF_PATH),
            "html": str(HTML_PATH),
            "magazine_data": str(MAGAZINE_DATA_PATH),
            "qa_dir": str(QA_DIR),
            "reports_dir": str(REPORT_DIR),
            "extracted_dir": str(EXTRACTED_DIR),
            "screenshots_dir": str(SCREENSHOT_DIR),
        },
        "metadata": metadata,
        "summary": summary,
        "checks": checks,
        "html": html_info,
        "pdf": pdf_info,
    }

    json_report, text_report = write_reports(report)

    print()
    print("PHASE 17 SUMMARY")
    print("-" * 72)

    for check in checks:
        status = "✓" if check["passed"] else (
            "⚠" if check["severity"] == "warning" else "✗"
        )
        print(f"{status} {check['name']}: {check['message']}")

    print()
    print("=" * 72)
    print(f"PHASE 17 RESULT: {summary['result']}")
    print("=" * 72)
    print(f"JSON report : {json_report}")
    print(f"Text report : {text_report}")
    print(f"Extracted   : {EXTRACTED_DIR}")

    return 0 if summary["result"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())