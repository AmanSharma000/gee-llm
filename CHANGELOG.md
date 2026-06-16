# Changelog

All notable changes to GEE-LLM are documented here.  
Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

---

## [1.0.0] — 2026-06-17

### Added
- Initial public release of the GEE-LLM framework.
- `backend/engine.py`: Core pipeline orchestrator — RAG retrieval → LLM generation → sandbox execution → self-correction → bounds validation.
- `backend/rag/retriever.py`: TF-IDF sparse lexical retrieval engine over 51 GEE code templates.
- `backend/rag/snippets/`: 51 curated GEE Python template scripts covering NDVI, EVI, SAVI, MNDWI, NBR, LST, AOD, SAR indices across Sentinel-2, Landsat-8, and MODIS.
- `backend/self_corrector.py`: Self-correction loop that translates GEE runtime exceptions into targeted correction prompts (up to 3 retries).
- `backend/error_analyzer.py`: Library of 10+ regex-matched GEE error patterns (type-mismatch, memory overrun, empty collection, etc.).
- `backend/comparison_engine.py`: Region-vs-region and temporal comparison query parser.
- `backend/satellite_selector.py`: Resolution-based automatic satellite selector.
- `backend/geometry_parser.py`: Custom boundary upload support (GeoJSON, KML, Shapefile ZIP).
- `backend/geometry_validator.py`: Area and vertex density validation.
- `backend/llm_client_multi.py`: Multi-model LLM client supporting Cohere Command-A, Groq Llama-3.3-70B, and Ollama (offline).
- `app.py`: Streamlit web dashboard with map visualization, export, and comparison UI.
- `data/benchmark_100_queries_final.json`: 100-query benchmark dataset spanning 10 Indian ecological zones.
- `reproduce/run_benchmark.py`: Cross-platform benchmark runner.
- `reproduce/sample_output_expected.json`: Expected outputs for 5 representative queries.
- `tests/`: 4 offline unit test modules (no GEE credentials required).
- `docs/`: QUICKSTART, USER_GUIDE, and ARCHITECTURE documentation.
