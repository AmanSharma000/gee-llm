# Architecture — GEE-LLM

This document describes the internal design of the GEE-LLM framework in depth.

---

## Table of Contents

1. [Design Philosophy](#1-design-philosophy)
2. [Pipeline Overview](#2-pipeline-overview)
3. [Module Reference](#3-module-reference)
4. [Data Flow Diagram](#4-data-flow-diagram)
5. [RAG Retrieval System](#5-rag-retrieval-system)
6. [Self-Correction Loop](#6-self-correction-loop)
7. [Physical Bounds Validation](#7-physical-bounds-validation)
8. [Caching Strategy](#8-caching-strategy)
9. [Known Limitations](#9-known-limitations)

---

## 1. Design Philosophy

GEE-LLM is designed around three constraints:

1. **No GPU required** — all computation runs on standard CPUs. TF-IDF retrieval is O(n·d) where n is the number of templates and d is vocabulary size; both are small.
2. **Minimal external dependencies** — the only mandatory cloud service is the GEE API itself. LLM can be replaced by a local Ollama model.
3. **Fail-safe pipeline** — every stage either succeeds cleanly or returns a structured error that triggers the self-correction path.

---

## 2. Pipeline Overview

```
User Query (natural language)
        │
        ▼
┌────────────────────────────────────┐
│  1. Query Pre-processing           │
│  • Comparison detection            │
│  • Satellite auto-selection        │
│  • Custom geometry injection       │
└──────────────┬─────────────────────┘
               │
               ▼
┌────────────────────────────────────┐
│  2. RAG Retrieval (TF-IDF)         │
│  • Build TF-IDF matrix over 51     │
│    template metadata strings       │
│  • Cosine-similarity top-K match   │
│  • Load matched .py template file  │
└──────────────┬─────────────────────┘
               │ template code + metadata
               ▼
┌────────────────────────────────────┐
│  3. Prompt Construction            │
│  • System rules (GEE constraints)  │
│  • Injected template as example    │
│  • Satellite & geometry context    │
└──────────────┬─────────────────────┘
               │ prompt string
               ▼
┌────────────────────────────────────┐
│  4. LLM Code Generation            │
│  • Cohere / Groq / Ollama          │
│  • temperature = 0.3               │
│  • Extract Python code block       │
└──────────────┬─────────────────────┘
               │ generated GEE Python script
               ▼
┌────────────────────────────────────┐
│  5. Subprocess Sandbox Execution   │
│  • Spawns isolated Python process  │
│  • 60-second timeout               │
│  • Captures stdout JSON + stderr   │
└──────────────┬─────────────────────┘
          ┌────┴────┐
      success    failure
          │           │
          │           ▼
          │  ┌─────────────────────────┐
          │  │  6. Self-Correction      │
          │  │  • Analyze error type    │
          │  │  • Build correction      │
          │  │    prompt with traceback │
          │  │  • Re-query LLM          │
          │  │  • Retry (up to 3 times) │
          │  └────────────┬────────────┘
          │               │
          └───────────────┤
                          ▼
           ┌────────────────────────────┐
           │  7. Physical Validation    │
           │  • Check spectral bounds   │
           │  • Reject invalid results  │
           └──────────────┬─────────────┘
                          │
                          ▼
                   Final Result
```

---

## 3. Module Reference

| Module | File | Responsibility |
|---|---|---|
| Pipeline Orchestrator | `backend/engine.py` | Coordinates all stages; entry point |
| LLM Client | `backend/llm_client.py` | Cohere + Ollama API calls |
| Multi-Model Client | `backend/llm_client_multi.py` | Cohere + Groq + Ollama selection |
| GEE Sandbox | `backend/gee_runner.py` | Subprocess isolation, timeout, result extraction |
| Self-Corrector | `backend/self_corrector.py` | Error→correction-prompt loop |
| Error Analyzer | `backend/error_analyzer.py` | Regex-based GEE error pattern library (10+ patterns) |
| RAG Retriever | `backend/rag/retriever.py` | TF-IDF vectorizer + cosine similarity |
| Prompt Builder | `backend/rag/prompt_builder.py` | System prompt + context assembly |
| Comparison Engine | `backend/comparison_engine.py` | Parses `X vs Y` queries into two sub-queries |
| Satellite Selector | `backend/satellite_selector.py` | Area-based Sentinel-2 / Landsat / MODIS selection |
| Geometry Parser | `backend/geometry_parser.py` | GeoJSON/KML/ZIP → `ee.Geometry` |
| Geometry Validator | `backend/geometry_validator.py` | Area & vertex density checks |
| Export Handler | `backend/export_handler.py` | CSV/JSON export formatting |
| Cache Manager | `backend/cache_manager.py` | DiskCache read/write with TTL |
| Query Logger | `backend/query_logger.py` | Append-only query telemetry log |

---

## 4. Data Flow Diagram

```
app.py (Streamlit UI)
    │
    │  query: str
    │  custom_geometry: ee.Geometry | None
    ▼
engine.handle_geo_query()
    │
    ├─► satellite_selector.select_best_satellite(query)
    │       └─► returns: {satellite, collection_id, scale, bands}
    │
    ├─► rag.retriever.retrieve_examples(query, top_k=3)
    │       └─► TF-IDF match → list of {query, code_file, index}
    │
    ├─► rag.prompt_builder.build_prompt(query, examples, satellite_info)
    │       └─► returns: str (full LLM prompt)
    │
    ├─► llm_client.call_llm(prompt)
    │       └─► returns: str (LLM response with code block)
    │
    ├─► gee_runner.run_gee_code(code, custom_geometry)
    │       └─► returns: {success, result, error}
    │
    └─► [if failure] self_corrector.execute_with_self_correction()
            ├─► error_analyzer.analyze_error(error_msg, code)
            ├─► build correction prompt
            ├─► call_llm(correction_prompt)
            └─► gee_runner.run_gee_code(corrected_code)  ← up to 3×
```

---

## 5. RAG Retrieval System

### Template Library

The `backend/rag/snippets/` directory contains **51 hand-curated GEE Python scripts**, each covering a specific combination of:
- Spectral index (NDVI, EVI, MNDWI, NBR, …)
- Satellite (Sentinel-2, Landsat-8, MODIS, Sentinel-1 SAR)
- Indian ecological zone (arid, semi-arid, tropical, coastal, Himalayan, urban)

### Retrieval Mechanism

1. **Index time**: A TF-IDF matrix is built over the metadata strings in `examples.jsonl` (query text + index + satellite).
2. **Query time**: The user query is vectorized using the same vocabulary. Cosine similarity is computed against all 51 templates.
3. **Top-K selection**: The 3 most similar templates are loaded and their code is injected into the LLM prompt as few-shot examples.

**Why TF-IDF instead of dense embeddings?**  
Dense embeddings require either a GPU or a slow CPU embedding API call. TF-IDF runs in < 50ms on CPU, satisfies the compute-agnostic design goal, and achieves comparable retrieval quality on the narrow GEE domain vocabulary.

---

## 6. Self-Correction Loop

```
Attempt 1: generate → execute → ✗ fail
    │
    ▼
error_analyzer.analyze_error(traceback, code)
    │
    ├─ pattern: "'list' object has no attribute 'map'"
    │       → suggestion: "Wrap in ee.List(): years = ee.List([...]); years.map(...)"
    │
    ├─ pattern: "Computation timed out"
    │       → suggestion: "Add bestEffort=True to reduceRegion()"
    │
    ├─ pattern: "Empty ImageCollection"
    │       → suggestion: "Widen date filter or check cloud threshold"
    │
    └─ pattern: unknown → "Review GEE API usage"
            │
            ▼
correction_prompt = original_prompt + "\n\nPREVIOUS CODE:\n{code}\n\nERROR:\n{traceback}\n\nFIX:\n{suggestion}"
            │
            ▼
Attempt 2: regenerate → execute → ✓ (or → Attempt 3)
```

The self-correction loop implements a key insight from the paper: **GEE errors are highly structured and predictable**. The 10 most common error types (client-side type mismatches and server-side memory overruns) account for ~77% of all failures, making targeted prompting highly effective.

---

## 7. Physical Bounds Validation

After successful execution, the result dict is checked for physically implausible values:

| Index | Valid Range | Action if violated |
|---|---|---|
| NDVI, EVI, NDWI, … | −1.0 to +1.0 | Reject, return error |
| LST | −50°C to +70°C | Reject, return error |
| AOD | 0.0 to 5.0 | Reject, return error |
| Histogram bin counts | ≥ 0 | Reject negative counts |

This layer catches scripts that execute without raising a Python exception but produce scientifically invalid data (e.g., an LLM that forgot to apply `.divide(10000)` to Sentinel-2 reflectance bands, yielding NDVI > 3.0).

---

## 8. Caching Strategy

- **Library**: [DiskCache](https://grantjenks.com/docs/diskcache/) (file-based, SQLite backend)
- **Cache key**: SHA-256 hash of `(query, custom_geometry_wkt)`
- **TTL**: 7 days (GEE data for past years does not change)
- **Location**: `data/cache/` (excluded from git)
- **Benefit**: Eliminates redundant GEE API calls for repeated queries (important for benchmark runs)

---

## 9. Known Limitations

| Limitation | Details |
|---|---|
| **India-only boundaries** | The `India_sorted` GEE asset covers India only. Non-Indian regions require a custom geometry upload. |
| **GEE account required** | A Google Earth Engine account is mandatory for all actual data queries. |
| **LLM non-determinism** | Results may vary slightly across runs due to LLM temperature (set to 0.3). |
| **No real-time data** | GEE imagery has a processing lag of ~5 days for Sentinel-2 and ~1 day for MODIS. |
| **English queries only** | The TF-IDF vocabulary and LLM prompts are English-only. |
| **Single-user Streamlit** | The default Streamlit deployment is single-user. For multi-user, deploy with `--server.port` and a reverse proxy. |
