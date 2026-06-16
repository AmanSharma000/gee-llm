# Data Directory

This directory contains the benchmark dataset used to evaluate the GEE-LLM framework in the accompanying research paper.

---

## Files

### `benchmark_100_queries_final.json`

**Description**: 100 natural-language geospatial queries used to evaluate baseline LLMs and GEE-LLM on automated Earth Engine code generation.

**Schema** (each entry):
```json
{
  "id": 1,
  "query": "ndvi of delhi for 2023",
  "api_name": "ee.ImageCollection"
}
```

| Field | Type | Description |
|---|---|---|
| `id` | integer | Unique query identifier (1–100) |
| `query` | string | Natural-language query in plain English |
| `api_name` | string | Primary GEE API call expected in the generated code |

**Coverage**: Queries span 10 Indian ecological zones including Thar Desert, Western Ghats, Indo-Gangetic Plain, Himalayan foothills, coastal regions, and urban agglomerations.

**Indices covered**: NDVI, EVI, SAVI, MNDWI, NDMI, NBR, UI, BSI, LST, AOD, SAR.

**Satellites targeted**: Sentinel-2, Landsat-8, MODIS.

**How queries were created**: All 100 queries were human-authored. No automated generation was used. Queries were designed to test lexical diversity (paraphrasing), spectral diversity (8+ index types), and spatial diversity (pan-India coverage).

---

## GEE Asset Dependency

All benchmark queries use the public GEE boundary asset:
```
projects/ee-myresearch/assets/India_sorted
```
This is a FeatureCollection of Indian administrative boundaries (states, districts, villages) used for spatial filtering in all GEE scripts. The asset is public and accessible to any authenticated GEE user.

---

## Excluded Data

The following data directories are excluded from this repository (added to `.gitignore`):

| Directory | Reason |
|---|---|
| `data/cache/` | Local disk cache of GEE API responses — user-specific |
| `data/query_history/` | User query session logs — may contain PII |
| `data/benchmark_results.json` | Benchmark run output — generated locally by `reproduce/run_benchmark.py` |
