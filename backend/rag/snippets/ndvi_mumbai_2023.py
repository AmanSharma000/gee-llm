import ee
from datetime import datetime


# Load custom India boundaries (village-level granularity)
india_boundaries = ee.FeatureCollection("projects/ee-myresearch/assets/India_sorted")

# Filter for Mumbai district
# Mumbai can be filtered by DISTRICT field
mumbai = india_boundaries.filter(ee.Filter.eq('DISTRICT', 'MUMBAI')).first()
geometry = mumbai.geometry()

# Target year
year = 2023

start = ee.Date.fromYMD(year, 1, 1)
end = ee.Date.fromYMD(year, 12, 31)

# Load Sentinel-2
collection = (
    ee.ImageCollection("COPERNICUS/S2_SR_HARMONIZED")
    .filterDate(start, end)
    .filterBounds(geometry)
    .filter(ee.Filter.lt("CLOUDY_PIXEL_PERCENTAGE", 20))
)

def calculate_ndvi_s2(image):
    """Calculate NDVI using Sentinel-2"""
    nir = image.select('B8').multiply(0.0001)
    red = image.select('B4').multiply(0.0001)
    ndvi = nir.subtract(red).divide(nir.add(red)).rename('NDVI')
    return image.addBands(ndvi)

# Calculate NDVI
ndvi_collection = collection.map(calculate_ndvi_s2)


# Store result in Feature for consistency and potential future batching
result_feature = ee.Feature(None, {
    'year': year,
    'region': 'Mumbai',
    'satellite': 'Sentinel-2',
    'NDVI': ndvi_collection.select('NDVI').mean().reduceRegion(
        reducer=ee.Reducer.fixedHistogram(-1.0, 1.0, 20),
        geometry=geometry,
        scale=10,
        bestEffort=True,
        maxPixels=1e13
    ).get('NDVI')
})

result_data = result_feature.getInfo()['properties']

result = {
    'year': result_data['year'],
    'ndvi_histogram': result_data['NDVI'] if result_data.get('NDVI') is not None else [],
    'region': result_data['region'],
    'satellite': result_data['satellite']
}
