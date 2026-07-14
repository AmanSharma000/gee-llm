import os
import sys
import time
import json
import traceback

# Append project root directory to path to enable backend imports
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from backend.engine import handle_geo_query
from backend.comparison_engine import ComparisonEngine

# Define the 15 benchmark queries across three complexity levels
BENCHMARK_QUERIES = [
    # Level 1: Simple (Single index, single region, single year)
    {"id": 1, "query": "ndvi of delhi for 2023", "level": "Simple", "index": "ndvi"},
    {"id": 2, "query": "evi of jaipur city for 2022 using sentinel-2", "level": "Simple", "index": "evi"},
    {"id": 3, "query": "mndwi of bangalore for 2023 using landsat", "level": "Simple", "index": "mndwi"},
    {"id": 4, "query": "ndwi of chennai for 2023", "level": "Simple", "index": "ndwi"},
    {"id": 5, "query": "savi of hyderabad for 2022", "level": "Simple", "index": "savi"},
    
    # Level 2: Medium (Comparison queries - temporal/spatial)
    {"id": 6, "query": "compare ndvi of delhi vs mumbai for 2023", "level": "Medium", "index": "ndvi", "is_comparison": True},
    {"id": 7, "query": "compare evi of chennai vs bangalore for 2022 using sentinel-2", "level": "Medium", "index": "evi", "is_comparison": True},
    {"id": 8, "query": "compare ndvi of gurugram in 2020 vs 2024", "level": "Medium", "index": "ndvi", "is_comparison": True},
    {"id": 9, "query": "compare mndwi of jaipur city in 2021 vs 2023", "level": "Medium", "index": "mndwi", "is_comparison": True},
    {"id": 10, "query": "compare savi of kolkata vs patna for 2022", "level": "Medium", "index": "savi", "is_comparison": True},
    
    # Level 3: Complex (Temporal Trend / Time Series)
    {"id": 11, "query": "ndvi trend of mumbai from 2018 to 2023", "level": "Complex", "index": "ndvi", "is_trend": True},
    {"id": 12, "query": "savi trend of haryana from 2020 to 2024", "level": "Complex", "index": "savi", "is_trend": True},
    {"id": 13, "query": "mndwi trend of west bengal from 2020 to 2023 using landsat", "level": "Complex", "index": "mndwi", "is_trend": True},
    {"id": 14, "query": "evi trend of delhi from 2019 to 2023", "level": "Complex", "index": "evi", "is_trend": True},
    {"id": 15, "query": "ndwi trend of gujarat from 2021 to 2024 using modis", "level": "Complex", "index": "ndwi", "is_trend": True}
]

def validate_scientific_bounds(index_name, value):
    """
    Validate if the computed geospatial index is within realistic physical bounds.
    Vegetation indices generally range from -1.0 to 1.0.
    """
    if value is None:
        return False, "Value is None"
    try:
        val = float(value)
    except (ValueError, TypeError):
        return False, f"Value '{value}' is not a numeric type"
    
    # Standard environmental bounds
    if index_name.lower() in ['ndvi', 'evi', 'savi', 'ndwi', 'mndwi', 'ndmi', 'nbr']:
        if -1.0 <= val <= 1.0:
            return True, "Valid"
        else:
            return False, f"Value {val:.4f} is outside remote sensing index bounds [-1.0, 1.0]"
    elif index_name.lower() in ['ui', 'bsi']:
        if -1.5 <= val <= 1.5:
            return True, "Valid"
        else:
            return False, f"Value {val:.4f} is outside index bounds [-1.5, 1.5]"
    return True, "Valid"

def extract_values_from_result(result, index_name, is_trend=False):
    """Extract numeric index values from different query output formats."""
    values = []
    
    if is_trend:
        # Expected list of dicts: [{'year': 2020, 'ndvi': 0.42}, ...]
        if isinstance(result, list):
            for item in result:
                if isinstance(item, dict):
                    # Check keys case-insensitively
                    for k, v in item.items():
                        if k.lower() == index_name.lower() and v is not None:
                            values.append(v)
        elif isinstance(result, dict):
            # Check for keys like 'ndvi', 'NDVI', etc. containing lists
            for k, v in result.items():
                if k.lower() == index_name.lower() and isinstance(v, list):
                    values.extend([x for x in v if x is not None])
    else:
        # Expected single dictionary: {'ndvi': 0.42} or single numeric
        if isinstance(result, dict):
            for k, v in result.items():
                if k.lower() == index_name.lower() and v is not None:
                    values.append(v)
        elif isinstance(result, (int, float)):
            values.append(result)
            
    return values

def run_single_query(query_info, use_rag, use_self_correction):
    """Execute a single query, handling comparison logic if needed."""
    query_text = query_info["query"]
    index_name = query_info["index"]
    is_comparison = query_info.get("is_comparison", False)
    is_trend = query_info.get("is_trend", False)
    
    start_time = time.time()
    attempts = 1
    corrections = []
    
    try:
        if is_comparison:
            # Replicate Streamlit comparison parsing logic
            comp_engine = ComparisonEngine()
            comp_info = comp_engine.parse_comparison_entities(query_text)
            if not comp_info:
                return {
                    "success": False,
                    "error": "Comparison query failed to parse",
                    "latency": time.time() - start_time,
                    "attempts": 1,
                    "scientific_valid": False
                }
                
            query1, query2 = comp_engine.create_comparison_queries(comp_info)
            
            # Execute sub-query 1
            res1 = handle_geo_query(query1, use_self_correction=use_self_correction, use_rag=use_rag)
            attempts = res1.get("attempts", 1)
            corrections.extend(res1.get("corrections", []))
            
            # Execute sub-query 2
            res2 = handle_geo_query(query2, use_self_correction=use_self_correction, use_rag=use_rag)
            attempts = max(attempts, res2.get("attempts", 1))
            corrections.extend(res2.get("corrections", []))
            
            latency = time.time() - start_time
            
            # Extract and validate values from both sub-queries
            vals1 = extract_values_from_result(res1["result"], index_name, is_trend=False)
            vals2 = extract_values_from_result(res2["result"], index_name, is_trend=False)
            
            if not vals1 or not vals2:
                return {
                    "success": True,
                    "latency": latency,
                    "attempts": attempts,
                    "corrections": corrections,
                    "scientific_valid": False,
                    "scientific_reason": "No numeric values extracted from comparison",
                    "values": []
                }
                
            valid1, reason1 = validate_scientific_bounds(index_name, vals1[0])
            valid2, reason2 = validate_scientific_bounds(index_name, vals2[0])
            
            scientific_valid = valid1 and valid2
            scientific_reason = "Valid" if scientific_valid else f"Part 1: {reason1}; Part 2: {reason2}"
            
            return {
                "success": True,
                "latency": latency,
                "attempts": attempts,
                "corrections": corrections,
                "scientific_valid": scientific_valid,
                "scientific_reason": scientific_reason,
                "values": [vals1[0], vals2[0]]
            }
            
        else:
            # Normal query
            res = handle_geo_query(query_text, use_self_correction=use_self_correction, use_rag=use_rag)
            latency = time.time() - start_time
            attempts = res.get("attempts", 1)
            corrections = res.get("corrections", [])
            
            vals = extract_values_from_result(res["result"], index_name, is_trend)
            
            if not vals:
                return {
                    "success": True,
                    "latency": latency,
                    "attempts": attempts,
                    "corrections": corrections,
                    "scientific_valid": False,
                    "scientific_reason": f"No index values found matching '{index_name}'",
                    "values": []
                }
            
            # Validate all extracted values
            scientific_valid = True
            scientific_reason = "Valid"
            for v in vals:
                valid, reason = validate_scientific_bounds(index_name, v)
                if not valid:
                    scientific_valid = False
                    scientific_reason = reason
                    break
                    
            return {
                "success": True,
                "latency": latency,
                "attempts": attempts,
                "corrections": corrections,
                "scientific_valid": scientific_valid,
                "scientific_reason": scientific_reason,
                "values": vals
            }
            
    except Exception as e:
        latency = time.time() - start_time
        return {
            "success": False,
            "error": str(e),
            "latency": latency,
            "attempts": attempts,
            "scientific_valid": False,
            "scientific_reason": f"Exception raised: {type(e).__name__}"
        }

def run_full_benchmark():
    out_path = os.path.join(os.path.dirname(__file__), "benchmark_results.json")
    
    # Load existing results if they exist to allow incremental updates/resuming
    existing_queries = {}
    if os.path.exists(out_path):
        try:
            with open(out_path, "r", encoding="utf-8") as f:
                old_data = json.load(f)
                for oq in old_data.get("queries", []):
                    existing_queries[oq["id"]] = oq
            print(f"Loaded {len(existing_queries)} existing query results from {out_path} for incremental resume.")
        except Exception as e:
            print(f"Could not load existing benchmark file: {e}. Starting fresh.")

    print("====================================================")
    print("STARTING GEOSPATIAL LLM BENCHMARK EVALUATION (INCREMENTAL)")
    print("====================================================")
    print(f"Total Queries: {len(BENCHMARK_QUERIES)}")
    print("Configs: 1) Baseline (No RAG, No Fix)")
    print("         2) RAG-Only (RAG active, No Fix)")
    print("         3) Full System (RAG + Fixes + Self-Correction)")
    print("====================================================\n")
    
    # Structure to hold results
    benchmark_data = {
        "metadata": {
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "num_queries": len(BENCHMARK_QUERIES)
        },
        "queries": []
    }
    
    # Iterate over queries
    for idx, q in enumerate(BENCHMARK_QUERIES):
        print(f"[{idx+1}/{len(BENCHMARK_QUERIES)}] Query: \"{q['query']}\" ({q['level']})")
        
        # Check if we have cached results for this query
        cached_q = existing_queries.get(q["id"])
        
        # 1. BASELINE RUN
        baseline_cached = cached_q.get("baseline") if cached_q else None
        if baseline_cached:
            print("  - Baseline: Using cached result")
            baseline_res = baseline_cached
        else:
            print("  - Running Baseline...")
            baseline_res = run_single_query(q, use_rag=False, use_self_correction=False)
            print(f"    Success: {baseline_res['success']}, Valid: {baseline_res['scientific_valid']}, Time: {baseline_res['latency']:.2f}s")
            
        # 2. RAG-ONLY RUN
        rag_cached = cached_q.get("rag_only") if cached_q else None
        if rag_cached and rag_cached.get("success") and rag_cached.get("scientific_valid"):
            print("  - RAG-Only: Using cached result")
            rag_res = rag_cached
        else:
            print("  - Running RAG-Only...")
            rag_res = run_single_query(q, use_rag=True, use_self_correction=False)
            print(f"    Success: {rag_res['success']}, Valid: {rag_res['scientific_valid']}, Time: {rag_res['latency']:.2f}s")
            
        # 3. FULL SYSTEM RUN
        full_cached = cached_q.get("full_system") if cached_q else None
        if full_cached and full_cached.get("success") and full_cached.get("scientific_valid"):
            print("  - Full System: Using cached result")
            full_res = full_cached
        else:
            print("  - Running Full System...")
            full_res = run_single_query(q, use_rag=True, use_self_correction=True)
            print(f"    Success: {full_res['success']}, Valid: {full_res['scientific_valid']}, Time: {full_res['latency']:.2f}s, Attempts: {full_res['attempts']}")
            
        # Save query record
        query_record = {
            "id": q["id"],
            "query": q["query"],
            "level": q["level"],
            "index": q["index"],
            "baseline": baseline_res,
            "rag_only": rag_res,
            "full_system": full_res
        }
        benchmark_data["queries"].append(query_record)
        
        # Save incrementally
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(benchmark_data, f, indent=2, ensure_ascii=False)
        print()
        
    print("====================================================")
    print(f"BENCHMARK COMPLETED. Results written to: {out_path}")
    print("====================================================")

if __name__ == "__main__":
    run_full_benchmark()
