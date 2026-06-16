# User Guide — GEE-LLM

This guide describes every input, output, option, and expected behaviour of the GEE-LLM framework.

---

## Table of Contents

1. [Overview](#1-overview)
2. [Inputs](#2-inputs)
3. [Outputs](#3-outputs)
4. [Configuration Options](#4-configuration-options)
5. [Model Selection](#5-model-selection)
6. [Supported Regions](#6-supported-regions)
7. [Supported Indices & Satellites](#7-supported-indices--satellites)
8. [Expected Behaviour & Limits](#8-expected-behaviour--limits)
9. [Common Errors](#9-common-errors)
10. [Programmatic API](#10-programmatic-api)

---

## 1. Overview

GEE-LLM exposes two interfaces:

| Interface | How to access |
|---|---|
| **Web Dashboard** | `streamlit run app.py` → `http://localhost:8501` |
| **Python API** | `from backend.engine import handle_geo_query` |

---

## 2. Inputs

### 2.1 Natural Language Query (required)

A plain-English description of the geospatial analysis you want to perform.

**Format**: Free-form text string.

**Good examples**:
- `ndvi of rajasthan for 2022`
- `compare evi of delhi vs mumbai from 2020 to 2023`
- `forest change in western ghats using landsat from 2015 to 2023`
- `mndwi of assam for 2023`

**Tips**:
- Include the **spectral index** (ndvi, evi, mndwi, nbr, …)
- Include the **region** (state, district, or city name)
- Include the **year or year range**
- Optionally specify the **satellite** (sentinel-2, landsat, modis)

### 2.2 Custom Region Geometry (optional)

Upload a custom boundary file via the sidebar in the web UI.

| Format | Notes |
|---|---|
| GeoJSON (`.geojson`, `.json`) | Recommended |
| KML (`.kml`) | Google Earth format |
| Shapefile ZIP (`.zip`) | Must contain `.shp`, `.shx`, `.dbf`, `.prj` |

Maximum geometry area: ~500,000 km² (larger areas trigger MODIS auto-selection).  
Maximum vertex count: 1,000 vertices (larger geometries are simplified).

### 2.3 Satellite Override (optional)

Specify your preferred satellite in the query text:
- `using sentinel-2` or `s2`
- `using landsat` or `landsat-8` or `l8`
- `using modis`

If not specified, the satellite is selected automatically based on the region area (see §7).

---

## 3. Outputs

### 3.1 Web Dashboard Output

Results are displayed as:
- **Histogram chart** — distribution of pixel values for the requested index
- **Time-series chart** — annual/monthly trend (for multi-year queries)
- **Summary statistics** — mean, min, max, standard deviation
- **Generated code** — the GEE Python script (expandable panel)
- **Export buttons** — download as CSV or JSON

### 3.2 Python API Output

`handle_geo_query()` returns a dictionary:

```python
{
    "success":     bool,              # True if execution succeeded
    "result":      dict | None,       # Parsed GEE result
    "code":        str,               # Generated GEE Python code
    "attempts":    int,               # Number of execution attempts (1–3)
    "corrections": list[str],         # List of correction prompts applied
    "error":       str | None,        # Final error message (if failed)
    "cached":      bool               # True if result was served from cache
}
```

**Example `result` for an NDVI query**:
```python
{
    "region":    "Delhi",
    "year":      2023,
    "satellite": "Sentinel-2",
    "ndvi":      [0.12, 0.18, 0.24, 0.31, 0.22, 0.15, 0.08]  # histogram bins
}
```

**Example `result` for a comparison query**:
```python
{
    "region_1": "Delhi",
    "region_2": "Mumbai",
    "year":     2023,
    "index":    "ndvi",
    "result_1": {"ndvi": [...]},
    "result_2": {"ndvi": [...]}
}
```

---

## 4. Configuration Options

### 4.1 API Keys

Set in `.streamlit/secrets.toml` (never commit this file):
```toml
COHERE_API_KEY = "..."
GROQ_API_KEY   = "..."
```

Or via environment variables:
```bash
export COHERE_API_KEY="..."
export GROQ_API_KEY="..."
```

### 4.2 `handle_geo_query()` Parameters

```python
from backend.engine import handle_geo_query

result = handle_geo_query(
    query            = "ndvi of delhi for 2023",  # required
    debug            = False,      # True: print intermediate steps to stdout
    use_self_correction = True,    # False: single attempt only (faster, less reliable)
    custom_geometry  = None,       # ee.Geometry object from geometry_parser
)
```

| Parameter | Type | Default | Description |
|---|---|---|---|
| `query` | `str` | — | Natural-language query (required) |
| `debug` | `bool` | `False` | Print intermediate steps |
| `use_self_correction` | `bool` | `True` | Enable self-correction loop |
| `custom_geometry` | `ee.Geometry` | `None` | Custom spatial boundary |

### 4.3 Cache

Results are cached on disk at `data/cache/` using DiskCache. Cache TTL: **7 days**.  
To clear the cache:
```bash
python clear_cache.py
```

---

## 5. Model Selection

GEE-LLM supports three LLM backends:

| Backend | Model | API Key Needed | Offline? |
|---|---|---|---|
| **Cohere** | `command-a-03-2025` | `COHERE_API_KEY` | No |
| **Groq** | `llama-3.3-70b-versatile` | `GROQ_API_KEY` | No |
| **Ollama** | Any local model | None | ✅ Yes |

To use Ollama (fully offline):
1. Install [Ollama](https://ollama.com) and pull a model: `ollama pull llama3`
2. Ensure Ollama is running: `ollama serve`
3. The framework auto-detects Ollama if no cloud API key is set.

---

## 6. Supported Regions

Any **Indian state, district, or major city** is supported via the `India_sorted` GEE FeatureCollection asset (`projects/ee-myresearch/assets/India_sorted`).

**Examples of valid region names**:
- States: `Rajasthan`, `Kerala`, `West Bengal`, `Himachal Pradesh`
- Districts: `Jaipur district`, `Shimla`, `Gurugram`
- Cities: `Delhi`, `Mumbai`, `Chennai`, `Bangalore`
- Geographic features: `Western Ghats`, `Thar Desert`

> **Note**: International regions outside India are not currently supported via the built-in boundary asset. Use the custom geometry upload for other countries.

---

## 7. Supported Indices & Satellites

### Spectral Indices

| Index | Full Name | Typical Range |
|---|---|---|
| NDVI | Normalized Difference Vegetation Index | −1 to +1 |
| EVI | Enhanced Vegetation Index | −1 to +1 |
| SAVI | Soil Adjusted Vegetation Index | −1.5 to +1.5 |
| MSAVI | Modified SAVI | −1 to +1 |
| NDWI | Normalized Difference Water Index | −1 to +1 |
| MNDWI | Modified NDWI | −1 to +1 |
| NDMI | Normalized Difference Moisture Index | −1 to +1 |
| NBR | Normalized Burn Ratio | −1 to +1 |
| UI | Urban Index | −1 to +1 |
| BSI | Bare Soil Index | varies |
| GCI | Green Chlorophyll Index | 0 to 20 |
| NDSI | Normalized Difference Snow Index | −1 to +1 |
| LST | Land Surface Temperature | °C |
| AOD | Aerosol Optical Depth | 0 to 5 |

### Satellite Auto-Selection Logic

| Region Area | Auto-selected Satellite |
|---|---|
| < 5,000 km² (city/district) | Sentinel-2 (10 m) |
| 5,000 – 100,000 km² (state) | Landsat-8 (30 m) |
| > 100,000 km² (multi-state) | MODIS (500 m) |

---

## 8. Expected Behaviour & Limits

| Behaviour | Details |
|---|---|
| **Self-correction retries** | Up to 3 attempts per query |
| **Typical latency** | 5–30 seconds per query (GEE API + LLM API) |
| **Cache hit latency** | < 1 second |
| **Physical bounds check** | Rejects results with NDVI > 1.0, NDVI < −1.0, etc. |
| **Max region area** | ~500,000 km² (India total area: 3.29M km² — use MODIS) |
| **Date archive limits** | Sentinel-2: 2015–present; Landsat-8: 2013–present; MODIS: 2000–present |
| **Concurrent requests** | 1 (Streamlit single-user by default) |

---

## 9. Common Errors

| Error Message | Cause | Solution |
|---|---|---|
| `'list' object has no attribute 'map'` | LLM used Python list instead of `ee.List` | Self-corrected automatically |
| `EEException: Computation timed out` | Region too large or scale too fine | Framework retries with `bestEffort=True` |
| `Empty ImageCollection` | Date range has no available imagery | Try a wider date range |
| `not authorized` | GEE authentication expired | Run `earthengine authenticate` |
| `Code did not define 'result' variable` | LLM output missing `result =` | Self-corrected automatically |
| `CohereAPIError: 429` | API rate limit hit | Wait 60 seconds and retry |
| `GROQ_API_KEY not set` | Missing Groq credentials | Set `GROQ_API_KEY` in secrets.toml |

---

## 10. Programmatic API

```python
import ee
ee.Initialize()

from backend.engine import handle_geo_query
from backend.geometry_parser import parse_geojson

# Basic query
result = handle_geo_query("ndvi of kerala for 2023")

if result["success"]:
    print(result["result"])
    print(f"Attempts needed: {result['attempts']}")
else:
    print(f"Failed: {result['error']}")

# Query with custom geometry
geojson_str = '{"type": "FeatureCollection", ...}'
geometry = parse_geojson(geojson_str)
result = handle_geo_query("ndvi trend 2020–2023", custom_geometry=geometry)
```
