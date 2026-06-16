import os
import re
import json
import ee
from datetime import datetime
import concurrent.futures

try:
    import streamlit as st
except ImportError:
    st = None


# -------------------------------------------------------------
# EARTH ENGINE INITIALIZATION
# -------------------------------------------------------------
def _init_ee():

    running_in_streamlit = st is not None

    # Check if we have secrets for service account
    has_secrets = False
    try:
        if running_in_streamlit and "gee_service_account" in st.secrets:
            has_secrets = True
    except FileNotFoundError:
        # Streamlit raises FileNotFoundError or similar if secrets.toml is missing
        pass
    except Exception:
        pass

    if has_secrets:
        cfg = dict(st.secrets["gee_service_account"])
        service_email = cfg["client_email"]
        creds_json = json.dumps(cfg)
        project_id = cfg.get("project_id")

        credentials = ee.ServiceAccountCredentials(
            service_email,
            key_data=creds_json,
        )
        ee.Initialize(credentials, project=project_id)
    else:
        # Fallback to standard local auth (gcloud)
        # This works if the user has run 'earthengine authenticate' locally
        try:
            ee.Initialize()
        except Exception as e:
            # If that fails, we can't do much, but let's not crash immediately
            print(f"GEE Initialization failed: {e}")


_init_ee()


# -------------------------------------------------------------
# SAFETY CHECKS
# -------------------------------------------------------------
FORBIDDEN = [
    r"import\s+os",
    r"import\s+subprocess",
    r"__import__",
    r"open\(",
]


def _is_safe(code):
    for p in FORBIDDEN:
        if re.search(p, code):
            return False
    return True


def _sanitize(code):
    cleaned = []
    for line in code.splitlines():
        if "ee.Initialize" in line:
            continue
        cleaned.append(line)
    return "\n".join(cleaned)


def _fix_common_patterns(code):
    """
    Fix common LLM code generation mistakes before execution.
    
    Common issues:
    - ee.Date.now() doesn't exist in Earth Engine Python API
    - Should use Python's datetime.now() instead
    - ee.List.sequence() with Python datetime values (type mixing)
    - Off-by-one errors in year calculations
    """
    # Fix ee.Date.now() -> datetime.now()
    # Pattern 1: ee.Date(ee.Date.now())
    code = re.sub(
        r'ee\.Date\(ee\.Date\.now\(\)\)',
        'datetime.now()',
        code
    )
    
    # Pattern 2: ee.Date.now()
    code = re.sub(
        r'ee\.Date\.now\(\)',
        'datetime.now()',
        code
    )
    
    # Fix ee.List.sequence() -> list(range())
    # This is more Pythonic and avoids type mixing
    # Pattern: ee.List.sequence(start, end) -> list(range(start, end + 1))
    # Note: ee.List.sequence is inclusive on both ends, range is exclusive on end
    code = re.sub(
        r'ee\.List\.sequence\(([^,]+),\s*([^)]+)\)',
        r'list(range(int(\1), int(\2) + 1))',
        code
    )
    
    # Fix common off-by-one error: current_year - 1 before sequence/range
    # Pattern: current_year = datetime.now().year - 1
    # This is usually wrong - should just be datetime.now().year
    code = re.sub(
        r'current_year\s*=\s*datetime\.now\(\)\.year\s*-\s*1',
        'current_year = datetime.now().year',
        code
    )
    
    # Also fix datetime.datetime.now() -> datetime.now()
    # (when using 'from datetime import datetime')
    code = re.sub(
        r'datetime\.datetime\.now\(\)',
        'datetime.now()',
        code
    )
    
    # If we replaced with datetime.now(), ensure datetime import exists
    if 'datetime.now()' in code and 'from datetime import datetime' not in code and 'import datetime' not in code:
        # Add import at the top (after any existing imports)
        lines = code.split('\n')
        import_added = False
        for i, line in enumerate(lines):
            if line.strip() and not line.strip().startswith('#') and not line.strip().startswith('import') and not line.strip().startswith('from'):
                lines.insert(i, 'from datetime import datetime')
                import_added = True
                break
        if import_added:
            code = '\n'.join(lines)
    
    return code


# -------------------------------------------------------------
#  AUTO GEOMETRY INJECTION (PREVENT “geometry not defined”)
# -------------------------------------------------------------
def _fallback_geometry():
    """
    Default geometry if LLM forgets.
    Instead of defaulting to India (which is wrong for other regions),
    we return None so we can detect the missing geometry and fail gracefully,
    or we could return a world polygon if appropriate.
    For now, let's return None to force the LLM to be explicit.
    """
    return None


def _convert(obj):
    """Convert any EE object (or nested structure) into pure Python."""
    if isinstance(obj, list):
        return [_convert(x) for x in obj]
    if isinstance(obj, dict):
        return {k: _convert(v) for k, v in obj.items()}

    # CRITICAL SAFETY GUARD: Prevent massive downloads
    # We explicitly block Image and ImageCollection because .getInfo() on them
    # tries to download the entire raster/collection, which causes timeouts/crashes.
    if isinstance(obj, (ee.Image, ee.ImageCollection)):
        raise RuntimeError(
            "Result is too large (Image/ImageCollection). "
            "Please reduce it to a statistic (mean, median) or use a chart. "
            "Do NOT return raw images."
        )

    try:
        return obj.getInfo()
    except Exception:
        return obj


# -------------------------------------------------------------
#  MAIN EXECUTOR
# -------------------------------------------------------------
def run_gee_code(code: str, custom_geometry = None):

    if not _is_safe(code):
        raise ValueError("Unsafe generated code.")

    code = _sanitize(code)
    
    # Fix common LLM code generation mistakes
    code = _fix_common_patterns(code)

    # Inject geometry so LLM can never break execution
    geometry = _fallback_geometry()

    # Create the execution environment (globals and locals combined)
    # This is crucial so that functions defined in 'code' can see variables defined in 'code'
    exec_env = {
        "ee": ee,
        "datetime": datetime,  # Add datetime for date operations
    }
    
    # NEW: Inject custom geometry if provided
    if custom_geometry is not None:
        exec_env["geometry"] = custom_geometry
    
    # Only inject geometry if it's not None. 
    # If it is None, the code MUST define 'geometry' itself or it will fail.
    if geometry:
        exec_env["geometry"] = geometry

    def _run_internal():
        try:
            exec(code, exec_env)
        except Exception as e:
            # Capture the code that failed for debugging
            raise RuntimeError(f"GEE code execution failed: {e}\n\nCode:\n{code}")

        if "result" not in exec_env:
            raise RuntimeError("Generated code did NOT define `result`.")

        result = exec_env["result"]
        
        # NEW: Capture geometry and image from execution environment
        geometry_obj = exec_env.get("geometry", None)
        image_obj = exec_env.get("image", None)

        # Convert EE → Python (recursively)
        result_converted = _convert(result)
        
        # NEW: Return dict with result, geometry, and image
        return {
            "result": result_converted,
            "geometry": geometry_obj,
            "image": image_obj
        }

    # Run with a 60-second timeout to prevent GEE from hanging on memory limit errors
    executor = concurrent.futures.ThreadPoolExecutor()
    future = executor.submit(_run_internal)
    try:
        return future.result(timeout=60)
    except concurrent.futures.TimeoutError:
        raise RuntimeError("GEE execution timed out after 60 seconds (Likely a Memory Limit Exceeded error due to unscaled reduction).")
    finally:
        executor.shutdown(wait=False)
