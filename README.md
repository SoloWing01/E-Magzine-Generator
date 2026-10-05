# Northeast Sentinel AI

## Securing the Northeast: Indian Army's Role in Stability, Peace & National Security

An automated AI-powered editorial pipeline that discovers Northeast
India news, validates and filters the reporting, evaluates relevance,
classifies and ranks articles, performs semantic retrieval with
embeddings and Chroma, generates grounded editorial content with
Mistral, prepares images and analytics, and finally produces a
professionally formatted 50-page e-magazine in HTML and PDF.

------------------------------------------------------------------------

## Overview

**Northeast Sentinel AI** is an end-to-end AI/ML publication-generation
system.

The project is designed to automate the journey from:

> **Web news → structured data → NLP/ML selection → RAG → grounded
> editorial writing → images → analytics → magazine composition → HTML →
> PDF → QA**

Instead of manually searching for articles and manually designing every
page, the system builds a reproducible editorial workflow.

The current magazine edition is:

-   **Title:** Securing the Northeast
-   **Subtitle:** Indian Army's Role in Stability, Peace & National
    Security
-   **Coverage:** Northeast India
-   **Configured assignment window:** 5 September 2026 -- 5 October 2026
-   **Target output:** 50-page e-magazine
-   **Current selected corpus:** 11 articles
-   **Current sections:** 5
-   **Current charts:** 4

------------------------------------------------------------------------

# Key Features

-   Automated web article discovery
-   Scrapling-based web extraction
-   Article cleaning and metadata validation
-   Publication-date filtering
-   Northeast India relevance detection
-   NLP-based classification
-   Named Entity Recognition
-   Multi-factor article scoring
-   Exact and semantic deduplication
-   Sentence Transformer embeddings
-   Local Chroma vector database
-   Retrieval-Augmented Generation (RAG)
-   Mistral-powered editorial generation
-   Evidence-grounded content generation
-   Claim-level grounding/validation
-   Automatic image discovery and selection
-   Image relevance checking
-   Image deduplication
-   Article and source analytics
-   Automatic chart generation
-   Content-driven page planning
-   50-page deterministic magazine composition
-   Jinja2 HTML rendering
-   CSS-based magazine styling
-   WeasyPrint HTML-to-PDF conversion
-   Automated PDF/page validation
-   Local asset packaging for deterministic rendering

------------------------------------------------------------------------

# System Architecture

``` text
                         ┌──────────────────────┐
                         │   Assignment Config  │
                         │   settings.py        │
                         └──────────┬───────────┘
                                    │
                                    ▼
                         ┌──────────────────────┐
                         │   Scrapling / Web    │
                         │   Article Discovery  │
                         └──────────┬───────────┘
                                    │
                                    ▼
                         ┌──────────────────────┐
                         │ Cleaning & Validation│
                         │ Date Filtering       │
                         └──────────┬───────────┘
                                    │
                                    ▼
                         ┌──────────────────────┐
                         │        SQLite        │
                         │   Structured Data    │
                         └──────────┬───────────┘
                                    │
                                    ▼
                         ┌──────────────────────┐
                         │ Northeast Relevance  │
                         │     NLP  / Category  │
                         └──────────┬───────────┘
                                    │
                                    ▼
                         ┌──────────────────────┐
                         │ Scoring & Ranking    │
                         │ Deduplication        │
                         └──────────┬───────────┘
                                    │
                                    ▼
                         ┌──────────────────────┐
                         │  Selected Articles   │
                         └──────────┬───────────┘
                                    │
                    ┌───────────────┴────────────────┐
                    │                                │
                    ▼                                ▼
          ┌──────────────────┐             ┌──────────────────┐
          │ Sentence         │             │ Image Pipeline   │
          │ Transformers     │             │ Search / Relevance│
          │ Embeddings       │             │ / Download       │
          └────────┬─────────┘             └────────┬─────────┘
                   │                                │
                   ▼                                │
          ┌──────────────────┐                       │
          │      Chroma      │                       │
          │  Vector Store    │                       │
          └────────┬─────────┘                       │
                   │                                │
                   ▼                                │
          ┌──────────────────┐                       │
          │ RAG Retriever    │                       │
          └────────┬─────────┘                       │
                   │                                │
                   ▼                                │
          ┌──────────────────┐                       │
          │ Mistral LLM      │                       │
          │ Grounded Writing │                       │
          └────────┬─────────┘                       │
                   │                                │
                   ▼                                │
          ┌──────────────────┐                       │
          │ Grounding / QA   │                       │
          └────────┬─────────┘                       │
                   │                                │
                   └───────────────┬────────────────┘
                                   │
                                   ▼
                         ┌──────────────────────┐
                         │ Analytics & Charts   │
                         └──────────┬───────────┘
                                    │
                                    ▼
                         ┌──────────────────────┐
                         │ Magazine Page Builder│
                         │ 50-page Page Plan    │
                         └──────────┬───────────┘
                                    │
                                    ▼
                         ┌──────────────────────┐
                         │ Jinja2 + HTML/CSS    │
                         │ Magazine Renderer    │
                         └──────────┬───────────┘
                                    │
                                    ▼
                         ┌──────────────────────┐
                         │     WeasyPrint       │
                         │     HTML → PDF       │
                         └──────────┬───────────┘
                                    │
                                    ▼
                         ┌──────────────────────┐
                         │     PDF QA / Tests   │
                         └──────────┬───────────┘
                                    │
                                    ▼
                         ┌──────────────────────┐
                         │ Final 50-page PDF    │
                         └──────────────────────┘
```

------------------------------------------------------------------------

# Project Structure

``` text
northeast_magzine/
│
├── app/
│   │
│   ├── analytics/
│   │   ├── charts.py
│   │   ├── statistics.py
│   │   └── run_analytics.py
│   │
│   ├── config/
│   │   └── settings.py
│   │
│   ├── database/
│   │   ├── database.py
│   │   ├── models.py
│   │   ├── article_repository.py
│   │   ├── init_db.py
│   │   ├── migrate_scoring.py
│   │   └── cleanup_test_data.py
│   │
│   ├── embeddings/
│   │   └── embedder.py
│   │
│   ├── images/
│   │   ├── search.py
│   │   ├── downloader.py
│   │   ├── relevance.py
│   │   ├── deduplicator.py
│   │   └── pipeline.py
│   │
│   ├── llm/
│   │   ├── factory.py
│   │   ├── mistral.py
│   │   ├── gemini.py
│   │   └── groq.py
│   │
│   ├── magazine/
│   │   ├── content_generator.py
│   │   ├── page_builder.py
│   │   ├── render_magazine.py
│   │   └── templates/
│   │       ├── magazine.html
│   │       └── pdf_generator.py
│   │
│   ├── nlp/
│   │   ├── cleaner/relevance/classifier/NER
│   │   ├── relevance.py
│   │   ├── classifier.py
│   │   ├── ner.py
│   │   └── summarizer.py
│   │
│   ├── preprocessing/
│   │   ├── cleaner.py
│   │   ├── date_filter.py
│   │   └── deduplicator.py
│   │
│   ├── qa/
│   │   └── phase17_pdf_qa.py
│   │
│   ├── rag/
│   │   ├── retriever.py
│   │   ├── generator.py
│   │   └── grounding.py
│   │
│   ├── scoring/
│   │   ├── article_scorer.py
│   │   └── scoring_pipeline.py
│   │
│   ├── scraper/
│   │   ├── base_scraper.py
│   │   ├── article_discovery.py
│   │   ├── news_scraper.py
│   │   ├── pib_scraper.py
│   │   ├── image_scraper.py
│   │   └── collection_pipeline.py
│   │
│   └── vectorstore/
│       ├── chroma_store.py
│       └── test_retrieval.py
│
├── data/
│   ├── northeast_sentinel.db
│   ├── raw/
│   ├── processed/
│   ├── images/
│   ├── charts/
│   └── output/
│       ├── editorial_content.json
│       ├── magazine_data.json
│       ├── northeast_sentinel_magazine.html
│       └── northeast_sentinel_magazine.pdf
│
├── chroma_db/
├── templates/
├── tests/
├── main.py
├── requirements.txt
├── README.md
└── .env
```

> The exact project structure may evolve as additional pipeline
> components are added.

------------------------------------------------------------------------

# Technology Stack

## Data Collection

-   Python
-   Scrapling
-   Requests
-   BeautifulSoup

## Data Engineering

-   SQLite
-   SQLAlchemy
-   Pandas
-   Pydantic
-   Pydantic Settings

## NLP / Machine Learning

-   spaCy
-   Scikit-learn
-   Sentence Transformers
-   PyTorch
-   Torchvision

## RAG

-   LangChain
-   Chroma
-   Sentence Transformers
-   Mistral

## Image Processing

-   Pillow
-   Image search/download pipeline

## Analytics

-   Matplotlib
-   Seaborn
-   Plotly

## Publication

-   Jinja2
-   HTML
-   CSS
-   WeasyPrint

## Quality Assurance

-   Python validation scripts
-   PDF structural checks
-   Page-count validation
-   Asset validation

------------------------------------------------------------------------

# Installation

## 1. Clone the project

``` bash
git clone <your-repository-url>
cd northeast_magzine
```

If the project is already on your computer:

``` bash
cd northeast_magzine
```

------------------------------------------------------------------------

## 2. Create a virtual environment

Linux/macOS:

``` bash
python3 -m venv venv
source venv/bin/activate
```

Windows:

``` powershell
python -m venv venv
venv\Scripts\activate
```

------------------------------------------------------------------------

## 3. Install dependencies

``` bash
pip install -r requirements.txt
```

------------------------------------------------------------------------

# Environment Configuration

The project uses a `.env` file for API keys and environment-specific
configuration.

## Create the `.env` file

From the project root:

``` bash
touch .env
```

On Windows PowerShell:

``` powershell
New-Item .env
```

Or simply create a new file named:

``` text
.env
```

in the same directory as:

``` text
main.py
```

------------------------------------------------------------------------

# `.env` Configuration

A typical configuration is:

``` env
# ============================================================
# MISTRAL
# ============================================================

MISTRAL_API_KEY=your_mistral_api_key
MISTRAL_MODEL=your_mistral_model


```

Replace:

``` text
your_mistral_api_key
```

with your actual API key.

Example:

``` env
MISTRAL_API_KEY=xxxxxxxxxxxxxxxx
```

Do not put quotation marks around the key unless your configuration
specifically requires them.

------------------------------------------------------------------------

# Important Security Rule

**Never commit `.env` to GitHub.**

Add this to `.gitignore`:

``` gitignore
.env
venv/
__pycache__/
*.pyc
```

Your API keys are credentials and should remain private.

If an API key is accidentally pushed to GitHub, revoke it and generate a
new one.

------------------------------------------------------------------------

# Running the Project

The project is designed so that the main pipeline can be started from
the project root with:

``` bash
python main.py
```

That's the main command.

You do not need to manually run every phase one by one when the main
orchestration is configured correctly.

------------------------------------------------------------------------

# What Happens When You Run `python main.py`?

The execution flow is:

``` text
python main.py
      │
      ▼
Load configuration
      │
      ▼
Collect candidate news
      │
      ▼
Clean and validate articles
      │
      ▼
Apply date filter
      │
      ▼
Store article data in SQLite
      │
      ▼
Check Northeast relevance
      │
      ▼
Classify articles
      │
      ▼
Extract entities
      │
      ▼
Score and rank articles
      │
      ▼
Remove duplicates
      │
      ▼
Generate embeddings
      │
      ▼
Store/search vectors in Chroma
      │
      ▼
Retrieve relevant evidence
      │
      ▼
Generate grounded content with Mistral
      │
      ▼
Validate generated claims
      │
      ▼
Find and process article images
      │
      ▼
Generate analytics and charts
      │
      ▼
Build the magazine page plan
      │
      ▼
Generate HTML
      │
      ▼
Convert HTML to PDF
      │
      ▼
Run final validation
      │
      ▼
Final PDF
```

------------------------------------------------------------------------

# Final Output

After a successful run, the main publication is available in:

``` text
data/output/northeast_sentinel_magazine.pdf
```

The HTML version is:

``` text
data/output/northeast_sentinel_magazine.html
```

The magazine data/blueprint is:

``` text
data/output/magazine_data.json
```

Generated editorial content is stored in:

``` text
data/output/editorial_content.json
```

------------------------------------------------------------------------

# Output Directory

``` text
data/output/
│
├── editorial_content.json
│
├── magazine_data.json
│
├── northeast_sentinel_magazine.html
│
└── northeast_sentinel_magazine.pdf
```

The most important file is:

``` text
northeast_sentinel_magazine.pdf
```

Open that file after the program completes.

------------------------------------------------------------------------

# How the Project Works

## Phase 1 --- Web Discovery

The scraper discovers candidate news articles from configured sources.

Each candidate contains information such as:

``` text
Title
URL
Source
Publication date
Article body
Image information
```

------------------------------------------------------------------------

## Phase 2 --- Cleaning

Web pages often contain navigation text, advertisements, repeated
whitespace and other unwanted content.

The preprocessing layer converts the raw page into clean article text.

------------------------------------------------------------------------

## Phase 3 --- Date Filtering

Only articles inside the configured assignment period are allowed to
continue.

``` text
Candidate Article
       │
       ├── Outside date range → Reject
       │
       └── Inside date range → Continue
```

------------------------------------------------------------------------

## Phase 4 --- Northeast Relevance

The NLP layer determines whether the article has a meaningful connection
to Northeast India.

The system considers the region's eight states and related
regional/security context.

Irrelevant articles are removed.

------------------------------------------------------------------------

## Phase 5 --- Classification

Relevant articles are organized into editorial themes:

``` text
Security & Strategic Affairs
Development
Regional News
Society & Youth
Sports & Achievements
```

This classification later determines the magazine's section structure.

------------------------------------------------------------------------

## Phase 6 --- Entity Extraction

Named entities such as:

``` text
People
Places
Organizations
States
Institutions
```

are extracted to provide additional structure and context.

------------------------------------------------------------------------

## Phase 7 --- Article Scoring

Each article receives multiple relevance/quality signals.

The system considers factors such as:

-   Northeast relevance
-   Theme relevance
-   Security relevance
-   Freshness
-   Source quality
-   Content quality

The resulting score is used to rank the candidate articles.

------------------------------------------------------------------------

## Phase 8 --- Deduplication

Duplicate and near-duplicate stories are removed.

This prevents multiple reports about the same event from unnecessarily
occupying the magazine.

------------------------------------------------------------------------

## Phase 9 --- Semantic Embeddings

Selected article text is converted into numerical embeddings using
Sentence Transformers.

These embeddings represent the semantic meaning of the article.

------------------------------------------------------------------------

## Phase 10 --- Chroma Vector Store

The embeddings are stored locally in Chroma.

This allows the system to perform semantic retrieval instead of relying
only on keyword matching.

------------------------------------------------------------------------

## Phase 11 --- RAG

When editorial content needs to be generated, the system first retrieves
relevant evidence from Chroma.

``` text
Article topic
      ↓
Semantic retrieval
      ↓
Relevant evidence
      ↓
Mistral
```

This is Retrieval-Augmented Generation.

------------------------------------------------------------------------

## Phase 12 --- Grounded Editorial Generation

Mistral generates the magazine article using retrieved source evidence.

The generation process is intentionally constrained so that the model
does not act as an independent news source.

The grounding layer checks the generated claims against the retrieved
evidence.

Only grounded content should move forward to publication.

------------------------------------------------------------------------

## Phase 13 --- Image Processing

The image pipeline:

``` text
Search
 ↓
Download candidate
 ↓
Check relevance
 ↓
Deduplicate
 ↓
Store locally
```

Selected images are placed on article opener pages, while continuation
pages use the available space for text.

------------------------------------------------------------------------

## Phase 14 --- Analytics

The analytics system generates visual summaries such as:

``` text
Articles by Category
Articles by Source
Articles Over Time
Northeast State Coverage
```

These charts become part of the magazine.

------------------------------------------------------------------------

## Phase 15 --- Magazine Composition

The page builder converts the selected editorial dataset into a
deterministic page plan.

It creates:

``` text
Cover
Inside cover
Editor's note
Table of contents
Methodology
Section openers
Article pages
Analytics
Source index
Methodology
AI pipeline
Back cover
```

The current target is:

``` text
50 pages
```

------------------------------------------------------------------------

## Phase 16 --- HTML Rendering

Jinja2 takes the structured page plan and renders it using:

``` text
magazine.html
```

The HTML/CSS controls the visual presentation:

-   Typography
-   Spacing
-   Images
-   Headers
-   Footers
-   Page numbers
-   Source information
-   Charts
-   Cover design
-   Section design

------------------------------------------------------------------------

## Phase 17 --- PDF Generation

WeasyPrint converts the final HTML/CSS magazine into a PDF.

``` text
HTML + CSS
    ↓
WeasyPrint
    ↓
PDF
```

------------------------------------------------------------------------

## Phase 18 --- Quality Assurance

The final PDF is checked for:

-   File existence
-   PDF readability
-   Page count
-   HTML page count
-   Asset availability
-   Content integrity
-   Layout/pagination problems
-   Missing images/charts

The goal is to prevent an apparently successful generation from
producing an invalid publication.

------------------------------------------------------------------------

# Current Magazine Composition

The current generated dataset contains:

``` text
Selected articles : 11
Sections          : 5
Charts            : 4
Target pages      : 50
Logical pages     : 50
Article pages     : 23
Chart pages       : 4
```

The magazine is therefore not simply a collection of articles; the page
builder creates a complete publication structure around the selected
corpus.

------------------------------------------------------------------------

# Example Article Flow

Consider an article such as:

``` text
Assam Rifles Seize Rs 5.07 Crore Heroin in Mizoram
```

The article passes through:

``` text
Web article
    ↓
Scrapling
    ↓
Cleaning
    ↓
Date validation
    ↓
Northeast relevance
    ↓
Security classification
    ↓
Article scoring
    ↓
Deduplication
    ↓
Embedding
    ↓
Chroma
    ↓
RAG retrieval
    ↓
Mistral generation
    ↓
Grounding
    ↓
Image selection
    ↓
Magazine page builder
    ↓
HTML
    ↓
PDF
```

This illustrates the complete end-to-end architecture.

------------------------------------------------------------------------

# Why RAG Is Used

A normal LLM workflow would be:

``` text
Prompt
  ↓
LLM
  ↓
Answer
```

This project uses:

``` text
Article
  ↓
Embedding
  ↓
Chroma
  ↓
Relevant evidence
  ↓
Mistral
  ↓
Grounding
  ↓
Editorial article
```

The purpose is to make generated content more traceable to the collected
source material.

------------------------------------------------------------------------

# Why SQLite and Chroma Are Both Used

They solve different problems.

### SQLite

Stores structured application data:

``` text
Article ID
Title
Source
URL
Date
Category
Scores
Article content
Metadata
```

### Chroma

Stores semantic vector representations:

``` text
Article text
      ↓
Embedding vector
      ↓
Semantic search
```

Therefore:

``` text
SQLite = structured data

Chroma = semantic retrieval
```

------------------------------------------------------------------------

# Why the Project Uses a Page Builder

The page builder separates **content decisions** from **visual
presentation**.

It determines:

``` text
What goes on page 1?
What goes on page 2?
Which article continues?
Where do charts appear?
Where does the source index appear?
```

Jinja2/CSS then determines:

``` text
How those pages look.
```

This separation makes the magazine easier to maintain and redesign.

------------------------------------------------------------------------

# Reproducibility

The project is designed to keep generated assets local:

``` text
data/images/
data/charts/
data/output/
chroma_db/
data/northeast_sentinel.db
```

This helps make the final HTML and PDF rendering deterministic after the
data-generation stages have completed.

------------------------------------------------------------------------

# Troubleshooting

## `ModuleNotFoundError`

Make sure you run the project from the root directory:

``` bash
cd northeast_magzine
python main.py
```

Do not run individual modules from inside `app/` unless the module is
designed to be executed that way.

------------------------------------------------------------------------

## API key errors

Check:

``` text
.env
```

and confirm the required API key is present.

Example:

``` env
MISTRAL_API_KEY=your_key_here
```

Do not include extra spaces around the `=`.

------------------------------------------------------------------------

## PDF not generated

First check the terminal output from:

``` bash
python main.py
```

Then inspect:

``` text
data/output/
```

The expected final file is:

``` text
northeast_sentinel_magazine.pdf
```

------------------------------------------------------------------------

## PDF has missing images

Check that:

``` text
data/images/
data/charts/
```

contain the referenced assets.

Also ensure that the HTML renderer uses paths relative to:

``` text
data/output/northeast_sentinel_magazine.html
```

------------------------------------------------------------------------

## PDF page count is incorrect

Check:

``` text
data/output/magazine_data.json
```

and the validation information generated by the page builder.

Then inspect the PDF QA output.

------------------------------------------------------------------------

# Development Notes

The project is organized as a multi-stage pipeline rather than a single
monolithic script.

The major stages are:

``` text
Collection
→ Preprocessing
→ Database
→ NLP
→ Scoring
→ Deduplication
→ Embeddings
→ Vector Search
→ RAG
→ Grounding
→ Images
→ Analytics
→ Composition
→ HTML
→ PDF
→ QA
```

This architecture makes individual stages easier to test, replace and
improve.

------------------------------------------------------------------------

# Main Technologies

``` text
Python
Scrapling
SQLAlchemy
SQLite
Pandas
spaCy
Scikit-learn
Sentence Transformers
PyTorch
LangChain
Chroma
Mistral
Pillow
Matplotlib
Plotly
Jinja2
WeasyPrint
```

------------------------------------------------------------------------

# Project Output

The final deliverable is:

``` text
data/output/northeast_sentinel_magazine.pdf
```

The corresponding HTML publication is:

``` text
data/output/northeast_sentinel_magazine.html
```

The machine-readable magazine blueprint is:

``` text
data/output/magazine_data.json
```

------------------------------------------------------------------------

# Quick Start

For a clean installation:

``` bash
git clone <your-repository-url>
cd northeast_magzine

python -m venv venv
source venv/bin/activate

pip install -r requirements.txt
```

Create `.env`:

``` env
MISTRAL_API_KEY=your_mistral_api_key
MISTRAL_MODEL=your_mistral_model

HUGGINGFACE_API_KEY=your_huggingface_api_key
HUGGINGFACE_EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2
```

Then run:

``` bash
python main.py
```

When the pipeline completes, open:

``` text
data/output/northeast_sentinel_magazine.pdf
```

------------------------------------------------------------------------

# Security

Never commit:

``` text
.env
API keys
private credentials
```

Recommended `.gitignore`:

``` gitignore
.env
venv/
__pycache__/
*.pyc
```

------------------------------------------------------------------------

# Project Philosophy

Northeast Sentinel AI is built around a simple principle:

> **Automate the editorial workflow while keeping the source material,
> selection process, retrieval evidence and final publication
> traceable.**

The system therefore separates:

``` text
Data collection
      ↓
Data validation
      ↓
Machine-assisted selection
      ↓
Evidence retrieval
      ↓
Grounded generation
      ↓
Visual composition
      ↓
Publication
      ↓
Quality assurance
```

This makes the project more than a news scraper or an LLM wrapper. It is
an end-to-end AI-assisted editorial production system.

------------------------------------------------------------------------
