# Reproducibility Guide

This directory contains everything needed to reproduce the main results from the paper:

> *GEE-LLM as a Lightweight Agentic Framework for Automated Geospatial Code Generation*

---

## Prerequisites

Before running the benchmark you need:

1. **Python 3.9+** with dependencies installed:
   ```bash
   pip install -r ../requirements.txt
   ```

2. **A Google Earth Engine (GEE) account** with project access:
   - Sign up at [https://earthengine.google.com](https://earthengine.google.com)
   - Authenticate from the terminal:
     ```bash
     earthengine authenticate
     ```

3. **An LLM API key** — one of:
   - **Cohere** (free tier): [https://cohere.com](https://cohere.com) → set `COHERE_API_KEY`
   - **Groq** (free tier, used for Llama-3.3-70B): [https://console.groq.com](https://console.groq.com) → set `GROQ_API_KEY`
   - **Ollama** (fully offline): [https://ollama.com](https://ollama.com) → no key needed

   Set credentials via environment variable or `.streamlit/secrets.toml` in the project root:
   ```toml
   COHERE_API_KEY = "your-key-here"
   GROQ_API_KEY   = "your-key-here"
   ```

---

## Running the Benchmark

From the `reproduce/` directory:

```bash
cd reproduce
python run_benchmark.py
```

The script:
1. Loads the 100 queries from `../data/benchmark_100_queries_final.json`
2. For each query:
   - Sends the query to the GEE-LLM pipeline (with self-correction enabled)
   - Records: success/failure, number of attempts, corrections applied, latency
3. Saves results to `../data/benchmark_results.json`
4. Prints a summary table to stdout

**Expected runtime**: ~60–90 minutes for 100 queries (GEE API latency dominates).

---

## Interpreting the Output

The output file `../data/benchmark_results.json` has the structure:

```json
{
  "summary": {
    "total": 100,
    "successful_first_try": 32,
    "successful_after_correction": 13,
    "total_successful": 45,
    "failed": 55,
    "success_rate": 45.0
  },
  "details": [
    {
      "id": 1,
      "query": "ndvi of delhi for 2023",
      "success": true,
      "attempts": 1,
      "self_corrected": false,
      "duration": 4.21
    }
  ]
}
```

---

## Expected Results (Paper Table 4)

| Model | `COHERE_API_KEY` model | Success Rate |
|---|---|---|
| Baseline (no GEE-LLM) | `command-a-03-2025` | 12.0% |
| **GEE-LLM + Cohere** | `command-a-03-2025` | **44.0%** |
| Baseline (no GEE-LLM) | `llama-3.3-70b-versatile` | 17.0% |
| **GEE-LLM + Groq Llama** | `llama-3.3-70b-versatile` | **45.0%** |

> **Note on non-determinism**: LLM outputs are stochastic. Results may vary by ±2–3 percentage points across runs depending on model API version and temperature. McNemar's test significance (*p* < 0.001) is robust to these small variations.

---

## Partial Reproduction (No GEE Account)

If you do not have a GEE account, you can still verify the framework logic using the provided sample outputs:

```bash
python -c "import json; data=json.load(open('sample_output_expected.json')); print(json.dumps(data[0], indent=2))"
```

The file `sample_output_expected.json` contains expected GEE-LLM outputs for 5 representative queries. You can compare these against your own runs to verify correctness.

---

## Troubleshooting

| Error | Likely Cause | Fix |
|---|---|---|
| `EEException: not authorized` | GEE auth expired | Run `earthengine authenticate` again |
| `cohere.error.CohereAPIError` | Invalid/expired API key | Check `COHERE_API_KEY` in secrets.toml |
| `Empty collection` | Date range out of satellite archive | Query uses dates before satellite launch |
| `MemoryError` on large region | Region too large for GEE scale | Framework auto-retries with `bestEffort=True` |
