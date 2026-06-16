"""
Detect urban expansion using NDBI over time for Bangalore.
"""
import ee
from datetime import datetime

# Load custom India boundaries (village-level granularity)
india_boundaries = ee.FeatureCollection("projects/ee-myresearch/assets/India_sorted")

# Filter for Bangalore district
bangalore = india_boundaries.filter(ee.Filter.eq('DISTRICT', 'BANGALORE')).first()
geometry = bangalore.geometry()

# Function to compute yearly NDBI (Normalized Difference Built-up Index)
def compute_built_up(year):
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
        ee.Image.constant(0).addBands(ee.Image.constant(0)).rename(["B11", "B8"])
    )
    median = ee.Image(median)
    
    ndbi = median.normalizedDifference(["B11", "B8"]).rename("NDBI")
    built_up = ndbi.gt(0.1).rename("built_up")
    area_img = built_up.multiply(ee.Image.pixelArea()).divide(1e6)
    
    stats = area_img.reduceRegion(
        reducer=ee.Reducer.sum(),
        geometry=geometry,
        scale=10,
        bestEffort=True,
        maxPixels=1e13
    )
    
    return ee.Feature(None, {
        'year': year,
        'built_up_area_sqkm': stats.get('built_up')
    })

# Compute for multiple years using server-side mapping (dynamic)
current_year = datetime.now().year
years = ee.List([current_year - 8, current_year - 4, current_year - 1])
built_up_stats = years.map(compute_built_up)

# Get result in one go
result = ee.FeatureCollection(built_up_stats).getInfo()['features']
result = [{
    'year': f['properties']['year'], 
    'built_up_area_km2': round(f['properties']['built_up_area_sqkm'], 2) if f['properties']['built_up_area_sqkm'] is not None else None
} for f in result]
