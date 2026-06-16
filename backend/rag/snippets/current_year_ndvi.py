"""
Example: Multi-year NDVI calculation using proper date handling.

This example shows the CORRECT way to handle current dates in Earth Engine Python API.

CRITICAL RULES:
1. DO NOT use ee.Date.now() - it doesn't exist in Earth Engine Python API!
2. DO NOT use ee.List.sequence() with Python datetime values
3. Use Python's datetime module and list(range()) for year iterations
4. For N years: range(current_year - N, current_year) gives EXACTLY N years
"""
import ee
from datetime import datetime

# Load custom India boundaries (village-level granularity)
india_boundaries = ee.FeatureCollection("projects/ee-myresearch/assets/India_sorted")

# Filter for Gurugram (City query -> VILLAGE)
gurugram = india_boundaries.filter(ee.Filter.eq('VILLAGE', 'GURUGRAM')).first()
geometry = gurugram.geometry()

# CORRECT: Use Python's datetime to get current year
now_year = datetime.now().year

# WARNING: Common mistakes to AVOID:
# ❌ WRONG: current_year = datetime.now().year - 1  (off-by-one error)
# ❌ WRONG: ee.List.sequence(current_year - 5, current_year)  (gives 6 years, not 5!)
# ✅ CORRECT: list(range(current_year - 5, current_year))  (gives exactly 5 years)

# Calculate NDVI for the last 5 years
# Example in 2024: range(2019, 2024) = [2019, 2020, 2021, 2022, 2023] = 5 years
years = list(range(now_year - 5, now_year))

def compute_yearly_ndvi(year):
    """Compute mean NDVI for a single year."""
    year = ee.Number(year)
    start = ee.Date.fromYMD(year, 1, 1)
    end = ee.Date.fromYMD(year, 12, 31)
    
    collection = (
        ee.ImageCollection("COPERNICUS/S2_SR_HARMONIZED")
        .filterDate(start, end)
        .filterBounds(geometry)
        .filter(ee.Filter.lt("CLOUDY_PIXEL_PERCENTAGE", 20))
    )
    
    median = ee.Algorithms.If(
        collection.size().gt(0),
        collection.median(),
        ee.Image.constant(0).addBands(ee.Image.constant(0)).rename(["B8", "B4"])
    )
    median = ee.Image(median)
    
    ndvi = median.normalizedDifference(["B8", "B4"]).rename("NDVI")
    
    stats = ndvi.reduceRegion(
        reducer=ee.Reducer.fixedHistogram(-1.0, 1.0, 20),
        geometry=geometry,
        scale=10,
        bestEffort=True,
        maxPixels=1e13
    )
    
    return ee.Feature(None, {
        'year': year,
        'NDVI': stats.get("NDVI")
    })

# Server-side mapping
years_list = ee.List(years)
result_fc = ee.FeatureCollection(years_list.map(compute_yearly_ndvi))

# One network request
result = result_fc.getInfo()["features"]
result = [{"year": f["properties"]["year"], "NDVI": f["properties"]["NDVI"]} for f in result]


