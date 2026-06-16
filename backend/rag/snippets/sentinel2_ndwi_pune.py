import ee
from datetime import datetime


# Load custom India boundaries (village-level granularity)
india_boundaries = ee.FeatureCollection("projects/ee-myresearch/assets/India_sorted")

# Filter for Pune district
pune = india_boundaries.filter(ee.Filter.eq('DISTRICT', 'PUNE')).first()
geometry = pune.geometry()

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

def calculate_ndwi_s2(image):
    """Calculate NDWI using Sentinel-2"""
    # Sentinel-2: B3=GREEN, B8=NIR
    green = image.select('B3').multiply(0.0001)
    nir = image.select('B8').multiply(0.0001)
    
    # NDWI formula: (GREEN - NIR) / (GREEN + NIR)
    ndwi = green.subtract(nir).divide(green.add(nir)).rename('NDWI')
    
    return image.addBands(ndwi)

# Calculate NDWI
ndwi_collection = collection.map(calculate_ndwi_s2)


# Store result in Feature for consistency
result_feature = ee.Feature(None, {
    'year': year,
    'satellite': 'Sentinel-2',
    'NDWI': ndwi_collection.select('NDWI').mean().reduceRegion(
        reducer=ee.Reducer.fixedHistogram(-1.0, 1.0, 20),
        geometry=geometry,
        scale=10,
        bestEffort=True,
        maxPixels=1e13
    ).get('NDWI')
})

result_data = result_feature.getInfo()['properties']

result = {
    'year': result_data['year'],
    'ndwi_histogram': result_data['NDWI'] if result_data.get('NDWI') is not None else [],
    'satellite': result_data['satellite']
}
