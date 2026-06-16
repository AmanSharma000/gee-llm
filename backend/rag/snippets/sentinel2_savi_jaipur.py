import ee
from datetime import datetime


# Load custom India boundaries (village-level granularity)
india_boundaries = ee.FeatureCollection("projects/ee-myresearch/assets/India_sorted")

# Filter for Jaipur district
jaipur = india_boundaries.filter(ee.Filter.eq('DISTRICT', 'JAIPUR')).first()
geometry = jaipur.geometry()

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

def calculate_savi_s2(image):
    """Calculate SAVI using Sentinel-2"""
    nir = image.select('B8').multiply(0.0001)
    red = image.select('B4').multiply(0.0001)
    
    # SAVI formula: ((NIR - RED) / (NIR + RED + L)) * (1 + L)
    # L = 0.5 for moderate vegetation
    L = 0.5
    savi = nir.subtract(red).divide(
        nir.add(red).add(L)
    ).multiply(1 + L).rename('SAVI')
    
    return image.addBands(savi)

# Calculate SAVI
savi_collection = collection.map(calculate_savi_s2)


# Store result in Feature for consistency
result_feature = ee.Feature(None, {
    'year': year,
    'satellite': 'Sentinel-2',
    'SAVI': savi_collection.select('SAVI').mean().reduceRegion(
        reducer=ee.Reducer.fixedHistogram(-1.0, 1.0, 20),
        geometry=geometry,
        scale=10,
        bestEffort=True,
        maxPixels=1e13
    ).get('SAVI')
})

result_data = result_feature.getInfo()['properties']

result = {
    'year': result_data['year'],
    'savi_histogram': result_data['SAVI'] if result_data.get('SAVI') is not None else [],
    'satellite': result_data['satellite']
}
