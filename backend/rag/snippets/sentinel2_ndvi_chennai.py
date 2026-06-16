import ee
from datetime import datetime


# Load custom India boundaries (village-level granularity)
india_boundaries = ee.FeatureCollection("projects/ee-myresearch/assets/India_sorted")

# Filter for Chennai district
chennai = india_boundaries.filter(ee.Filter.eq('DISTRICT', 'CHENNAI')).first()
geometry = chennai.geometry()

# Target year
year = 2023

start = ee.Date.fromYMD(year, 1, 1)
end = ee.Date.fromYMD(year, 12, 31)

# Load Sentinel-2 Surface Reflectance
collection = (
    ee.ImageCollection("COPERNICUS/S2_SR_HARMONIZED")
    .filterDate(start, end)
    .filterBounds(geometry)
    .filter(ee.Filter.lt("CLOUDY_PIXEL_PERCENTAGE", 20))
)

def calculate_ndvi_s2(image):
    """Calculate NDVI using Sentinel-2 bands"""
    # Sentinel-2 bands: B8 = NIR, B4 = RED
    # Scale factor is 0.0001
    nir = image.select('B8').multiply(0.0001)
    red = image.select('B4').multiply(0.0001)
    
    # NDVI formula: (NIR - RED) / (NIR + RED)
    ndvi = nir.subtract(red).divide(nir.add(red)).rename('NDVI')
    
    return image.addBands(ndvi)

# Calculate NDVI
ndvi_collection = collection.map(calculate_ndvi_s2)


# Store result in Feature for consistency
result_feature = ee.Feature(None, {
    'year': year,
    'satellite': 'Sentinel-2',
    'resolution': '10m',
    'NDVI_histogram': ndvi_collection.select('NDVI').mean().reduceRegion(
        reducer=ee.Reducer.fixedHistogram(-1.0, 1.0, 20),
        geometry=geometry,
        scale=10,  # 10m resolution for Sentinel-2
        bestEffort=True,
        maxPixels=1e13
    ).get('NDVI')
})

result_data = result_feature.getInfo()['properties']

result = {
    'year': result_data['year'],
    'ndvi_histogram': result_data['NDVI_histogram'] if result_data.get('NDVI_histogram') is not None else [],
    'satellite': result_data['satellite'],
    'resolution': result_data['resolution']
}
