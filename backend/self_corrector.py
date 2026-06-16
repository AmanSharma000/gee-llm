"""
Self-correcting agent that automatically retries failed queries with corrections.
Includes caching support for GEE execution results.
"""
from typing import Dict, Any, Optional
import re
from backend.llm_client import call_llm
from backend.gee_runner import run_gee_code
from backend.error_analyzer import analyze_and_suggest_fix
from backend.logging_config import setup_logger, log_with_context

logger = setup_logger('backend.self_corrector')


# ---------------------------------------------------------------------------
# Pre-execution code sanitizer
# Strips known forbidden patterns before GEE even sees the code.
# ---------------------------------------------------------------------------
_FORBIDDEN_IMPORT_RE = re.compile(
    r"^\s*(?:import|from)\s+(?:matplotlib|seaborn|plotly|PIL|cv2|skimage)\S*.*$",
    re.MULTILINE
)
_PLT_CALL_RE = re.compile(
    r"^\s*(?:plt|fig|ax|axes)\.[a-zA-Z_]+\(.*\).*$",
    re.MULTILINE
)
# Matches any .sample( call on what looks like an ImageCollection variable
_SAMPLE_CALL_RE = re.compile(
    r"\.sample\s*\(",
    re.MULTILINE
)


def _sanitize_code(code: str) -> str:
    """
    Remove forbidden patterns from generated GEE code before execution:
      - matplotlib / seaborn / plotly imports
      - plt.* / fig.* plotting calls
      - .sample() calls on ImageCollections (not a valid GEE ImageCollection method)
    Returns cleaned code.
    """
    # Remove forbidden import lines
    code = _FORBIDDEN_IMPORT_RE.sub("", code)
    # Remove plt.*/fig.* call lines
    code = _PLT_CALL_RE.sub("", code)
    # Replace .sample( → this is always wrong for ImageCollection; flag it so
    # self-correction can catch it if it slips through
    if _SAMPLE_CALL_RE.search(code):
        # Replace with a comment so the execution fails gracefully with a
        # descriptive message rather than AttributeError
        code = _SAMPLE_CALL_RE.sub(
            ".reduceRegion(  # SANITIZED: .sample() is not valid on ImageCollection — use .reduceRegion() instead",
            code
        )
    return code

# Import cache manager (lazy import)
_cache_manager = None

def _get_cache_manager():
    global _cache_manager
    if _cache_manager is None:
        try:
            from backend.cache_manager import cache_manager
            _cache_manager = cache_manager
        except ImportError:
            _cache_manager = None
    return _cache_manager


class SelfCorrector:
    """Automatically corrects and retries failed GEE code execution."""
    
    def __init__(self, max_retries: int = 2, use_cache: bool = True):
        """
        Initialize the self-corrector.
        
        Args:
            max_retries: Maximum number of correction attempts
            use_cache: Whether to use caching for GEE results
        """
        self.max_retries = max_retries
        self.use_cache = use_cache
        log_with_context(
            logger, 20, "SelfCorrector initialized",
            max_retries=max_retries,
            use_cache=use_cache
        )
    
    def execute_with_retry(
        self,
        code: str,
        query: str,
        attempt: int = 0,
        custom_geometry = None
    ) -> Dict[str, Any]:
        """
        Execute code with automatic retry and correction on failure.
        
        Args:
            code: The GEE Python code to execute
            query: The original user query
            attempt: Current attempt number (0-indexed)
            
        Returns:
            Dictionary with execution result or error information
        """
        log_with_context(
            logger, 20, "Executing code with retry",
            attempt=attempt,
            max_retries=self.max_retries,
            code_length=len(code)
        )
        
        # Check cache first (only on first attempt)
        cache_mgr = _get_cache_manager() if self.use_cache else None
        if cache_mgr and attempt == 0:
            cached_result = cache_mgr.get_gee_result(code)
            if cached_result is not None:
                log_with_context(
                    logger, 20, "GEE result served from cache",
                    code_length=len(code)
                )
                return {
                    'success': True,
                    'result': cached_result,
                    'code': code,
                    'attempts': 1,
                    'corrections': [],
                    'from_cache': True
                }
        
        # Try to execute the code
        try:
            # ── Pre-execution sanitizer ──────────────────────────────────
            # Strip matplotlib imports, plt.* calls, and .sample() before
            # GEE even sees the code. This prevents common LLM mistakes.
            code = _sanitize_code(code)
            # ────────────────────────────────────────────────────────────
            execution_output = run_gee_code(code, custom_geometry=custom_geometry)
            
            # Extract result, geometry, and image from execution output
            result = execution_output.get('result') if isinstance(execution_output, dict) else execution_output
            geometry = execution_output.get('geometry') if isinstance(execution_output, dict) else None
            image = execution_output.get('image') if isinstance(execution_output, dict) else None
            
            # Validate results scientifically
            self.validate_scientific_bounds(query, result)
            
            # Cache successful result
            if cache_mgr and attempt == 0:
                cache_mgr.set_gee_result(code, result)
            
            log_with_context(
                logger, 20, "Code executed successfully",
                attempt=attempt,
                result_type=type(result).__name__
            )
            
            return {
                'success': True,
                'result': result,
                'geometry': geometry,
                'image': image,
                'code': code,
                'attempts': attempt + 1,
                'corrections': []
            }
            
        except Exception as e:
            error_message = str(e)
            
            log_with_context(
                logger, 30, "Code execution failed",
                attempt=attempt,
                error_type=type(e).__name__,
                error_preview=error_message[:200]
            )
            
            # Fail Fast: Do not retry on unrecoverable errors
            if "User memory limit exceeded" in error_message or \
               "Quota exceeded" in error_message or \
               "Authentication failed" in error_message or \
               "Caller does not have permission" in error_message:
                log_with_context(
                    logger, 40, "Unrecoverable error, failing fast",
                    error_type=type(e).__name__
                )
                return {
                    'success': False,
                    'error': error_message,
                    'code': code,
                    'attempts': attempt + 1,
                    'corrections': [],
                    'fail_fast': True
                }

            # Check if we should retry
            if attempt >= self.max_retries:
                log_with_context(
                    logger, 40, "Max retries reached, giving up",
                    total_attempts=attempt + 1
                )
                
                return {
                    'success': False,
                    'error': error_message,
                    'code': code,
                    'attempts': attempt + 1,
                    'corrections': [],
                    'max_retries_reached': True
                }
            
            # Extract line number from traceback if possible
            import traceback
            tb_str = traceback.format_exc()
            line_number = None
            # Look for "File "<string>", line X" pattern common in exec() tracebacks
            match = re.search(r'File "<string>", line (\d+)', tb_str)
            if match:
                line_number = match.group(1)
                error_message = f"Error on line {line_number}: {error_message}"

            # Analyze error and generate correction
            log_with_context(
                logger, 20, "Attempting automatic correction",
                attempt=attempt + 1,
                line_number=line_number
            )
            
            analysis, correction_prompt = analyze_and_suggest_fix(
                error_message, code, query
            )
            
            # Get corrected code from LLM (with caching)
            try:
                corrected_response = call_llm(correction_prompt, use_cache=self.use_cache)
                
                # Extract code from response (remove markdown if present)
                corrected_code = self._extract_code(corrected_response)
                
                log_with_context(
                    logger, 20, "Correction generated",
                    attempt=attempt + 1,
                    error_type=analysis['error_type'],
                    corrected_code_length=len(corrected_code)
                )
                
                # Validation: Check if corrected code is safe
                from backend.gee_runner import _is_safe
                if not _is_safe(corrected_code):
                    log_with_context(
                        logger, 40, "Corrected code failed safety check",
                        attempt=attempt + 1
                    )
                    return {
                        'success': False,
                        'error': "Corrected code failed safety check (forbidden imports or patterns).",
                        'code': code,
                        'attempts': attempt + 1,
                        'corrections': [],
                        'safety_check_failed': True
                    }

                # Retry with corrected code
                retry_result = self.execute_with_retry(
                    corrected_code,
                    query,
                    attempt + 1,
                    custom_geometry=custom_geometry
                )
                
                # If correction succeeded, cache the result under the ORIGINAL code key too!
                # This prevents re-running the correction loop for the same buggy code next time.
                if retry_result['success'] and self.use_cache:
                    cache_mgr = _get_cache_manager()
                    if cache_mgr:
                        # Cache the result using the ORIGINAL (buggy) code as the key
                        # So next time we see this buggy code, we just return the result immediately
                        cache_mgr.set_gee_result(code, retry_result['result'])
                        log_with_context(
                            logger, 20, "Cached corrected result under original code key",
                            original_code_length=len(code)
                        )
                
                # Add this correction to the history
                if 'corrections' not in retry_result:
                    retry_result['corrections'] = []
                
                retry_result['corrections'].insert(0, {
                    'attempt': attempt + 1,
                    'error_type': analysis['error_type'],
                    'error_message': error_message,
                    'suggestion': analysis['suggestion'],
                    'original_code': code
                })
                
                return retry_result
                
            except Exception as llm_error:
                log_with_context(
                    logger, 40, "Failed to generate correction",
                    attempt=attempt + 1,
                    llm_error=str(llm_error)
                )
                
                return {
                    'success': False,
                    'error': error_message,
                    'code': code,
                    'attempts': attempt + 1,
                    'corrections': [],
                    'correction_failed': True,
                    'correction_error': str(llm_error)
                }
    
    def _extract_code(self, response: str) -> str:
        """
        Extract Python code from LLM response.
        Removes markdown code blocks if present.
        
        Args:
            response: LLM response text
            
        Returns:
            Extracted Python code
        """
        # Remove markdown code blocks
        import re
        
        # Try to find code between ```python and ```
        match = re.search(r'```python\s*(.*?)\s*```', response, re.DOTALL)
        if match:
            return match.group(1).strip()
        
        # Try to find code between ``` and ```
        match = re.search(r'```\s*(.*?)\s*```', response, re.DOTALL)
        if match:
            return match.group(1).strip()
        
        # If no code blocks, return the whole response
        return response.strip()

    def validate_scientific_bounds(self, query: str, result: Any):
        """Validate if the result values are within scientifically expected bounds."""
        # 1. Extract index name from query
        index_name = None
        indices = ['ndvi', 'evi', 'savi', 'ndmi', 'nbr', 'mndwi', 'ui', 'bsi', 'ndwi']
        for idx in indices:
            if idx in query.lower():
                index_name = idx.upper()
                break
        
        if not index_name:
            return
            
        # Helper to recursively find histogram arrays or single values
        def extract_values_and_histograms(obj):
            vals = []
            hists = []
            if isinstance(obj, dict):
                for k, v in obj.items():
                    if index_name.lower() in k.lower():
                        if isinstance(v, list) and len(v) > 0 and isinstance(v[0], list):
                            hists.append(v)
                        elif isinstance(v, (int, float)):
                            vals.append(v)
            elif isinstance(obj, list):
                for item in obj:
                    v, h = extract_values_and_histograms(item)
                    vals.extend(v)
                    hists.extend(h)
            return vals, hists

        values, histograms = extract_values_and_histograms(result)
        
        # 3. Validate values (legacy single floats)
        for val in values:
            try:
                val_float = float(val)
            except (ValueError, TypeError):
                continue
            
            if index_name.lower() in ['ndvi', 'evi', 'savi', 'ndwi', 'mndwi', 'ndmi', 'nbr']:
                if not (-1.0 <= val_float <= 1.0):
                    raise ValueError(
                        f"Scientific validation failed: The calculated {index_name} value {val_float:.4f} "
                        f"is outside the valid physical range of [-1.0, 1.0]. This is often caused by "
                        f"using raw Sentinel-2 or Landsat surface reflectance without multiplying "
                        f"by their scaling factors (e.g., 0.0001)."
                    )
            elif index_name.lower() in ['ui', 'bsi']:
                if not (-1.5 <= val_float <= 1.5):
                    raise ValueError(
                        f"Scientific validation failed: The calculated {index_name} value {val_float:.4f} "
                        f"is outside the valid physical range of [-1.5, 1.5]."
                    )

        # 4. Validate Histograms (sum of pixel counts)
        for hist in histograms:
            total_pixels = sum([bin_data[1] for bin_data in hist if len(bin_data) >= 2])
            if total_pixels == 0:
                 raise ValueError(
                    f"Scientific validation failed: The {index_name} histogram captured 0 pixels within "
                    f"the expected valid range. This means ALL computed pixels were extreme outliers. "
                    f"This is almost always caused by forgetting to scale the optical bands (e.g., "
                    f"multiplying Sentinel-2/Landsat bands by 0.0001) BEFORE calculating the index."
                )


def execute_with_self_correction(
    code: str,
    query: str,
    max_retries: int = 2,
    use_cache: bool = True,
    custom_geometry = None
) -> Dict[str, Any]:
    """
    Convenience function to execute code with self-correction and caching.
    
    Args:
        code: The GEE Python code to execute
        query: The original user query
        max_retries: Maximum number of correction attempts
        use_cache: Whether to use caching
        
    Returns:
        Dictionary with execution result or error information
    """
    corrector = SelfCorrector(max_retries=max_retries, use_cache=use_cache)
    return corrector.execute_with_retry(code, query, custom_geometry=custom_geometry)
