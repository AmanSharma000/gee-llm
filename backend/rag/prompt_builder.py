
import os
from typing import List, Dict, Any

HERE = os.path.dirname(__file__)
SNIPPETS_BASE = os.path.join(HERE, "snippets")


def _load_code_from_file(code_file: str) -> str:
    if code_file.startswith("snippets/"):
        rel = code_file.split("snippets/", 1)[1]
        full_path = os.path.join(SNIPPETS_BASE, rel)
    else:
        full_path = os.path.join(HERE, code_file)

    with open(full_path, "r", encoding="utf-8") as f:
        return f.read()


def build_prompt(user_query: str,
                 examples: List[Dict[str, Any]],
                 mode: str = "code",
                 satellite: str = None,
                 custom_geometry=None) -> str:
    header = (
        "You are an expert assistant that writes Google Earth Engine Python code.\n"
        "You use the Earth Engine Python client library (import ee).\n"
        "You will be given some examples of user queries and their corresponding GEE Python code.\n"
        "Learn the pattern from the examples and then write code for the new query.\n\n"
        "Here are some examples:\n\n"
    )

    body_parts = []
    for idx, ex in enumerate(examples, start=1):
        query_text = ex.get("query", "")
        desc = ex.get("description", "")
        code_file = ex.get("code_file", "")
        try:
            code_text = _load_code_from_file(code_file)
        except Exception:
            code_text = "# Code not found"

        part = f"Example {idx}\n"
        part += f"Query:\n{query_text}\n\n"
        if desc:
            part += f"Description:\n{desc}\n\n"
        part += "GEE Python Code:\n"
        part += code_text
        part += "\n\n"
        body_parts.append(part)

    body = "".join(body_parts)

    footer = (
        "Now write Google Earth Engine Python code for the following new query:\n"
        "====================================\n"
        "NEW USER QUERY:\n"
        f"{user_query}\n"
        "====================================\n\n"
    )

    if mode == "code":
        footer += (
            "=== SYSTEM RULES & CONSTRAINTS ===\n"
            "You MUST strictly follow these rules to generate executable and optimized code:\n\n"

            "1. ENVIRONMENT & OUTPUT FORMAT:\n"
            "   - Start your code with `import ee` and `from datetime import datetime` ONLY.\n"
            "     Do NOT call ee.Initialize() or ee.Authenticate().\n"
            "   - Return ONLY executable Python code within a markdown block.\n"
            "     Do NOT include any explanations, introduction, or text outside the code block.\n"
            "   - Store the final output in a variable named `result`.\n\n"

            "   ╔══════════════════════════════════════════════════════════════════╗\n"
            "   ║   ⛔ ABSOLUTE FORBIDDEN RULES — BREAKING ANY = BROKEN CODE ⛔   ║\n"
            "   ╠══════════════════════════════════════════════════════════════════╣\n"
            "   ║                                                                  ║\n"
            "   ║  🚫 NEVER import or use matplotlib, seaborn, plt, pyplot, fig   ║\n"
            "   ║     This is a backend data service. The FRONTEND visualizes.    ║\n"
            "   ║     Writing `import matplotlib` means your code WILL FAIL.      ║\n"
            "   ║                                                                  ║\n"
            "   ║  🚫 NEVER call .sample() on an ImageCollection.                 ║\n"
            "   ║     ImageCollection has NO .sample() method — it will CRASH.    ║\n"
            "   ║     Use .reduceRegion(ee.Reducer.fixedHistogram()) instead.     ║\n"
            "   ║                                                                  ║\n"
            "   ║  🚫 NEVER use FAO/GAUL or any other dataset for Indian regions. ║\n"
            "   ║     ALWAYS use: ee.FeatureCollection(                           ║\n"
            "   ║       'projects/ee-myresearch/assets/India_sorted')             ║\n"
            "   ║                                                                  ║\n"
            "   ╚══════════════════════════════════════════════════════════════════╝\n\n"

            "2. REGIONAL GEOMETRY FILTERING:\n"
            "   - **Indian Locations:** Always use the custom dataset: "
            "`ee.FeatureCollection('projects/ee-myresearch/assets/India_sorted')`.\n"
            "     - For cities/villages (or if query says 'city'): filter by the field `VILLAGE` "
            "(e.g. `india_boundaries.filter(ee.Filter.eq('VILLAGE', 'GURUGRAM')).first()`).\n"
            "     - For districts (or default): filter by the field `DISTRICT` "
            "(e.g. `MUMBAI`, `NEW DELHI`, `BENGALURU URBAN`).\n"
            "     - For states: filter by the field `STATE` (e.g. `RAJASTHAN`, `MAHARASHTRA`).\n"
            "     - CRITICAL: When computing state or district area/statistics, filter for "
            "`ee.Filter.neq('VILLAGE', '')` to avoid administrative overlap double-counting.\n"
            "     - Specific rules: Treat 'Delhi' as STATE 'DELHI', 'New Delhi' as DISTRICT 'NEW DELHI', "
            "and 'Bangalore' as DISTRICT 'BENGALURU URBAN'.\n"
            "   - **Other Locations:** Use standard GAUL boundary collections (`FAO/GAUL/2015/level1` or similar).\n"
            "   - **Custom Uploads:** If custom geometry is active, a `geometry` variable is preloaded. "
            "Do not perform any filtering/geocoding in that case.\n"
            "   - Immediately after geocoding, define the boundary geometry: "
            "`geometry = FILTERED_FEATURE.geometry()`.\n\n"

            "3. EARTH ENGINE BEST PRACTICES & CASTING:\n"
            "   - **Casting ee.Algorithms.If:** GEE conditional branching returns a generic ComputedObject. "
            "You MUST explicitly cast it back to an `ee.Image` before calling image methods:\n"
            "     ```python\n"
            "     median = ee.Algorithms.If(collection.size().gt(0), collection.median(), fallback_image)\n"
            "     median = ee.Image(median) # MUST CAST HERE!\n"
            "     ```\n"
            "   - **Clamping Indices:** Clamping is required to avoid outlier issues. "
            "Clamp indices to `[-1.0, 1.0]` before reducing: `.clamp(-1.0, 1.0)`.\n"
            "   - **No Python Loops:** Never use Python `for` loops for GEE operations. "
            "Always use server-side mapping: `ee.List(years).map(function)`.\n"
            "   - **No Python list .map():** Cast Python lists to `ee.List(list)` before calling `.map()`. "
            "Inside the map function, cast the year argument to `ee.Number(year)`.\n"
            "   - **Never use .sampleRectangle():** It causes memory/size failures. "
            "Use `.reduceRegion()` instead.\n\n"

            "4. SPECTRAL INDICES & DATASETS:\n"
            "   - **Sentinel-2:** Use 'COPERNICUS/S2_SR_HARMONIZED'. Scale all bands by `0.0001` *before* "
            "computing vegetation/water indices (reflectance is stored as reflectance × 10000).\n"
            "   - **MODIS:** Use 'MODIS/061/MOD13A1'. Scale output *after* .getInfo() by `0.0001` "
            "in the python list comprehension.\n"
            "   - **MODIS NDWI:** 'MOD13A1' has no GREEN/SWIR1 bands. Compute NDWI using "
            "Near-Infrared ('sur_refl_b02') and Shortwave-Infrared ('sur_refl_b07').\n"
            "   - **Method selection:** Use `.normalizedDifference([band1, band2])` for difference indices "
            "(NDVI, NDWI, etc.) instead of manual subtraction/division.\n\n"

            "5. DATA REDUCTION & PERFORMANCE:\n"
            "   - **fixedHistogram Reducers:** Always use `ee.Reducer.fixedHistogram()` for regional index "
            "reductions (never `ee.Reducer.mean()`).\n"
            "     - NDVI, EVI, SAVI, NDWI, MNDWI, NBR, NDMI: `fixedHistogram(-1.0, 1.0, 20)`\n"
            "     - LST (Temperature): `fixedHistogram(0.0, 60.0, 60)`\n"
            "     - Precipitation (CHIRPS): `fixedHistogram(0.0, 3000.0, 30)`\n"
            "     - Radar (Sentinel-1): `fixedHistogram(-30.0, 10.0, 40)`\n"
            "   - **Reduce Region Arguments:** Always include `scale` (10 for Sentinel-2, 30 for Landsat, "
            "500 for MODIS), `bestEffort=True`, and `maxPixels=1e13`.\n"
            "   - **Single .getInfo() network request:** Batch all results into a single object "
            "(`ee.FeatureCollection`, `ee.Feature`, or `ee.Dictionary`) and call `.getInfo()` only ONCE "
            "at the end of the script.\n"
            "   - **None Handling:** Always check for `None` in Python after `.getInfo()` "
            "(e.g. `val if val is not None else None`).\n\n"
        )

        # Add custom geometry instruction if provided
        if custom_geometry is not None:
            footer += (
                "- **CRITICAL: USER UPLOADED CUSTOM GEOMETRY.** A custom region geometry has been PRE-LOADED "
                "into the `geometry` variable. DO NOT use geocoding (india_boundaries, FAO/GAUL, USDOS/LSIB, etc.). "
            )

    prompt = header + body + footer
    return prompt
