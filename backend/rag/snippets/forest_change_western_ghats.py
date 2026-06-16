"""
Forest cover change detection using NDVI threshold for Western Ghats.
"""
import ee
from datetime import datetime

# Load custom India boundaries (village-level granularity)
india_boundaries = ee.FeatureCollection("projects/ee-myresearch/assets/India_sorted")

# Filter for Western Ghats states (Kerala, Karnataka, Goa, Maharashtra)
western_ghats_states = india_boundaries.filter(ee.Filter.inList('STATE', ['KERALA', 'KARNATAKA', 'GOA', 'MAHARASHTRA']))
geometry = western_ghats_states.geometry()

# Function to compute forest area (NDVI > 0.6) for a year
def compute_forest_area(year):
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
    forest = ndvi.gt(0.4).rename("forest")
    area_img = forest.multiply(ee.Image.pixelArea()).divide(1e6)
    
    stats = area_img.reduceRegion(
        reducer=ee.Reducer.sum(),
        geometry=geometry,
        scale=10,
        bestEffort=True,
        maxPixels=1e13
    )
    
    return ee.Feature(None, {
        'year': year,
        'forest_area_sqkm': stats.get('forest')
    })

# Compute for 5 years ago and current year using server-side mapping
current_year = datetime.now().year
years = ee.List([current_year - 5, current_year - 1])
forest_stats = years.map(compute_forest_area)

# Get result in one go
result = ee.FeatureCollection(forest_stats).getInfo()['features']
result = [{
    'year': f['properties']['year'], 
    'forest_area_km2': round(f['properties']['forest_area_sqkm'], 2) if f['properties']['forest_area_sqkm'] is not None else None
} for f in result]
