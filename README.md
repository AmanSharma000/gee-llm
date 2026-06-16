<<<<<<< HEAD
# GEE-LLM: A Lightweight Agentic Framework for Google Earth Engine Code Generation

[![Python 3.9+](https://img.shields.io/badge/Python-3.9+-blue.svg)](https://www.python.org/)
[![Earth Engine API](https://img.shields.io/badge/Earth_Engine-API-green.svg)](https://earthengine.google.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Streamlit App](https://img.shields.io/badge/Live_App-Streamlit-red.svg)](https://geo-ai-llm-aman.streamlit.app/)

**GEE-LLM** is a lightweight, compute-agnostic agentic framework that translates natural-language geospatial queries into executable [Google Earth Engine](https://earthengine.google.com/) (GEE) Python scripts on commodity hardware — no GPU required.

🌐 **Live Demo**: [https://geo-ai-llm-aman.streamlit.app/](https://geo-ai-llm-aman.streamlit.app/)  
📦 **Repository**: [https://github.com/AmanSharma000/gee-llm](https://github.com/AmanSharma000/gee-llm)

---

## 🔬 Why GEE-LLM?

Standard large language models (LLMs) fail at GEE code generation because GEE uses a *deferred server-side* computational graph. General LLMs generate eager-execution scripts that raise `EEException` at runtime. GEE-LLM solves this by combining:

1. **Lexical RAG retrieval (TF-IDF)** — matches the user query to one of 51 curated GEE template scripts
2. **Local subprocess sandbox** — executes generated code in isolation and captures GEE tracebacks
3. **Self-correction loop** — translates runtime exceptions into targeted re-prompts (up to 3 attempts)
4. **Physical bounds validation** — rejects scripts that succeed but return spectral values outside physically valid ranges

---

## 🚀 System Architecture

```
┌──────────────────────┐
│ Natural Language Query│
└──────────┬───────────┘
           │
           ▼
┌────────────────────────────┐
│  Lexical RAG Retriever     │ ◄─── 51 GEE Code Templates
│  (TF-IDF keyword match)    │
└─────────────┬──────────────┘
              │ inject context
              ▼
┌────────────────────────────┐
│    LLM Code Generator      │
│  (Cohere / Groq / Ollama)  │
└─────────────┬──────────────┘
              │ GEE Python code
              ▼
┌────────────────────────────┐
│  Local Subprocess Sandbox  │ ◄─── execution loop
└─────────────┬──────────────┘
              │ runtime exception traceback
              ▼
┌────────────────────────────┐
│   Self-Correction Logic    │ ──► translates GEE errors → re-prompt
└─────────────┬──────────────┘
              │ valid server graph
              ▼
┌────────────────────────────┐
│ Physical Bounds Validator  │ ──► rejects invalid spectral values
└─────────────┬──────────────┘
              │
              ▼
┌──────────────────────┐
│  Final Verified Result│
└──────────────────────┘
```

---

## 📦 Repository Structure

```
gee-llm/
├── app.py                          # Streamlit web dashboard
├── requirements.txt                # Python dependencies
├── LICENSE                         # MIT License
├── README.md                       # This file
├── TUTORIAL.md                     # Comprehensive step-by-step user guide
├── CONTRIBUTING.md                 # Contribution guidelines
├── CHANGELOG.md                    # Version history
│
├── backend/
│   ├── engine.py                   # Core pipeline orchestrator
│   ├── llm_client.py               # LLM API client (Cohere / Ollama)
│   ├── llm_client_multi.py         # Multi-model client (Cohere, Groq, Ollama)
│   ├── gee_runner.py               # Safe GEE subprocess runner
│   ├── self_corrector.py           # Exception parsing & self-correction
│   ├── error_analyzer.py           # GEE error pattern library
│   ├── comparison_engine.py        # Region & temporal comparison
│   ├── satellite_selector.py       # Resolution-based satellite selector
│   ├── geometry_parser.py          # GeoJSON/KML/ZIP boundary upload
│   ├── geometry_validator.py       # Area & vertex density checks
│   ├── export_handler.py           # CSV/JSON export
│   ├── cache_manager.py            # Local disk cache
│   ├── query_logger.py             # Query telemetry logger
│   └── rag/
│       ├── retriever.py            # TF-IDF sparse retrieval engine
│       ├── prompt_builder.py       # Context-aware prompt construction
│       ├── examples.jsonl          # Evaluated RAG query dataset
│       └── snippets/               # 51 curated GEE code templates
│           └── *.py
│
├── data/
│   ├── benchmark_100_queries_final.json   # 100-query evaluation benchmark
│   └── README_data.md                     # Data provenance & schema
│
├── tests/
│   ├── test_comparison_parsing.py
│   ├── test_retriever_v2.py
│   ├── test_robustness.py
│   └── test_self_correction_logic.py
│
├── reproduce/
│   ├── README_reproduce.md         # Step-by-step reproducibility guide
│   ├── run_benchmark.py            # Cross-platform benchmark runner
│   └── sample_output_expected.json # Expected outputs for 5 queries
│
└── docs/
    ├── QUICKSTART.md               # 5-minute getting-started guide
    ├── USER_GUIDE.md               # Inputs, outputs, options, behaviour
    └── ARCHITECTURE.md             # Deep-dive design document
```

---

## 🖥️ Computational Requirements

| Requirement | Minimum | Recommended |
|---|---|---|
| CPU | Any x86-64 (2 cores) | 4+ cores |
| RAM | 4 GB | 8 GB |
| GPU | ❌ Not required | — |
| OS | Windows / Linux / macOS | Linux/macOS for CI |
| Network | Internet (GEE API + LLM API) | — |
| Storage | ~200 MB | — |

---

## 🛠️ Installation & Setup

### Prerequisites
- Python 3.9 or higher
- A registered [Google Earth Engine account](https://earthengine.google.com)
- A **Cohere API key** ([free tier available](https://cohere.com)) **OR** local [Ollama](https://ollama.com) for offline execution

### 1. Clone the Repository
```bash
git clone https://github.com/AmanSharma000/gee-llm.git
cd gee-llm
```

### 2. Create Virtual Environment
```bash
# Windows
python -m venv .venv
.venv\Scripts\activate

# Linux / macOS
python3 -m venv .venv
source .venv/bin/activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Authenticate Google Earth Engine
```bash
earthengine authenticate
```

### 5. Set API Credentials
Create `.streamlit/secrets.toml`:
```toml
COHERE_API_KEY = "your-cohere-api-key-here"
```
*Or export as an environment variable:*
```bash
export COHERE_API_KEY="your-key"        # Linux/macOS
set COHERE_API_KEY=your-key             # Windows
```

### 6. Launch the Dashboard
```bash
streamlit run app.py
```
Open [http://localhost:8501](http://localhost:8501) in your browser.

> **Quick Start**: See [docs/QUICKSTART.md](docs/QUICKSTART.md) for a 5-minute guide.

---

## 💬 Example Queries

| Query | Index | Satellite |
|---|---|---|
| `ndvi trend of mumbai from 2018 to 2023` | NDVI | Auto (Sentinel-2) |
| `compare ndvi of delhi vs mumbai for 2023` | NDVI | Auto |
| `evi of jaipur city for 2022 using sentinel-2` | EVI | Sentinel-2 |
| `mndwi of west bengal for 2023` | MNDWI | Landsat-8 |
| `forest change in western ghats from 2015 to 2023` | NBR | Landsat-8 |

---

## 📊 Benchmark Results

Evaluated on a 100-query benchmark spanning diverse Indian ecological zones:

| Model | Baseline Success | GEE-LLM Success | Improvement |
|---|---|---|---|
| Cohere Command-A | 12.0% | 44.0% | +32 pp |
| Groq Llama-3.3-70B | 17.0% | 45.0% | +28 pp |

McNemar's test: *p* < 0.001, odds ratio up to 15.0. See [`reproduce/`](reproduce/) to run the benchmark yourself.

---

## 🔁 Reproducibility

To reproduce the main results from the paper:
```bash
cd reproduce
python run_benchmark.py
```
See [`reproduce/README_reproduce.md`](reproduce/README_reproduce.md) for the full guide, including expected outputs and notes on non-determinism.

---

## 🎯 Supported Spectral Indices & Satellites

| Satellite | Resolution | Archive Start |
|---|---|---|
| Sentinel-2 | 10 m | 2015 |
| Landsat-8 | 30 m | 2013 |
| MODIS | 500 m | 2000 |

**Indices**: NDVI · EVI · SAVI · NDWI · MNDWI · NDMI · NBR · UI · BSI · MSAVI · NDSI · GCI · LST · AOD

---

## 📄 Citation

If you use GEE-LLM in your research, please cite:

```bibtex
@article{sharma2026geellm,
  title   = {GEE-LLM as a Lightweight Agentic Framework for Automated Geospatial Code Generation},
  author  = {Sharma, Aman and Kumar, Manish},
  journal = {(under review)},
  year    = {2026}
}
```

---

## 🤝 Contributing

Contributions are welcome! Please read [CONTRIBUTING.md](CONTRIBUTING.md) before submitting a pull request.

---

## 🔑 License

This project is licensed under the [MIT License](LICENSE) — see the file for details.
=======
# gee-llm
GEE-LLM as a Lightweight Agentic Framework for Automated Geospatial Code Generation
>>>>>>> 5019b3a23db7506c380d5853182ff6757ffaa838
