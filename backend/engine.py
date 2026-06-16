import re
from typing import Any

from backend.rag.retriever import retrieve_examples
from backend.rag.prompt_builder import build_prompt
from backend.llm_client import call_llm
from backend.gee_runner import run_gee_code
from backend.self_corrector import execute_with_self_correction
from backend.query_logger import QueryLogger
from backend.satellite_selector import select_best_satellite


# Keys that indicate a histogram result — do NOT retry if any of these exist
_HISTOGRAM_KEYS = {'ndvi_histogram', 'evi_histogram', 'savi_histogram',
                   'ndwi_histogram', 'mndwi_histogram', 'nbr_histogram',
                   'ndmi_histogram', 'lst_histogram', 'histogram',
                   'ndvi', 'evi', 'savi', 'ndwi', 'time_series'}


def _is_scalar_result(result: Any) -> bool:
    """Return True if result is a plain scalar dict (no histogram / series data)."""
    if not isinstance(result, dict):
        return False
    # If it has a list value anywhere, it's likely a histogram
    for v in result.values():
        if isinstance(v, (list, tuple)):
            return False
    # If none of the known histogram keys are present, it's scalar
    keys_lower = {k.lower() for k in result.keys()}
    return not keys_lower.intersection(_HISTOGRAM_KEYS)


def _build_histogram_retry_prompt(user_query: str, scalar_result: dict) -> str:
    """Build a strict retry prompt that forces fixedHistogram output."""
    region = scalar_result.get('region', 'the requested region')
    year   = scalar_result.get('year', 'the requested year')
    satellite = scalar_result.get('satellite', 'Sentinel-2')
    return (
        f"The previous attempt for the query '{user_query}' returned only a scalar value "
        f"(e.g. mean_ndvi). You MUST produce a histogram distribution instead.\n\n"
        f"Write Google Earth Engine Python code that:\n"
        f"1. Filters the {satellite} ImageCollection for {region}, year={year}.\n"
        f"2. Calculates the NDVI (or relevant index) per image.\n"
        f"3. Uses `ee.Reducer.fixedHistogram(-1.0, 1.0, 20)` to reduce the mean composite over the region.\n"
        f"4. Stores the result as `result = {{'year': {year}, 'ndvi_histogram': <histogram_list>, "
        f"'region': '{region}', 'satellite': '{satellite}'}}`\n"
        f"5. Follows all standard rules: no plotting, single .getInfo(), bestEffort=True, maxPixels=1e13.\n"
        f"Return ONLY executable Python code in a markdown block."
    )


CODE_BLOCK_RE = re.compile(
    r"```(?:python)?\s*(.*?)```",
    re.DOTALL | re.IGNORECASE,
)


def _extract_code(raw: str) -> str:
    """
    Take raw LLM output and extract *only* the Python code.

    Handles cases like:
    - ```python ... ```
    - ``` ... ```
    - Extra text before 'import ee'
    """
    text = raw.strip()

    # 1) If there is a fenced code block, use that
    m = CODE_BLOCK_RE.search(text)
    if m:
        code = m.group(1)
    else:
        code = text

    code = code.strip()

    # 2) If code starts with 'python' on first line, drop that
    if code.lower().startswith("python") and "\n" in code:
        code = code.split("\n", 1)[1].strip()

    # 3) If there's some explanation before the first 'import ee',
    #    cut everything before it
    idx = code.find("import ee")
    if idx != -1:
        code = code[idx:]

    return code.strip()


def handle_geo_query(user_query: str, debug: bool = False, use_self_correction: bool = True, use_rag: bool = True, custom_geometry = None):
    """
    Full pipeline:
    - Retrieve similar examples with RAG
    - Build prompt
    - Call LLM to generate code
    - Clean the code
    - Execute in GEE with self-correction (if enabled) and return result
    
    Args:
        user_query: The user's natural language query
        debug: Whether to print debug information
        use_self_correction: Whether to use automatic error correction (default: True)
        use_rag: Whether to retrieve context examples using RAG (default: True)
    """
    # Initialize query logger
    query_logger = QueryLogger(user_query)
    
    try:
        # 1) RAG
        examples = retrieve_examples(user_query, k=3) if use_rag else []
        query_logger.log_stage('rag', {
            'num_examples': len(examples),
            'examples': [ex['query'] for ex in examples]
        })

        # 2) Determine preferred satellite
        satellite = select_best_satellite(user_query)

        # 3) Prompt
        prompt = build_prompt(user_query, examples, mode="code", satellite=satellite, custom_geometry=custom_geometry)

        # 3) LLM
        raw_output = call_llm(prompt)
        code = _extract_code(raw_output)
        
        query_logger.log_stage('llm', {
            'prompt_length': len(prompt),
            'response_length': len(raw_output),
            'code_length': len(code)
        })

        if debug:
            print("=== RAG EXAMPLES ===")
            for ex in examples:
                print("-", ex["query"], " -> ", ex["code_file"])
            print("\n=== PROMPT (first 500 chars) ===\n")
            print(prompt[:500])
            print("\n=== RAW LLM OUTPUT ===\n")
            print(raw_output)
            print("\n=== CLEANED CODE ===\n")
            print(code)

        # 4) Run in GEE with self-correction
        if use_self_correction:
            execution_result = execute_with_self_correction(code, user_query, max_retries=2, custom_geometry=custom_geometry)
            
            if execution_result['success']:
                result = execution_result['result']
                final_code = execution_result['code']

                # ── Histogram enforcer ────────────────────────────────────
                # If the LLM returned a plain scalar dict instead of a
                # histogram, retry ONCE with an explicit histogram prompt.
                if _is_scalar_result(result):
                    query_logger.log_stage('histogram_retry', {
                        'reason': 'scalar_result_detected',
                        'scalar_keys': list(result.keys())
                    })
                    retry_prompt = _build_histogram_retry_prompt(user_query, result)
                    retry_raw = call_llm(retry_prompt)
                    retry_code = _extract_code(retry_raw)
                    retry_exec = execute_with_self_correction(
                        retry_code, user_query, max_retries=2,
                        custom_geometry=custom_geometry
                    )
                    if retry_exec['success'] and not _is_scalar_result(retry_exec['result']):
                        result = retry_exec['result']
                        final_code = retry_exec['code']
                # ─────────────────────────────────────────────────────────

                # Log successful execution
                query_logger.log_stage('gee', {
                    'success': True,
                    'attempts': execution_result['attempts'],
                    'corrections': execution_result.get('corrections', []),
                    'result_type': type(result).__name__
                })
                
                # Log final result
                query_logger.log_result(result)
                
                return {
                    "query": user_query,
                    "code": final_code,
                    "result": result,
                    "attempts": execution_result['attempts'],
                    "corrections": execution_result.get('corrections', []),
                    "geometry": execution_result.get('geometry'),
                    "image": execution_result.get('image')
                }
            else:
                # Log failed execution
                error = execution_result['error']
                query_logger.log_stage('gee', {
                    'success': False,
                    'attempts': execution_result['attempts'],
                    'corrections': execution_result.get('corrections', []),
                    'error': error
                })
                query_logger.log_error(Exception(error))
                
                raise Exception(error)
        else:
            # Original behavior without self-correction
            execution_output = run_gee_code(code, custom_geometry=custom_geometry)
            
            # Extract result, geometry, and image
            result = execution_output.get('result') if isinstance(execution_output, dict) else execution_output
            geometry = execution_output.get('geometry') if isinstance(execution_output, dict) else None
            image = execution_output.get('image') if isinstance(execution_output, dict) else None
            
            query_logger.log_stage('gee', {
                'success': True,
                'result_type': type(result).__name__
            })
            query_logger.log_result(result)
            
            return {
                "query": user_query,
                "code": code,
                "result": result,
                "geometry": geometry,
                "image": image
            }
            
    except Exception as e:
        query_logger.log_error(e)
        raise
