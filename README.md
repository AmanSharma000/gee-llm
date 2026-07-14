# GEE-LLM: Grounded Google Earth Engine Code Generation and Scientific Interpretation for Geospatial Decision Support

[![Python 3.9+](https://img.shields.io/badge/Python-3.9+-blue.svg)](https://www.python.org/)
[![Earth Engine API](https://img.shields.io/badge/Earth_Engine-API-green.svg)](https://earthengine.google.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Streamlit UI](https://img.shields.io/badge/UI-Streamlit-red.svg)](https://streamlit.io/)

GEE-LLM is a lightweight, compute-agnostic agentic framework designed to close the loop from natural-language geospatial queries to decision-ready environmental insight. Operating on commodity CPU hardware, the framework translates queries into execution-validated Google Earth Engine (GEE) Python code and generates grounded, data-traceable scientific interpretations of the satellite statistics to support geospatial decision-making without raw imagery access or model hallucinations.

---

## 🚀 System Architecture

The GEE-LLM pipeline coordinates five key stages to generate, verify, and interpret Earth Engine analyses:

```
                  ┌──────────────────────┐
                  │ Natural Language Query│
                  └──────────┬───────────┘
                             │
                             ▼
               ┌───────────────────────────┐     
               │  Lexical RAG Retriever    │ ◄─── [50+ GEE Templates]
               └─────────────┬─────────────┘
                             │ (Inject Context)
                             ▼
               ┌───────────────────────────┐
               │    LLM Code Generator     │
               └─────────────┬─────────────┘
                             │ (GEE Python Code)
                             ▼
               ┌───────────────────────────┐
               │  Local Subprocess Sandbox  │ ◄─── (Execution Loop)
               └─────────────┬─────────────┘
                             │ (Runtime Exception Traceback)
                             ▼
               ┌───────────────────────────┐
               │   Self-Correction Logic   │ ───► [Translates GEE Errors]
               └─────────────┬─────────────┘
                             │ (Valid Server Graph)
                             ▼
               ┌───────────────────────────┐
               │ Physical Bounds Validator │ ───► [Checks Spectral Limits]
               └─────────────┬─────────────┘
                             │ (Verified Numeric Result)
                             ▼
               ┌───────────────────────────┐
               │  Grounded Interpretation   │ ───► [Scientific Narrative]
               └─────────────┬─────────────┘
                             │
                             ▼
                  ┌──────────────────────┐
                  │ Final Verified Output│
                  └──────────────────────┘
```

---

## 📦 Project Directory Structure

```
geo-gee-llm-adv/
├── app.py                          # Main Streamlit web application dashboard
├── requirements.txt                # System dependencies
├── LICENSE                         # Open-source MIT License
├── README.md                       # Core system documentation
├── TUTORIAL.md                     # Comprehensive 80+ page step-by-step user guide
├── project_pdf.pdf                 # Formatted PDF version of the guide
├── backend/
│   ├── engine.py                   # Core pipeline orchestrator
│   ├── llm_client.py               # LLM integration client (Cohere API / Ollama)
│   ├── gee_runner.py               # Safe Earth Engine subprocess runner
│   ├── self_corrector.py           # Subprocess exception parsing & prompt translation
│   ├── error_analyzer.py           # Regular expression compiler for GEE tracebacks
│   ├── comparison_engine.py        # Regional & temporal comparison logic
│   ├── satellite_selector.py       # Smart resolution-based satellite selection
│   ├── geometry_parser.py          # Custom spatial boundary uploads (GeoJSON, KML, ZIP)
│   ├── geometry_validator.py       # Area & vertex density checks
│   ├── export_handler.py           # Result formatting exports (CSV, JSON)
│   ├── cache_manager.py            # Local disk cache to reduce server load
│   ├── query_logger.py             # System telemetry logger
│   └── rag/
│       ├── retriever.py            # TF-IDF sparse lexical retrieval engine
│       ├── prompt_builder.py       # Context-aware prompt construction
│       ├── examples.jsonl          # Evaluated RAG queries dataset
│       └── snippets/               # Directory of 50+ GEE code templates
├── RESEARCH_PAPER/
│   ├── Spatial Information Research_llm/ # Special Issue LaTeX & compiled manuscript files
│   │   ├── RESEARCH_PAPER_SIR.tex       # Main manuscript source document
│   │   ├── TITLE_PAGE_SIR.tex           # Submissions title page
│   │   ├── COVER_LETTER_SIR.tex         # Professional submission cover letter
│   │   └── RESEARCH_PAPER_SIR.pdf       # Compiled 26-page manuscript PDF
│   ├── references/                 # isolates human-expert ground-truth scripts
│   │   └── ref_*.py (15 files)     # Reference code for benchmark validation
│   ├── compute_codebleu.py         # Code similarity evaluation suite
│   └── run_evaluation_benchmark.py # Script to run evaluations on models
└── scratch/
    ├── check_all_references.py     # Verification runner for reference scripts
    └── reference_checks.json       # Live execution results telemetry
```

---

## 🛠️ Installation & Setup

### Prerequisites
- Python 3.9 or higher
- A registered Google Earth Engine Account ([Sign up](https://earthengine.google.com))
- A Cohere API key ([Get a free key](https://cohere.com)) OR a local installation of [Ollama](https://ollama.com) (for private, offline execution)

### 1. Clone the Repository
```bash
git clone https://github.com/AmanSharma000/geo-gee-llm-adv.git
cd geo-gee-llm-adv
```

### 2. Configure Virtual Environment
**Windows:**
```powershell
python -m venv .venv
.venv\Scripts\activate
```
**Linux / macOS:**
```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Authenticate Google Earth Engine
Initialize Earth Engine authentication from the terminal:
```bash
earthengine authenticate
```

### 5. Set API Credentials
Create a `.streamlit/secrets.toml` file in the project root:
```toml
COHERE_API_KEY = "your-cohere-api-key-here"
```
*Alternatively, you can export it as an environment variable:*
```bash
export COHERE_API_KEY="your-key"
```

---

## 🚀 Launching the Dashboard

Run the Streamlit frontend to interact with GEE-LLM via a local web interface:
```bash
streamlit run app.py
```
Navigate to `http://localhost:8501` to use the dashboard.

### Example Queries:
- **Index trend:** `ndvi trend of mumbai from 2018 to 2023`
- **Region comparison:** `compare ndvi of delhi vs mumbai for 2023`
- **Satellite selection:** `evi of jaipur city for 2022 using sentinel-2`
- **Water mapping:** `mndwi of west bengal for 2023`

---

## 📊 Open Science & Reproducibility Suite

To support peer-review evaluation (specifically for the *Spatial Information Research* Special Issue), the repository includes automated verification and similarity testing harnesses:

### 1. Verify Ground-Truth References
To execute the 15 human-expert reference scripts on the live GEE backend using the public `India_sorted` boundary asset:
```bash
python scratch/check_all_references.py
```
This script validates execution status and saves the output telemetry directly to `scratch/reference_checks.json`.

### 2. Compute CodeBLEU Metrics
To evaluate the similarity of generated code against the human-expert reference suite:
```bash
python RESEARCH_PAPER/compute_codebleu.py
```

### 3. Run the Evaluation Benchmark
To run the full 100-query benchmark across different local or API-based model configurations:
```bash
python RESEARCH_PAPER/run_evaluation_benchmark.py
```

---

## 🎯 Supported Spectral Indices & Satellites

### Satellites
*   **Sentinel-2 (10m):** High-resolution terrestrial indices (2015-present).
*   **Landsat-8 (30m):** Medium-resolution long-term analysis (2013-present).
*   **MODIS (500m):** High-frequency daily regional composites (2000-present).

### Spectral Indices
*   **NDVI:** Normalized Difference Vegetation Index
*   **EVI:** Enhanced Vegetation Index
*   **SAVI:** Soil Adjusted Vegetation Index
*   **NDWI / MNDWI:** Water Index / Modified Water Index
*   **NDMI:** Normalized Difference Moisture Index
*   **NBR:** Normalized Burn Ratio
*   **UI:** Urban Index
*   **BSI:** Bare Soil Index

---

## 🔑 License
This project is licensed under the [MIT License](LICENSE) - see the LICENSE file for details.
