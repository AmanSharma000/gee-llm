"""
reproduce/run_benchmark.py
--------------------------
Cross-platform benchmark runner for the GEE-LLM 100-query evaluation.

Usage:
    cd reproduce
    python run_benchmark.py [--model cohere|groq|ollama] [--queries N]

Outputs:
    ../data/benchmark_results.json
"""

import json
import time
import argparse
import sys
from pathlib import Path

# Ensure the project root is on the Python path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from backend.engine import handle_geo_query

# ---------------------------------------------------------------------------
# Paths (all relative — cross-platform)
# ---------------------------------------------------------------------------
BENCHMARK_FILE = PROJECT_ROOT / "data" / "benchmark_100_queries_final.json"
OUTPUT_FILE    = PROJECT_ROOT / "data" / "benchmark_results.json"


def run_benchmark(max_queries: int = 100) -> None:
    """Run the 100-query GEE-LLM evaluation benchmark."""

    if not BENCHMARK_FILE.exists():
        print(f"ERROR: Benchmark file not found: {BENCHMARK_FILE}")
        print("Make sure you are running from the 'reproduce/' directory.")
        sys.exit(1)

    with open(BENCHMARK_FILE, "r", encoding="utf-8") as f:
        queries = json.load(f)

    queries = queries[:max_queries]
    total         = len(queries)
    successful    = 0
    self_corrected = 0
    failed        = 0
    results       = []

    print(f"\n{'='*60}")
    print(f" GEE-LLM Benchmark — {total} queries")
    print(f"{'='*60}\n")

    for i, item in enumerate(queries):
        query      = item["query"]
        api_target = item.get("api_name", "unknown")
        print(f"[{i+1:3d}/{total}] {query}")

        start = time.time()
        try:
            res = handle_geo_query(
                query,
                debug=False,
                use_self_correction=True,
                custom_geometry=None
            )
            duration = time.time() - start
            attempts  = res.get("attempts", 1)
            code      = res.get("code", "")
            api_used  = api_target.split(".")[-1] in code

            if attempts > 1:
                self_corrected += 1
                label = f"✓ (corrected, {attempts} attempts)"
            else:
                successful += 1
                label = "✓ (first try)"

            results.append({
                "id":                i + 1,
                "query":             query,
                "api_target":        api_target,
                "success":           True,
                "attempts":          attempts,
                "self_corrected":    attempts > 1,
                "api_found_in_code": api_used,
                "duration":          round(duration, 3),
                "corrections":       res.get("corrections", []),
            })
            print(f"       {label} in {duration:.1f}s\n")

        except Exception as exc:
            duration = time.time() - start
            failed += 1
            results.append({
                "id":       i + 1,
                "query":    query,
                "success":  False,
                "error":    str(exc),
                "duration": round(duration, 3),
            })
            print(f"       ✗ FAILED: {str(exc)[:80]}\n")

    # ------------------------------------------------------------------
    # Summary
    # ------------------------------------------------------------------
    total_success  = successful + self_corrected
    success_rate   = total_success / total * 100 if total else 0

    print(f"\n{'='*60}")
    print(f" Results Summary")
    print(f"{'='*60}")
    print(f"  Total queries     : {total}")
    print(f"  First-try success : {successful}")
    print(f"  Corrected success : {self_corrected}")
    print(f"  Total success     : {total_success}  ({success_rate:.1f}%)")
    print(f"  Failed            : {failed}")
    print(f"{'='*60}\n")

    output = {
        "summary": {
            "total":                      total,
            "successful_first_try":       successful,
            "successful_after_correction": self_corrected,
            "total_successful":           total_success,
            "failed":                     failed,
            "success_rate_pct":           round(success_rate, 2),
        },
        "details": results,
    }

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2)

    print(f"Results saved to: {OUTPUT_FILE}\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="GEE-LLM benchmark runner")
    parser.add_argument(
        "--queries", type=int, default=100,
        help="Number of queries to run (default: 100, max: 100)"
    )
    args = parser.parse_args()
    run_benchmark(max_queries=min(args.queries, 100))
