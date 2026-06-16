"""
Compute both NDVI and NDWI for Mumbai region.
Returns multi-index analysis data.
"""
import ee

# Load custom India boundaries (village-level granularity)
india_boundaries = ee.FeatureCollection("projects/ee-myresearch/assets/India_sorted")

# Filter for Mumbai district
mumbai = india_boundaries.filter(ee.Filter.eq('DISTRICT', 'MUMBAI')).first()
geometry = mumbai.geometry()

# Get Sentinel-2 data for 2024
s2 = ee.ImageCollection('COPERNICUS/S2_SR_HARMONIZED') \
    .filterDate('2024-01-01', '2024-12-31') \
    .filterBounds(geometry) \
    .filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE', 20))

# Add indices
def add_indices(img):
    ndvi = img.normalizedDifference(['B8', 'B4']).rename('NDVI')
    ndwi = img.normalizedDifference(['B3', 'B8']).rename('NDWI')
    return img.addBands([ndvi, ndwi])

s2_indices = s2.map(add_indices)
median = s2_indices.median()

# Get mean values over region
stats = median.select(['NDVI', 'NDWI']).reduceRegion(
    reducer=ee.Reducer.fixedHistogram(-1.0, 1.0, 20),
    geometry=geometry,
    scale=30,
    maxPixels=1e9
)


# Batch both index values into single .getInfo() call
result_data = stats.getInfo()  # Single network request for both NDVI and NDWI

result = {
    'region': 'Mumbai',
    'year': 2024,
    'NDVI': round(result_data['NDVI'], 4) if result_data.get('NDVI') is not None else None,
    'NDWI': round(result_data['NDWI'], 4) if result_data.get('NDWI') is not None else None
}
