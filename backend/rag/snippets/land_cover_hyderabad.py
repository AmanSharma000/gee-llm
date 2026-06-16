"""
Land cover classification for Hyderabad using multiple indices (NDVI, NDWI, NDBI).
"""
import ee
from datetime import datetime

# Load custom India boundaries (village-level granularity)
india_boundaries = ee.FeatureCollection("projects/ee-myresearch/assets/India_sorted")

# Filter for Hyderabad district
hyderabad = india_boundaries.filter(ee.Filter.eq('DISTRICT', 'HYDERABAD')).first()
geometry = hyderabad.geometry()

# Target year
year = 2023

# Get Sentinel-2 data
s2 = ee.ImageCollection('COPERNICUS/S2_SR_HARMONIZED') \
    .filterDate(f'{year}-01-01', f'{year}-12-31') \
    .filterBounds(geometry) \
    .filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE', 20))

# Add all indices
def add_indices(img):
    ndvi = img.normalizedDifference(['B8', 'B4']).rename('NDVI')
    ndwi = img.normalizedDifference(['B3', 'B8']).rename('NDWI')
    ndbi = img.normalizedDifference(['B11', 'B8']).rename('NDBI')
    return img.addBands([ndvi, ndwi, ndbi])

s2_indices = s2.map(add_indices)
median = s2_indices.median()

# Simple classification
# Water: NDWI > 0.3
# Vegetation: NDVI > 0.4 and NDWI < 0.3
# Urban: NDBI > 0.1 and NDVI < 0.4
# Bare soil: everything else

ndvi = median.select('NDVI')
ndwi = median.select('NDWI')
ndbi = median.select('NDBI')

water = ndwi.gt(0.3)
vegetation = ndvi.gt(0.4).And(ndwi.lt(0.3))
urban = ndbi.gt(0.1).And(ndvi.lt(0.4))

# Calculate areas
pixel_area = ee.Image.pixelArea().divide(1e6)  # sq km

water_area = water.multiply(pixel_area).reduceRegion(
    reducer=ee.Reducer.sum(),
    geometry=geometry,
    scale=10,
    bestEffort=True,
    maxPixels=1e13
).get('NDWI')

veg_area = vegetation.multiply(pixel_area).reduceRegion(
    reducer=ee.Reducer.sum(),
    geometry=geometry,
    scale=10,
    bestEffort=True,
    maxPixels=1e13
).get('NDVI')

urban_area = urban.multiply(pixel_area).reduceRegion(
    reducer=ee.Reducer.sum(),
    geometry=geometry,
    scale=10,
    bestEffort=True,
    maxPixels=1e13
).get('NDBI')


# Batch all area calculations into single .getInfo() call for performance
stats_dict = ee.Dictionary({
    'water_km2': water_area,
    'vegetation_km2': veg_area,
    'urban_km2': urban_area
})

result_data = stats_dict.getInfo()  # Single network request!

result = {
    'region': 'Hyderabad',
    'year': year,
    'water_km2': round(result_data['water_km2'], 2) if result_data['water_km2'] else 0,
    'vegetation_km2': round(result_data['vegetation_km2'], 2) if result_data['vegetation_km2'] else 0,
    'urban_km2': round(result_data['urban_km2'], 2) if result_data['urban_km2'] else 0
}
