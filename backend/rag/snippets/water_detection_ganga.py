"""
Water body detection using NDWI for Ganga River basin.
"""
import ee

# Load custom India boundaries (village-level granularity)
india_boundaries = ee.FeatureCollection("projects/ee-myresearch/assets/India_sorted")

# Filter for Varanasi district (on the banks of Ganga)
varanasi = india_boundaries.filter(ee.Filter.eq('DISTRICT', 'VARANASI')).first()
geometry = varanasi.geometry()

# Get Sentinel-2 data for 2024
s2 = ee.ImageCollection('COPERNICUS/S2_SR_HARMONIZED') \
    .filterDate('2024-01-01', '2024-12-31') \
    .filterBounds(geometry) \
    .filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE', 20))

# Add NDWI band
def add_ndwi(img):
    ndwi = img.normalizedDifference(['B3', 'B8']).rename('NDWI')
    return img.addBands(ndwi)

s2_ndwi = s2.map(add_ndwi)
median = s2_ndwi.median().select('NDWI')

# Classify as water (NDWI > 0.3)
water_mask = median.gt(0.3)

# Calculate water area in sq km
water_area = water_mask.multiply(ee.Image.pixelArea()).divide(1e6)

stats = water_area.reduceRegion(
    reducer=ee.Reducer.sum(),
    geometry=geometry,
    scale=10,
    bestEffort=True,
    maxPixels=1e13
)


# Store result in Feature for consistency with other snippets
result_feature = ee.Feature(None, {
    'region': 'Ganga River Basin',
    'year': 2024,
    'water_area_km2': stats.get('NDWI')
})

result_data = result_feature.getInfo()['properties']

# Return as a list for consistency
result = [{
    'region': result_data['region'],
    'year': result_data['year'],
    'water_area_km2': round(result_data['water_area_km2'], 2) if result_data['water_area_km2'] else 0
}]
